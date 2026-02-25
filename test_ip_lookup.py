"""Tests for bgpkit_client.ip_lookup and the ip_lookup MCP tool."""

import json
import pytest
import httpx

from unittest.mock import AsyncMock, MagicMock, patch

from bgpkit_client import lookup_ip, _validate_ip


# ---------------------------------------------------------------------------
# _validate_ip tests
# ---------------------------------------------------------------------------

def test_validate_ip_valid_v4():
    assert _validate_ip("8.8.8.8") == "8.8.8.8"


def test_validate_ip_valid_v6():
    assert _validate_ip("2001:4860:4860::8888") == "2001:4860:4860::8888"


def test_validate_ip_strips_whitespace():
    assert _validate_ip("  1.1.1.1  ") == "1.1.1.1"


def test_validate_ip_private_is_allowed():
    # Private IPs should be accepted by the validator (BGPKit handles no-match)
    assert _validate_ip("192.168.1.1") == "192.168.1.1"


def test_validate_ip_invalid():
    with pytest.raises(ValueError, match="Invalid IP address"):
        _validate_ip("not-an-ip")


def test_validate_ip_cidr_rejected():
    with pytest.raises(ValueError, match="Invalid IP address"):
        _validate_ip("8.8.8.0/24")


# ---------------------------------------------------------------------------
# Helper: build a mock httpx.Response
# ---------------------------------------------------------------------------

def _mock_response(status_code: int, body: dict | str) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    if isinstance(body, dict):
        resp.json.return_value = body
        resp.text = json.dumps(body)
    else:
        resp.json.side_effect = Exception("not json")
        resp.text = body
    return resp


# ---------------------------------------------------------------------------
# lookup_ip – happy path
# ---------------------------------------------------------------------------

BGPKIT_HAPPY_RESPONSE = {
    "code": 200,
    "data": {
        "ip": "8.8.8.8",
        "country": "US",
        "prefix": "8.8.8.0/24",
        "asn": 15169,
        "as_name": "GOOGLE",
        "as_country": "US",
        "rpki_status": "Valid",
        "updated_at": "2024-01-15T00:00:00Z",
    },
}


@pytest.mark.asyncio
async def test_lookup_ip_happy_path():
    mock_resp = _mock_response(200, BGPKIT_HAPPY_RESPONSE)

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("bgpkit_client.httpx.AsyncClient", return_value=mock_client):
        result = await lookup_ip("8.8.8.8")

    assert result["ip"] == "8.8.8.8"
    assert result["country"] == "US"
    assert result["asn"]["prefix"] == "8.8.8.0/24"
    assert result["asn"]["asn"] == 15169
    assert result["asn"]["name"] == "GOOGLE"
    assert result["asn"]["country"] == "US"
    assert result["asn"]["rpki"] == "Valid"
    assert result["asn"]["updatedAt"] == "2024-01-15T00:00:00Z"


@pytest.mark.asyncio
async def test_lookup_ip_normalises_address():
    """Input IP should be normalised before use."""
    mock_resp = _mock_response(200, BGPKIT_HAPPY_RESPONSE)

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("bgpkit_client.httpx.AsyncClient", return_value=mock_client):
        result = await lookup_ip("  8.8.8.8  ")

    assert result["ip"] == "8.8.8.8"


# ---------------------------------------------------------------------------
# lookup_ip – no-match / private / unrouted
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_lookup_ip_no_match_none_data():
    """BGPKit returns null data for unrouted IPs."""
    mock_resp = _mock_response(200, {"code": 200, "data": None})

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("bgpkit_client.httpx.AsyncClient", return_value=mock_client):
        result = await lookup_ip("192.168.1.1")

    assert result["ip"] == "192.168.1.1"
    assert result["country"] is None
    assert result["asn"] is None


@pytest.mark.asyncio
async def test_lookup_ip_no_match_empty_data():
    """BGPKit returns empty data dict with no prefix for some private IPs."""
    mock_resp = _mock_response(200, {"code": 200, "data": {"ip": "10.0.0.1", "country": None}})

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("bgpkit_client.httpx.AsyncClient", return_value=mock_client):
        result = await lookup_ip("10.0.0.1")

    assert result["ip"] == "10.0.0.1"
    assert result["asn"] is None


# ---------------------------------------------------------------------------
# lookup_ip – error handling
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_lookup_ip_invalid_address():
    with pytest.raises(ValueError, match="Invalid IP address"):
        await lookup_ip("not-an-ip")


@pytest.mark.asyncio
async def test_lookup_ip_timeout():
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(
        side_effect=httpx.TimeoutException("timed out")
    )

    with patch("bgpkit_client.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(RuntimeError, match="timed out"):
            await lookup_ip("8.8.8.8")


@pytest.mark.asyncio
async def test_lookup_ip_rate_limit():
    mock_resp = _mock_response(429, "Too Many Requests")
    mock_resp.text = "Too Many Requests"

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("bgpkit_client.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(RuntimeError, match="rate limit"):
            await lookup_ip("8.8.8.8")


@pytest.mark.asyncio
async def test_lookup_ip_http_error():
    mock_resp = _mock_response(503, "Service Unavailable")
    mock_resp.text = "Service Unavailable"

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("bgpkit_client.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(RuntimeError, match="HTTP 503"):
            await lookup_ip("8.8.8.8")


@pytest.mark.asyncio
async def test_lookup_ip_request_error():
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(
        side_effect=httpx.RequestError("connection refused")
    )

    with patch("bgpkit_client.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(RuntimeError, match="request failed"):
            await lookup_ip("8.8.8.8")


@pytest.mark.asyncio
async def test_lookup_ip_api_level_error():
    """BGPKit returning HTTP 200 with a non-200 code in the payload should raise RuntimeError."""
    mock_resp = _mock_response(200, {"code": 400, "message": "invalid IP"})

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("bgpkit_client.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(RuntimeError, match="API error"):
            await lookup_ip("8.8.8.8")


@pytest.mark.asyncio
async def test_lookup_ip_non_json_response():
    mock_resp = _mock_response(200, "this is not json")

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("bgpkit_client.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(RuntimeError, match="non-JSON"):
            await lookup_ip("8.8.8.8")


# ---------------------------------------------------------------------------
# MCP tool: ip_lookup
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mcp_ip_lookup_happy_path():
    """The MCP tool should return JSON for a routed IP."""
    from server import ip_lookup as mcp_ip_lookup

    expected = {
        "ip": "8.8.8.8",
        "country": "US",
        "asn": {
            "prefix": "8.8.8.0/24",
            "asn": 15169,
            "name": "GOOGLE",
            "country": "US",
            "rpki": "Valid",
            "updatedAt": "2024-01-15T00:00:00Z",
        },
    }

    with patch("server.lookup_ip", AsyncMock(return_value=expected)):
        output = await mcp_ip_lookup("8.8.8.8")

    parsed = json.loads(output)
    assert parsed["ip"] == "8.8.8.8"
    assert parsed["country"] == "US"
    assert parsed["asn"]["asn"] == 15169
    assert parsed["asn"]["rpki"] == "Valid"


@pytest.mark.asyncio
async def test_mcp_ip_lookup_unrouted():
    """Unrouted/private IPs should return JSON with asn=null and a message field."""
    from server import ip_lookup as mcp_ip_lookup

    unrouted = {"ip": "10.0.0.1", "country": None, "asn": None}

    with patch("server.lookup_ip", AsyncMock(return_value=unrouted)):
        output = await mcp_ip_lookup("10.0.0.1")

    parsed = json.loads(output)
    assert parsed["ip"] == "10.0.0.1"
    assert parsed["asn"] is None
    assert "message" in parsed
    assert "No BGP route" in parsed["message"]


@pytest.mark.asyncio
async def test_mcp_ip_lookup_invalid_ip():
    """The MCP tool should return JSON with an error field for invalid IPs."""
    from server import ip_lookup as mcp_ip_lookup

    with patch("server.lookup_ip", AsyncMock(side_effect=ValueError("Invalid IP address: 'bad'"))):
        output = await mcp_ip_lookup("bad")

    parsed = json.loads(output)
    assert "error" in parsed
    assert "Invalid IP" in parsed["error"]


@pytest.mark.asyncio
async def test_mcp_ip_lookup_rate_limit():
    """Rate limit errors should be surfaced as JSON with an error field."""
    from server import ip_lookup as mcp_ip_lookup

    with patch("server.lookup_ip", AsyncMock(side_effect=RuntimeError("rate limit exceeded"))):
        output = await mcp_ip_lookup("8.8.8.8")

    parsed = json.loads(output)
    assert "error" in parsed
    assert "rate limit" in parsed["error"]

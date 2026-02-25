"""Tests for the asn_lookup MCP tool and its helpers."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from server import _parse_asn, _fetch_asn_name, asn_lookup


# ---------------------------------------------------------------------------
# _parse_asn – unit tests (synchronous)
# ---------------------------------------------------------------------------


class TestParseAsn:
    def test_plain_integer_string(self):
        assert _parse_asn("13335") == 13335

    def test_as_prefix_uppercase(self):
        assert _parse_asn("AS13335") == 13335

    def test_as_prefix_lowercase(self):
        assert _parse_asn("as13335") == 13335

    def test_as_prefix_mixed_case(self):
        assert _parse_asn("As13335") == 13335

    def test_whitespace_stripped(self):
        assert _parse_asn("  AS13335  ") == 13335

    def test_asn_1(self):
        assert _parse_asn("1") == 1

    def test_max_asn(self):
        assert _parse_asn("4294967295") == 4294967295

    def test_invalid_alpha(self):
        with pytest.raises(ValueError, match="Invalid ASN"):
            _parse_asn("notanasn")

    def test_zero_invalid(self):
        with pytest.raises(ValueError, match="out of valid range"):
            _parse_asn("0")

    def test_overflow_invalid(self):
        with pytest.raises(ValueError, match="out of valid range"):
            _parse_asn("4294967296")

    def test_empty_string(self):
        with pytest.raises(ValueError):
            _parse_asn("")

    def test_as_prefix_only(self):
        with pytest.raises(ValueError):
            _parse_asn("AS")

    def test_float_string(self):
        with pytest.raises(ValueError):
            _parse_asn("13335.5")


# ---------------------------------------------------------------------------
# _fetch_asn_name – async tests with mocked httpx
# ---------------------------------------------------------------------------


def _make_mock_response(status_code: int, json_data: dict | None = None):
    """Create a mock httpx.Response-like object."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    if json_data is not None:
        mock_resp.json = MagicMock(return_value=json_data)
    return mock_resp


class MockAsyncClient:
    """Minimal async context manager wrapping a fixed response."""

    def __init__(self, response):
        self._response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def get(self, url):
        return self._response


@pytest.mark.asyncio
async def test_fetch_asn_name_success():
    resp = _make_mock_response(200, {"data": {"name": "CLOUDFLARENET", "asn": 13335}})
    with patch("server.httpx.AsyncClient", return_value=MockAsyncClient(resp)):
        result = await _fetch_asn_name(13335)
    assert result == "CLOUDFLARENET"


@pytest.mark.asyncio
async def test_fetch_asn_name_top_level_name_fallback():
    """API response with top-level 'name' instead of nested 'data.name'."""
    resp = _make_mock_response(200, {"name": "SOME-NET"})
    with patch("server.httpx.AsyncClient", return_value=MockAsyncClient(resp)):
        result = await _fetch_asn_name(65000)
    assert result == "SOME-NET"


@pytest.mark.asyncio
async def test_fetch_asn_name_404_raises_value_error():
    resp = _make_mock_response(404)
    with patch("server.httpx.AsyncClient", return_value=MockAsyncClient(resp)):
        with pytest.raises(ValueError, match="not found"):
            await _fetch_asn_name(99999999)


@pytest.mark.asyncio
async def test_fetch_asn_name_429_raises_runtime_error():
    resp = _make_mock_response(429)
    with patch("server.httpx.AsyncClient", return_value=MockAsyncClient(resp)):
        with pytest.raises(RuntimeError, match="Rate limited"):
            await _fetch_asn_name(13335)


@pytest.mark.asyncio
async def test_fetch_asn_name_500_retries_then_raises():
    """5xx errors should be retried; after all retries a RuntimeError is raised."""
    resp = _make_mock_response(500)

    class AlwaysFailClient(MockAsyncClient):
        async def get(self, url):
            return self._response

    # Patch asyncio.sleep to avoid actual delays in tests
    with patch("server.httpx.AsyncClient", return_value=AlwaysFailClient(resp)):
        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(RuntimeError, match="upstream error"):
                await _fetch_asn_name(13335)


@pytest.mark.asyncio
async def test_fetch_asn_name_unexpected_status_raises():
    resp = _make_mock_response(403)
    with patch("server.httpx.AsyncClient", return_value=MockAsyncClient(resp)):
        with pytest.raises(RuntimeError, match="Unexpected response"):
            await _fetch_asn_name(13335)


# ---------------------------------------------------------------------------
# asn_lookup MCP tool – end-to-end with mocked _fetch_asn_name
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_asn_lookup_valid_numeric():
    with patch("server._fetch_asn_name", new_callable=AsyncMock, return_value="CLOUDFLARENET"):
        result = await asn_lookup("13335")
    assert result == "CLOUDFLARENET"


@pytest.mark.asyncio
async def test_asn_lookup_valid_as_prefix():
    with patch("server._fetch_asn_name", new_callable=AsyncMock, return_value="CLOUDFLARENET"):
        result = await asn_lookup("AS13335")
    assert result == "CLOUDFLARENET"


@pytest.mark.asyncio
async def test_asn_lookup_invalid_input_returns_error():
    result = await asn_lookup("not-a-number")
    assert result.startswith("Error:")


@pytest.mark.asyncio
async def test_asn_lookup_zero_returns_error():
    result = await asn_lookup("0")
    assert result.startswith("Error:")


@pytest.mark.asyncio
async def test_asn_lookup_not_found_returns_error():
    with patch(
        "server._fetch_asn_name",
        new_callable=AsyncMock,
        side_effect=ValueError("ASN 99999999 not found"),
    ):
        result = await asn_lookup("99999999")
    assert "Error:" in result
    assert "not found" in result


@pytest.mark.asyncio
async def test_asn_lookup_rate_limited_returns_error():
    with patch(
        "server._fetch_asn_name",
        new_callable=AsyncMock,
        side_effect=RuntimeError("Rate limited by BGPKit API"),
    ):
        result = await asn_lookup("13335")
    assert "Error:" in result
    assert "Rate limited" in result


@pytest.mark.asyncio
async def test_asn_lookup_upstream_failure_returns_error():
    with patch(
        "server._fetch_asn_name",
        new_callable=AsyncMock,
        side_effect=RuntimeError("BGPKit API returned 503 – upstream error"),
    ):
        result = await asn_lookup("13335")
    assert "Error:" in result

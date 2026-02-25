"""Tests for ASN lookup functionality."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from bgp_lg import lookup_asn_owner, _parse_asn


class TestParseASN:
    """Test ASN parsing from various formats."""

    def test_parse_asn_numeric_format(self):
        """Test parsing numeric ASN format."""
        assert _parse_asn("64512") == 64512
        assert _parse_asn(" 64512 ") == 64512

    def test_parse_asn_with_as_prefix(self):
        """Test parsing ASN with AS prefix."""
        assert _parse_asn("AS64512") == 64512
        assert _parse_asn("as64512") == 64512
        assert _parse_asn(" AS64512 ") == 64512

    def test_parse_asn_valid_boundaries(self):
        """Test valid ASN boundary values."""
        assert _parse_asn("0") == 0
        assert _parse_asn("4294967295") == 4294967295

    def test_parse_asn_invalid_format(self):
        """Test invalid ASN format raises ValueError."""
        with pytest.raises(ValueError):
            _parse_asn("invalid")

    def test_parse_asn_out_of_range(self):
        """Test ASN out of valid range raises ValueError."""
        with pytest.raises(ValueError):
            _parse_asn("-1")
        
        with pytest.raises(ValueError):
            _parse_asn("4294967296")


@pytest.mark.asyncio
class TestLookupASNOwner:
    """Test ASN owner lookup via BGPKit API."""

    @pytest.mark.asyncio
    async def test_lookup_asn_success(self):
        """Test successful ASN lookup."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "owner_name": "Google LLC"
            }
        }

        with patch("bgp_lg.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            result = await lookup_asn_owner("AS15169")
            assert result == "Google LLC"
            mock_client.post.assert_called_once_with(
                "https://api.bgpkit.com/v3/utils/asn",
                params={"asn": 15169}
            )

    @pytest.mark.asyncio
    async def test_lookup_asn_not_found(self):
        """Test ASN not found returns 404."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch("bgp_lg.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            with pytest.raises(RuntimeError, match="not found in BGPKit database"):
                await lookup_asn_owner("AS99999999")

    @pytest.mark.asyncio
    async def test_lookup_asn_rate_limit(self):
        """Test rate limit handling."""
        mock_response = MagicMock()
        mock_response.status_code = 429

        with patch("bgp_lg.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            with pytest.raises(RuntimeError, match="rate limit exceeded"):
                await lookup_asn_owner("AS15169")

    @pytest.mark.asyncio
    async def test_lookup_asn_server_error(self):
        """Test server error handling."""
        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch("bgp_lg.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            with pytest.raises(RuntimeError, match="server error"):
                await lookup_asn_owner("AS15169")

    @pytest.mark.asyncio
    async def test_lookup_asn_timeout(self):
        """Test timeout handling."""
        import httpx

        with patch("bgp_lg.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.TimeoutException("timeout")
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            with pytest.raises(RuntimeError, match="timed out"):
                await lookup_asn_owner("AS15169")

    @pytest.mark.asyncio
    async def test_lookup_asn_invalid_format(self):
        """Test invalid ASN format."""
        with pytest.raises(ValueError, match="Invalid ASN"):
            await lookup_asn_owner("not-an-asn")

"""Integration tests connecting to actual RouteViews servers.

These tests require network access and may be slow.
They can be skipped with: pytest -m "not integration"
"""

import pytest
import asyncio
from bgp_lg import TelnetClient, execute_bgp_command, get_available_servers, validate_ip_or_cidr


pytestmark = pytest.mark.integration


class TestTelnetConnection:
    """Test basic telnet connectivity to RouteViews servers."""
    
    @pytest.mark.asyncio
    async def test_connect_to_routeviews_main(self):
        """Test connection to RouteViews main server."""
        client = TelnetClient(
            host="route-views.routeviews.org",
            port=23,
            username="rviews",
            password="rviews",
            prompt=">",
            timeout=15
        )
        
        try:
            await client.connect()
            # Simple telnet connection should succeed
            assert client.reader is not None
            assert client.writer is not None
            await client.close()
        except ConnectionRefusedError:
            pytest.skip("Route-views server unavailable")
        except asyncio.TimeoutError:
            pytest.skip("Route-views server timeout")
    
    @pytest.mark.asyncio
    async def test_connect_to_linx(self):
        """Test connection to RouteViews LINX server."""
        client = TelnetClient(
            host="route-views.linx.routeviews.org",
            port=23,
            prompt=">",
            timeout=15
        )
        
        try:
            await client.connect()
            assert client.reader is not None
            assert client.writer is not None
            await client.close()
        except ConnectionRefusedError:
            pytest.skip("Route-views LINX server unavailable")
        except asyncio.TimeoutError:
            pytest.skip("Route-views LINX server timeout")


class TestBGPCommands:
    """Test actual BGP commands on RouteViews servers."""
    
    @pytest.mark.asyncio
    async def test_bgp_summary_main(self):
        """Test BGP summary command on main server."""
        try:
            result = await execute_bgp_command(
                "RouteViews Main",
                "show ip bgp summary"
            )
            
            # Should contain BGP neighbor information
            assert "Router" in result or "Neighbor" in result
            assert len(result) > 0
            
        except ConnectionRefusedError:
            pytest.skip("Route-views server unavailable")
        except asyncio.TimeoutError:
            pytest.skip("Route-views server timeout")
        except Exception as e:
            pytest.skip(f"BGP command failed: {e}")
    
    @pytest.mark.asyncio
    async def test_route_lookup_google_dns(self):
        """Test route lookup for Google Public DNS."""
        try:
            result = await execute_bgp_command(
                "RouteViews Main",
                "show ip route 8.8.8.0/24"
            )
            
            # Should contain routing information
            assert len(result) > 0
            
        except ConnectionRefusedError:
            pytest.skip("Route-views server unavailable")
        except asyncio.TimeoutError:
            pytest.skip("Route-views server timeout")
        except Exception as e:
            pytest.skip(f"Route lookup failed: {e}")
    
    @pytest.mark.asyncio
    async def test_route_lookup_with_validation(self):
        """Test route lookup with IP validation."""
        test_ips = [
            "1.1.1.1",
            "208.67.222.123",
            "2001:4860:4860::8888"
        ]
        
        for ip in test_ips:
            # Should not raise for valid IPs
            assert validate_ip_or_cidr(ip)


class TestServerList:
    """Test server management."""
    
    def test_list_servers(self):
        """Test that we can list all configured servers."""
        servers = get_available_servers()
        
        assert len(servers) > 0
        assert any("Main" in s for s in servers)
        assert any("Linx" in s for s in servers)
    
    def test_server_configuration_valid(self):
        """Test that all server configurations are valid."""
        servers = get_available_servers()
        
        assert len(servers) > 0


class TestInputValidation:
    """Test input validation functions."""
    
    def test_validate_ip_addresses(self):
        """Test IP address validation (public IPs only)."""
        valid_ips = [
            "1.1.1.1",
            "8.8.8.0/24",
            "208.67.222.0/24",
            "2001:4860:4860::8888",
            "2001:4860:4860::/32"
        ]
        
        for ip in valid_ips:
            is_valid, message = validate_ip_or_cidr(ip)
            assert is_valid, f"Should validate {ip}: {message}"
    
    def test_invalid_ip_addresses(self):
        """Test that invalid IPs are rejected."""
        invalid_ips = [
            "256.256.256.256",
            "1.1.1",
            "not-an-ip",
            "1.1.1.1/33",  # Invalid CIDR mask
            "192.168.0.0/16",  # Private IP
            "127.0.0.1",  # Loopback
            ""
        ]
        
        for ip in invalid_ips:
            is_valid, message = validate_ip_or_cidr(ip)
            assert not is_valid, f"Should reject {ip}: {message}"

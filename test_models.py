"""Tests for Pydantic models and updated validation utilities."""

import pytest
from pydantic import ValidationError

from models import AppConfig, RouteLookupRequest, RouteLookupResponse, ServerConfig
from validation import validate_ip_or_cidr, get_ip_type


# ---------------------------------------------------------------------------
# ServerConfig tests
# ---------------------------------------------------------------------------

class TestServerConfig:
    def test_valid_server_config(self):
        cfg = ServerConfig(name="Test", host="example.com")
        assert cfg.name == "Test"
        assert cfg.host == "example.com"
        assert cfg.port == 23
        assert cfg.enabled is True
        assert cfg.username == ""
        assert cfg.timeout == 15

    def test_server_config_custom_values(self):
        cfg = ServerConfig(
            name="MyServer",
            host="1.2.3.4",
            port=2323,
            username="admin",
            password="secret",
            prompt=">",
            timeout=30,
            enabled=False,
            connection_method="telnet",
        )
        assert cfg.port == 2323
        assert cfg.enabled is False
        assert cfg.username == "admin"

    def test_server_config_missing_required_fields(self):
        with pytest.raises(ValidationError):
            ServerConfig(host="example.com")  # name is required

        with pytest.raises(ValidationError):
            ServerConfig(name="Test")  # host is required


# ---------------------------------------------------------------------------
# AppConfig tests
# ---------------------------------------------------------------------------

class TestAppConfig:
    def test_empty_config(self):
        cfg = AppConfig()
        assert cfg.servers == []

    def test_config_with_servers(self):
        cfg = AppConfig(
            servers=[
                {"name": "Server1", "host": "host1.example.com"},
                {"name": "Server2", "host": "host2.example.com", "port": 2323},
            ]
        )
        assert len(cfg.servers) == 2
        assert isinstance(cfg.servers[0], ServerConfig)
        assert cfg.servers[1].port == 2323

    def test_app_config_validates_nested_server_configs(self):
        raw = {
            "servers": [
                {
                    "name": "RouteViews Linx",
                    "host": "route-views.linx.routeviews.org",
                    "port": 23,
                    "connection_method": "telnet",
                    "username": "",
                    "password": "",
                    "prompt": ">",
                    "timeout": 15,
                    "enabled": True,
                }
            ]
        }
        cfg = AppConfig.model_validate(raw)
        assert cfg.servers[0].name == "RouteViews Linx"
        assert isinstance(cfg.servers[0], ServerConfig)


# ---------------------------------------------------------------------------
# RouteLookupRequest validation tests
# ---------------------------------------------------------------------------

class TestRouteLookupRequest:
    def test_valid_ipv4(self):
        req = RouteLookupRequest(destination="8.8.8.8")
        assert req.destination == "8.8.8.8"
        assert req.server == "RouteViews Linx"

    def test_valid_ipv6(self):
        req = RouteLookupRequest(destination="2001:4860:4860::8888")
        assert req.destination == "2001:4860:4860::8888"

    def test_valid_cidr_v4(self):
        req = RouteLookupRequest(destination="8.8.8.0/24")
        assert req.destination == "8.8.8.0/24"

    def test_valid_cidr_v6(self):
        req = RouteLookupRequest(destination="2001:4860::/32")
        assert req.destination == "2001:4860::/32"

    def test_strips_whitespace(self):
        req = RouteLookupRequest(destination="  8.8.8.8  ")
        assert req.destination == "8.8.8.8"

    def test_private_ipv4_rejected(self):
        with pytest.raises(ValidationError):
            RouteLookupRequest(destination="192.168.1.1")

    def test_loopback_rejected(self):
        with pytest.raises(ValidationError):
            RouteLookupRequest(destination="127.0.0.1")

    def test_private_cidr_rejected(self):
        with pytest.raises(ValidationError):
            RouteLookupRequest(destination="10.0.0.0/8")

    def test_invalid_ip_rejected(self):
        with pytest.raises(ValidationError):
            RouteLookupRequest(destination="not-an-ip")

    def test_custom_server(self):
        req = RouteLookupRequest(destination="1.1.1.1", server="RouteViews Main")
        assert req.server == "RouteViews Main"


# ---------------------------------------------------------------------------
# RouteLookupResponse tests
# ---------------------------------------------------------------------------

class TestRouteLookupResponse:
    def test_response_model(self):
        resp = RouteLookupResponse(
            destination="8.8.8.8",
            server="RouteViews Linx",
            result="BGP route data...",
        )
        assert resp.destination == "8.8.8.8"
        assert resp.server == "RouteViews Linx"
        assert resp.result == "BGP route data..."

    def test_response_serialization(self):
        resp = RouteLookupResponse(
            destination="1.1.1.0/24",
            server="RouteViews Equinix",
            result="some data",
        )
        d = resp.model_dump()
        assert d == {
            "destination": "1.1.1.0/24",
            "server": "RouteViews Equinix",
            "result": "some data",
        }


# ---------------------------------------------------------------------------
# validate_ip_or_cidr (uses Pydantic internally now)
# ---------------------------------------------------------------------------

class TestValidateIpOrCidr:
    def test_valid_public_ipv4(self):
        valid, msg = validate_ip_or_cidr("8.8.8.8")
        assert valid is True
        assert "Valid IP address" in msg

    def test_valid_public_ipv6(self):
        valid, msg = validate_ip_or_cidr("2001:4860:4860::8888")
        assert valid is True

    def test_valid_public_cidr(self):
        valid, msg = validate_ip_or_cidr("8.8.8.0/24")
        assert valid is True
        assert "Valid CIDR subnet" in msg

    def test_private_ip_invalid(self):
        valid, msg = validate_ip_or_cidr("192.168.1.1")
        assert valid is False
        assert "not public" in msg

    def test_loopback_invalid(self):
        valid, msg = validate_ip_or_cidr("127.0.0.1")
        assert valid is False

    def test_private_cidr_invalid(self):
        valid, msg = validate_ip_or_cidr("10.0.0.0/8")
        assert valid is False

    def test_invalid_format(self):
        valid, msg = validate_ip_or_cidr("not-an-ip")
        assert valid is False

    def test_whitespace_trimmed(self):
        valid, msg = validate_ip_or_cidr("  8.8.8.8  ")
        assert valid is True


# ---------------------------------------------------------------------------
# get_ip_type (unchanged logic, just verify still works)
# ---------------------------------------------------------------------------

class TestGetIpType:
    def test_ipv4(self):
        assert get_ip_type("8.8.8.8") == "IPv4"

    def test_ipv6(self):
        assert get_ip_type("2001:4860:4860::8888") == "IPv6"

    def test_ipv4_cidr(self):
        assert get_ip_type("8.8.8.0/24") == "IPv4"

    def test_ipv6_cidr(self):
        assert get_ip_type("2001:db8::/32") == "IPv6"

    def test_invalid(self):
        assert get_ip_type("not-an-ip") == "unknown"

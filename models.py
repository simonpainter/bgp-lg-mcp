"""Pydantic models for BGP Looking Glass data exchange and validation."""

import ipaddress

from pydantic import BaseModel, field_validator


class ServerConfig(BaseModel):
    """Configuration for a single BGP looking-glass server."""

    name: str
    host: str
    port: int = 23
    connection_method: str = "telnet"
    username: str = ""
    password: str = ""
    prompt: str = ">"
    timeout: int = 15
    enabled: bool = True


class AppConfig(BaseModel):
    """Application configuration containing list of servers."""

    servers: list[ServerConfig] = []


class RouteLookupRequest(BaseModel):
    """Request model for a BGP route lookup."""

    destination: str
    server: str = "RouteViews Linx"

    @field_validator("destination")
    @classmethod
    def validate_destination(cls, v: str) -> str:
        """Validate that destination is a public IPv4/IPv6 address or CIDR subnet."""
        v = v.strip()
        if "/" in v:
            try:
                network = ipaddress.ip_network(v, strict=False)
            except ValueError:
                raise ValueError(f"Invalid IP address or CIDR notation: {v}")
            if network.is_private or network.is_loopback or network.is_link_local:
                raise ValueError(f"CIDR subnet {v} is not public")
        else:
            try:
                ip = ipaddress.ip_address(v)
            except ValueError:
                raise ValueError(f"Invalid IP address or CIDR notation: {v}")
            if ip.is_private or ip.is_loopback or ip.is_link_local:
                raise ValueError(f"Address {v} is not public")
        return v


class RouteLookupResponse(BaseModel):
    """Response model for a BGP route lookup."""

    destination: str
    server: str
    result: str

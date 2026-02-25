"""Pydantic models for BGP Looking Glass JSON responses."""

from typing import Optional, List, Any
from pydantic import BaseModel, Field


# Base response models

class ErrorResponse(BaseModel):
    """Error response model."""
    type: str = "error"
    error: str


class BGPRoute(BaseModel):
    """Represents a single BGP route entry."""
    prefix: Optional[str] = None
    metric: Optional[str] = None
    next_hop: Optional[str] = None
    as_path: Optional[str] = None


class RouteLookupResponse(BaseModel):
    """Response model for route_lookup tool."""
    type: str = "route_lookup"
    raw_output: str
    parsed_routes: List[BGPRoute] = Field(default_factory=list)
    parse_status: str = "partial"


class BGPSummaryResponse(BaseModel):
    """Response model for bgp_summary tool."""
    type: str = "bgp_summary"
    raw_output: str
    router_id: Optional[str] = None
    local_as: Optional[int] = None
    neighbor_count: int = 0
    established_count: int = 0
    neighbors: List[dict] = Field(default_factory=list)
    parse_status: str = "partial"


class ASNOwnerResponse(BaseModel):
    """Response model for asn_owner tool."""
    type: str = "asn_owner"
    asn: str
    owner: str


class IPLookupResponse(BaseModel):
    """Response model for ip_lookup tool."""
    type: str = "ip_lookup"
    ip: str
    country: Optional[str] = None
    asn: Optional[int] = None
    prefix: Optional[str] = None
    name: Optional[str] = None
    rpki: Optional[str] = None
    updated_at: Optional[str] = None


class ServerInfo(BaseModel):
    """Information about a BGP server."""
    name: str
    host: str
    port: int
    connection_method: str
    enabled: bool


class ListServersResponse(BaseModel):
    """Response model for list_servers tool."""
    type: str = "server_list"
    servers: List[ServerInfo]

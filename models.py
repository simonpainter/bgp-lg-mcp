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


class PingStats(BaseModel):
    """Ping statistics."""
    sent: int
    received: int
    success_rate: float = Field(..., description="Success rate as percentage (0-100)")
    min_ms: Optional[float] = None
    avg_ms: Optional[float] = None
    max_ms: Optional[float] = None


class PingResponse(BaseModel):
    """Response model for ping tool."""
    type: str = "ping"
    ip: str
    server: str
    stats: PingStats
    raw_output: str


class TracerouteHop(BaseModel):
    """Represents a single hop in traceroute."""
    hop_number: int
    host: Optional[str] = None
    ip: Optional[str] = None
    asn: Optional[int] = None
    times_ms: List[float] = Field(default_factory=list, description="Round-trip times in milliseconds")
    rtt_avg_ms: Optional[float] = None


class TracerouteResponse(BaseModel):
    """Response model for traceroute tool."""
    type: str = "traceroute"
    ip: str
    target_hostname: Optional[str] = None
    server: str
    total_hops: int
    hops: List[TracerouteHop] = Field(default_factory=list)
    raw_output: str

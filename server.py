"""BGP Looking Glass MCP Server."""

import json
import os
import sys

from mcp.server.fastmcp import FastMCP

from bgp_lg import (
    validate_ip_or_cidr,
    get_ip_type,
    load_config,
    get_available_servers,
    execute_bgp_command,
    lookup_asn_owner,
    lookup_ip_geolocation,
    _parse_bgp_route_lookup,
    _parse_bgp_summary,
    _parse_ping_output,
    _parse_traceroute_output,
)
from models import (
    ErrorResponse,
    RouteLookupResponse,
    BGPSummaryResponse,
    ASNOwnerResponse,
    IPLookupResponse,
    ListServersResponse,
    ServerInfo,
    PingResponse,
    PingStats,
    TracerouteResponse,
    TracerouteHop,
)



# Create the MCP server
mcp = FastMCP("BGP Looking Glass")


@mcp.tool()
async def route_lookup(destination: str, server: str = "RouteViews Linx", format: str = "text") -> str:
    """Look up a route on a BGP looking-glass server.

    Args:
        destination: IPv4/IPv6 address or CIDR subnet (e.g., 1.1.1.1 or 1.1.1.0/24).
        server: Name of the BGP server to query (defaults to RouteViews Linx).
                Call list_servers() to see all available servers and their response times.
        format: Response format - "text" (default) or "json" for structured output.

    Returns:
        Route lookup results from the BGP server (text or JSON format).
    """
    # Validate destination
    is_valid, message = validate_ip_or_cidr(destination)
    if not is_valid:
        error = ErrorResponse(error=message)
        if format.lower() == "json":
            return error.model_dump_json(indent=2)
        return f"Error: {message}"

    try:
        command = f"show ip bgp {destination}"
        response = await execute_bgp_command(server, command)
        
        # Return JSON format if requested
        if format.lower() == "json":
            parsed: RouteLookupResponse = _parse_bgp_route_lookup(response)
            return parsed.model_dump_json(indent=2)
        
        return response
    except ValueError as e:
        error = ErrorResponse(error=f"Configuration error: {str(e)}")
        if format.lower() == "json":
            return error.model_dump_json(indent=2)
        return f"Configuration error: {str(e)}"
    except ConnectionError as e:
        error_msg = f"Connection error: {str(e)} - The BGP server may be unreachable or not accepting connections"
        error = ErrorResponse(error=error_msg)
        if format.lower() == "json":
            return error.model_dump_json(indent=2)
        return error_msg
    except RuntimeError as e:
        error = ErrorResponse(error=f"Query error: {str(e)}")
        if format.lower() == "json":
            return error.model_dump_json(indent=2)
        return f"Query error: {str(e)}"
    except Exception as e:
        error = ErrorResponse(error=f"Unexpected error: {type(e).__name__}: {str(e)}")
        if format.lower() == "json":
            return error.model_dump_json(indent=2)
        return f"Unexpected error: {type(e).__name__}: {str(e)}"


@mcp.tool()
async def bgp_summary(server: str = "RouteViews Linx", format: str = "text") -> str:
    """Get BGP summary information from a route server.

    Returns information about the BGP router including neighbor counts, 
    AS number, router ID, and other BGP statistics.

    Args:
        server: Name of the BGP server to query (defaults to RouteViews Linx).
                Call list_servers() to see all available servers and their response times.
        format: Response format - "text" (default) or "json" for structured output.

    Returns:
        BGP summary output from the server showing router statistics and neighbors.
    """
    try:
        command = "show ip bgp summary"
        response = await execute_bgp_command(server, command)
        
        # Return JSON format if requested
        if format.lower() == "json":
            parsed: BGPSummaryResponse = _parse_bgp_summary(response)
            return parsed.model_dump_json(indent=2)
        
        return response        
    except ValueError as e:
        error = ErrorResponse(error=f"Configuration error: {str(e)}")
        if format.lower() == "json":
            return error.model_dump_json(indent=2)
        return f"Configuration error: {str(e)}"
    except ConnectionError as e:
        error_msg = f"Connection error: {str(e)} - The BGP server may be unreachable or not accepting connections"
        error = ErrorResponse(error=error_msg)
        if format.lower() == "json":
            return error.model_dump_json(indent=2)
        return error_msg
    except RuntimeError as e:
        error = ErrorResponse(error=f"Query error: {str(e)}")
        if format.lower() == "json":
            return error.model_dump_json(indent=2)
        return f"Query error: {str(e)}"
    except Exception as e:
        error = ErrorResponse(error=f"Unexpected error: {type(e).__name__}: {str(e)}")
        if format.lower() == "json":
            return error.model_dump_json(indent=2)
        return f"Unexpected error: {type(e).__name__}: {str(e)}"


@mcp.tool()
@mcp.tool()
def list_servers(format: str = "text") -> str:
    """List all configured BGP looking-glass servers.

    Args:
        format: Response format - "text" (default) or "json" for structured output.

    Returns:
        List of configured servers with their details.
    """
    try:
        config_data = load_config()
        servers = config_data.get("servers", [])
        
        if not servers:
            if format.lower() == "json":
                response = ListServersResponse(servers=[])
                return response.model_dump_json(indent=2)
            return "No servers configured."
        
        if format.lower() == "json":
            server_infos = [
                ServerInfo(
                    name=server['name'],
                    host=server['host'],
                    port=server.get('port', 23),
                    connection_method=server.get('connection_method', 'unknown'),
                    enabled=server.get('enabled', True),
                    supports_ping=server.get('supports_ping', False),
                    supports_traceroute=server.get('supports_traceroute', False)
                )
                for server in servers
            ]
            response = ListServersResponse(servers=server_infos)
            return response.model_dump_json(indent=2)
        
        # Text format
        output = "Configured BGP Looking-Glass Servers:\n"
        for server in servers:
            status = "enabled" if server.get("enabled", True) else "disabled"
            output += f"\n- {server['name']} ({status})\n"
            output += f"  Host: {server['host']}:{server.get('port', 23)}\n"
            output += f"  Method: {server.get('connection_method', 'unknown')}\n"
            
            # Show ping and traceroute capabilities
            ping_support = "✓ yes" if server.get('supports_ping', False) else "✗ no"
            trace_support = "✓ yes" if server.get('supports_traceroute', False) else "✗ no"
            output += f"  Ping: {ping_support}\n"
            output += f"  Traceroute: {trace_support}\n"
        
        return output
    except Exception as e:
        error = ErrorResponse(error=f"Error listing servers: {str(e)}")
        if format.lower() == "json":
            return error.model_dump_json(indent=2)
        return f"Error listing servers: {str(e)}"


@mcp.tool()
async def asn_owner(asn: str, format: str = "text") -> str:
    """Look up the owner name for an Autonomous System Number (ASN).

    Uses the BGPKit public API to retrieve ASN ownership information.

    Args:
        asn: Autonomous System Number in format "AS123" or "123" (e.g., "AS64512" or "64512").
        format: Response format - "text" (default) or "json" for structured output.

    Returns:
        Owner name for the ASN (text or JSON format).
    """
    try:
        owner_name = await lookup_asn_owner(asn)
        
        if format.lower() == "json":
            response: ASNOwnerResponse = ASNOwnerResponse(asn=asn, owner=owner_name)
            return response.model_dump_json(indent=2)
        
        return f"ASN {asn}: {owner_name}"
    except ValueError as e:
        error = ErrorResponse(error=f"Invalid ASN: {str(e)}")
        if format.lower() == "json":
            return error.model_dump_json(indent=2)
        return f"Invalid ASN: {str(e)}"
    except RuntimeError as e:
        error = ErrorResponse(error=f"Lookup error: {str(e)}")
        if format.lower() == "json":
            return error.model_dump_json(indent=2)
        return f"Lookup error: {str(e)}"
    except Exception as e:
        error = ErrorResponse(error=f"Unexpected error: {type(e).__name__}: {str(e)}")
        if format.lower() == "json":
            return error.model_dump_json(indent=2)
        return f"Unexpected error: {type(e).__name__}: {str(e)}"


@mcp.tool()
async def ip_lookup(ip: str, format: str = "text") -> str:
    """Look up geolocation and BGP metadata for an IP address.

    Uses the BGPKit public API to retrieve IP geolocation information including
    country, covering prefix, ASN, and RPKI validation status.

    Args:
        ip: IPv4 or IPv6 address (e.g., "8.8.8.8" or "2001:4860:4860::8888").
            Must be a public address (not private or reserved).
        format: Response format - "text" (default) or "json" for structured output.

    Returns:
        Dictionary-formatted string with: ip, country, asn, prefix, name, rpki, updated_at
    """
    try:
        result = await lookup_ip_geolocation(ip)
        
        if format.lower() == "json":
            response: IPLookupResponse = IPLookupResponse(**result)
            return response.model_dump_json(indent=2)
        
        # Format response as text
        output = f"IP Lookup: {result['ip']}\n"
        output += f"Country: {result['country']}\n"
        output += f"ASN: {result['asn']}\n"
        output += f"Prefix: {result['prefix']}\n"
        output += f"Name: {result['name']}\n"
        output += f"RPKI Status: {result['rpki']}\n"
        output += f"Updated: {result['updated_at']}"
        
        return output
    except ValueError as e:
        error = ErrorResponse(error=f"Invalid IP address: {str(e)}")
        if format.lower() == "json":
            return error.model_dump_json(indent=2)
        return f"Invalid IP address: {str(e)}"
    except RuntimeError as e:
        error = ErrorResponse(error=f"Lookup error: {str(e)}")
        if format.lower() == "json":
            return error.model_dump_json(indent=2)
        return f"Lookup error: {str(e)}"
    except Exception as e:
        error = ErrorResponse(error=f"Unexpected error: {type(e).__name__}: {str(e)}")
        if format.lower() == "json":
            return error.model_dump_json(indent=2)
        return f"Unexpected error: {type(e).__name__}: {str(e)}"


@mcp.tool()
async def ping_host(ip: str, server: str = "RouteViews Linx", format: str = "text") -> str:
    """Ping an IP address from a BGP looking-glass server.

    Args:
        ip: IPv4 or IPv6 address to ping.
        server: Name of the BGP server to use for pinging (defaults to RouteViews Linx).
                Call list_servers() to see all available servers.
        format: Response format - "text" (default) or "json" for structured output.

    Returns:
        Ping statistics including success rate, packet counts, and round-trip times.
    """
    # Validate IP
    is_valid, message = validate_ip_or_cidr(ip)
    if not is_valid:
        error = ErrorResponse(error=message)
        if format.lower() == "json":
            return error.model_dump_json(indent=2)
        return f"Error: {message}"

    try:
        # Get config to check server capabilities
        config = load_config()
        servers_info = config.get("servers", {})
        
        if server not in servers_info:
            raise ValueError(f"Server '{server}' not found. Call list_servers() to see available servers.")
        
        server_info = servers_info[server]
        if not server_info.get("supports_ping", False):
            raise ValueError(f"Server '{server}' does not support ping command.")
        
        # Execute ping command
        command = f"ping {ip}"
        response = await execute_bgp_command(server, command)
        
        # Parse ping output
        ping_stats = _parse_ping_output(response)
        
        # Return JSON format if requested
        if format.lower() == "json":
            ping_stats_obj = PingStats(
                sent=ping_stats["sent"],
                received=ping_stats["received"],
                success_rate=ping_stats["success_rate"],
                min_ms=ping_stats["min_ms"],
                avg_ms=ping_stats["avg_ms"],
                max_ms=ping_stats["max_ms"],
            )
            ping_response = PingResponse(
                type="ping",
                ip=ip,
                server=server,
                stats=ping_stats_obj,
                raw_output=response,
            )
            return ping_response.model_dump_json(indent=2)
        
        # Format response as text
        output = f"Ping Results for {ip}\n"
        output += f"Server: {server}\n"
        output += f"Packets sent: {ping_stats['sent']}\n"
        output += f"Packets received: {ping_stats['received']}\n"
        output += f"Success rate: {ping_stats['success_rate']}%\n"
        if ping_stats["min_ms"] is not None:
            output += f"Round-trip times (ms): min={ping_stats['min_ms']}, avg={ping_stats['avg_ms']}, max={ping_stats['max_ms']}"
        
        return output
    except ValueError as e:
        error = ErrorResponse(error=str(e))
        if format.lower() == "json":
            return error.model_dump_json(indent=2)
        return f"Error: {str(e)}"
    except ConnectionError as e:
        error_msg = f"Connection error: {str(e)} - The BGP server may be unreachable or not accepting connections"
        error = ErrorResponse(error=error_msg)
        if format.lower() == "json":
            return error.model_dump_json(indent=2)
        return error_msg
    except RuntimeError as e:
        error = ErrorResponse(error=f"Ping error: {str(e)}")
        if format.lower() == "json":
            return error.model_dump_json(indent=2)
        return f"Ping error: {str(e)}"
    except Exception as e:
        error = ErrorResponse(error=f"Unexpected error: {type(e).__name__}: {str(e)}")
        if format.lower() == "json":
            return error.model_dump_json(indent=2)
        return f"Unexpected error: {type(e).__name__}: {str(e)}"


@mcp.tool()
async def traceroute_host(ip: str, server: str = "RouteViews Linx", format: str = "text") -> str:
    """Trace the route to an IP address from a BGP looking-glass server.

    Args:
        ip: IPv4 or IPv6 address to trace route to.
        server: Name of the BGP server to use for traceroute (defaults to RouteViews Linx).
                Call list_servers() to see all available servers.
        format: Response format - "text" (default) or "json" for structured output.

    Returns:
        Traceroute results showing hops, hostnames, IPs, ASNs, and response times.
    """
    # Validate IP
    is_valid, message = validate_ip_or_cidr(ip)
    if not is_valid:
        error = ErrorResponse(error=message)
        if format.lower() == "json":
            return error.model_dump_json(indent=2)
        return f"Error: {message}"

    try:
        # Get config to check server capabilities
        config = load_config()
        servers_info = config.get("servers", {})
        
        if server not in servers_info:
            raise ValueError(f"Server '{server}' not found. Call list_servers() to see available servers.")
        
        server_info = servers_info[server]
        if not server_info.get("supports_traceroute", False):
            raise ValueError(f"Server '{server}' does not support traceroute command.")
        
        # Execute traceroute command
        command = f"traceroute {ip}"
        response = await execute_bgp_command(server, command)
        
        # Parse traceroute output
        traceroute_data = _parse_traceroute_output(response, ip)
        
        # Return JSON format if requested
        if format.lower() == "json":
            hops = [
                TracerouteHop(
                    hop_number=hop["hop_number"],
                    host=hop["host"],
                    ip=hop["ip"],
                    asn=hop["asn"],
                    times_ms=hop["times_ms"],
                    rtt_avg_ms=hop["rtt_avg_ms"],
                )
                for hop in traceroute_data["hops"]
            ]
            traceroute_response = TracerouteResponse(
                type="traceroute",
                ip=ip,
                target_hostname=traceroute_data["target_hostname"],
                server=server,
                total_hops=traceroute_data["total_hops"],
                hops=hops,
                raw_output=response,
            )
            return traceroute_response.model_dump_json(indent=2)
        
        # Format response as text
        output = f"Traceroute to {ip}\n"
        output += f"Server: {server}\n"
        if traceroute_data["target_hostname"]:
            output += f"Target hostname: {traceroute_data['target_hostname']}\n"
        output += f"Total hops: {traceroute_data['total_hops']}\n\n"
        
        for hop in traceroute_data["hops"]:
            output += f"{hop['hop_number']:2d}. "
            if hop["host"] == "*":
                output += "* (no response)"
            else:
                if hop["host"]:
                    output += f"{hop['host']}"
                if hop["ip"]:
                    output += f" ({hop['ip']})"
                if hop["asn"]:
                    output += f" [AS {hop['asn']}]"
                if hop["times_ms"]:
                    times_str = " ".join([f"{t:.1f}" for t in hop["times_ms"]])
                    output += f" {times_str} ms"
            output += "\n"
        
        return output
    except ValueError as e:
        error = ErrorResponse(error=str(e))
        if format.lower() == "json":
            return error.model_dump_json(indent=2)
        return f"Error: {str(e)}"
    except ConnectionError as e:
        error_msg = f"Connection error: {str(e)} - The BGP server may be unreachable or not accepting connections"
        error = ErrorResponse(error=error_msg)
        if format.lower() == "json":
            return error.model_dump_json(indent=2)
        return error_msg
    except RuntimeError as e:
        error = ErrorResponse(error=f"Traceroute error: {str(e)}")
        if format.lower() == "json":
            return error.model_dump_json(indent=2)
        return f"Traceroute error: {str(e)}"
    except Exception as e:
        error = ErrorResponse(error=f"Unexpected error: {type(e).__name__}: {str(e)}")
        if format.lower() == "json":
            return error.model_dump_json(indent=2)
        return f"Unexpected error: {type(e).__name__}: {str(e)}"


# Create ASGI application for production deployment
app = mcp.streamable_http_app()


if __name__ == "__main__":
    # Support environment variables for configuration
    transport_mode = os.getenv("TRANSPORT_MODE", "streamable-http").lower()
    server_host = os.getenv("SERVER_HOST", "127.0.0.1")
    server_port = int(os.getenv("SERVER_PORT", "8000"))
    
    # Validate transport mode
    valid_transports = ["stdio", "sse", "streamable-http"]
    if transport_mode not in valid_transports:
        transport_mode = "streamable-http"
    
    # Check for stdio mode (for MCP clients) via argument or environment variable
    if (len(sys.argv) > 1 and sys.argv[1] == "--stdio") or transport_mode == "stdio":
        mcp.run()
    else:
        # Start an HTTP server (default: streamable-http)
        mcp.run(transport=transport_mode)  # type: ignore

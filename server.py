"""BGP Looking Glass MCP Server."""

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
)


# Create the MCP server
mcp = FastMCP("BGP Looking Glass")


@mcp.tool()
async def route_lookup(destination: str, server: str = "RouteViews Linx") -> str:
    """Look up a route on a BGP looking-glass server.

    Args:
        destination: IPv4/IPv6 address or CIDR subnet (e.g., 1.1.1.1 or 1.1.1.0/24).
        server: Name of the BGP server to query (defaults to RouteViews Linx).
                Call list_servers() to see all available servers and their response times.

    Returns:
        Route lookup results from the BGP server.
    """
    # Validate destination
    is_valid, message = validate_ip_or_cidr(destination)
    if not is_valid:
        return f"Error: {message}"

    try:
        command = f"show ip bgp {destination}"
        response = await execute_bgp_command(server, command)
        return response
    except ValueError as e:
        return f"Configuration error: {str(e)}"
    except ConnectionError as e:
        return f"Connection error: {str(e)} - The BGP server may be unreachable or not accepting connections"
    except RuntimeError as e:
        return f"Query error: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {type(e).__name__}: {str(e)}"


@mcp.tool()
async def bgp_summary(server: str = "RouteViews Linx") -> str:
    """Get BGP summary information from a route server.

    Returns information about the BGP router including neighbor counts, 
    AS number, router ID, and other BGP statistics.

    Args:
        server: Name of the BGP server to query (defaults to RouteViews Linx).
                Call list_servers() to see all available servers and their response times.

    Returns:
        BGP summary output from the server showing router statistics and neighbors.
    """
    try:
        command = "show ip bgp summary"
        response = await execute_bgp_command(server, command)
        return response        
    except ValueError as e:
        return f"Configuration error: {str(e)}"
    except ConnectionError as e:
        return f"Connection error: {str(e)} - The BGP server may be unreachable or not accepting connections"
    except RuntimeError as e:
        return f"Query error: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {type(e).__name__}: {str(e)}"


@mcp.tool()
def list_servers() -> str:
    """List all configured BGP looking-glass servers.

    Returns:
        List of configured servers with their details.
    """
    try:
        config_data = load_config()
        servers = config_data.get("servers", [])
        
        if not servers:
            return "No servers configured."
        
        output = "Configured BGP Looking-Glass Servers:\n"
        for server in servers:
            status = "enabled" if server.get("enabled", True) else "disabled"
            output += f"\n- {server['name']} ({status})\n"
            output += f"  Host: {server['host']}:{server.get('port', 23)}\n"
            output += f"  Method: {server.get('connection_method', 'unknown')}\n"
        
        return output
    except Exception as e:
        return f"Error listing servers: {str(e)}"


@mcp.tool()
async def asn_owner(asn: str) -> str:
    """Look up the owner name for an Autonomous System Number (ASN).

    Uses the BGPKit public API to retrieve ASN ownership information.

    Args:
        asn: Autonomous System Number in format "AS123" or "123" (e.g., "AS64512" or "64512").

    Returns:
        Owner name for the ASN.
    """
    try:
        owner_name = await lookup_asn_owner(asn)
        return f"ASN {asn}: {owner_name}"
    except ValueError as e:
        return f"Invalid ASN: {str(e)}"
    except RuntimeError as e:
        return f"Lookup error: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {type(e).__name__}: {str(e)}"


@mcp.tool()
async def ip_lookup(ip: str) -> str:
    """Look up geolocation and BGP metadata for an IP address.

    Uses the BGPKit public API to retrieve IP geolocation information including
    country, covering prefix, ASN, and RPKI validation status.

    Args:
        ip: IPv4 or IPv6 address (e.g., "8.8.8.8" or "2001:4860:4860::8888").
            Must be a public address (not private or reserved).

    Returns:
        Dictionary-formatted string with: ip, country, asn, prefix, name, rpki, updated_at
    """
    try:
        result = await lookup_ip_geolocation(ip)
        
        # Format response
        output = f"IP Lookup: {result['ip']}\n"
        output += f"Country: {result['country']}\n"
        output += f"ASN: {result['asn']}\n"
        output += f"Prefix: {result['prefix']}\n"
        output += f"Name: {result['name']}\n"
        output += f"RPKI Status: {result['rpki']}\n"
        output += f"Updated: {result['updated_at']}"
        
        return output
    except ValueError as e:
        return f"Invalid IP address: {str(e)}"
    except RuntimeError as e:
        return f"Lookup error: {str(e)}"
    except Exception as e:
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

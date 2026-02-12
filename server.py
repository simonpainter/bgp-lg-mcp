"""BGP Looking Glass MCP Server."""

import json
import logging
import sys
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP
from mcp.server.stdio import stdio_server

from bgp_client import BGPTelnetClient
from validation import validate_ip_or_cidr, get_ip_type

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create the MCP server
mcp = FastMCP("bgp-lg-mcp")

# Global config
config = None
config_path = Path(__file__).parent / "config.json"


def load_config() -> dict:
    """Load configuration from config.json."""
    global config
    
    if config is not None:
        return config
    
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
        logger.info(f"Loaded configuration from {config_path}")
        return config
    except FileNotFoundError:
        logger.error(f"Config file not found at {config_path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in config file: {e}")
        raise


def get_server_config(server_name: str) -> Optional[dict]:
    """Get configuration for a specific server.

    Args:
        server_name: Name of the server.

    Returns:
        Server configuration dict or None if not found.
    """
    config_data = load_config()
    for server in config_data.get("servers", []):
        if server.get("name") == server_name:
            return server
    return None


def get_available_servers() -> list:
    """Get list of available (enabled) server names from config.

    Returns:
        List of enabled server names.
    """
    config_data = load_config()
    return [
        server.get("name")
        for server in config_data.get("servers", [])
        if server.get("enabled", True)
    ]


def build_server_description() -> str:
    """Build a formatted description of available servers for tool docs.

    Returns:
        Formatted string describing available servers.
    """
    servers = get_available_servers()
    if not servers:
        return "No servers available."
    
    desc = "Available servers: " + ", ".join(servers)
    desc += f". Default: '{servers[0]}' (fastest)."
    return desc


async def query_bgp_server(server_name: str, destination: str) -> str:
    """Query a BGP looking-glass server for route information.

    Args:
        server_name: Name of the server to query.
        destination: IP address or CIDR subnet to look up.

    Returns:
        Server response with route details.
    """
    server_config = get_server_config(server_name)
    if not server_config:
        raise ValueError(f"Server '{server_name}' not found in configuration")

    if not server_config.get("enabled", True):
        raise ValueError(f"Server '{server_name}' is disabled")

    try:
        # Create on-demand connection (fast enough for RouteViews servers)
        client = BGPTelnetClient(
            host=server_config["host"],
            port=server_config.get("port", 23),
            username=server_config.get("username", ""),
            password=server_config.get("password", ""),
            prompt=server_config.get("prompt", "#"),
            timeout=server_config.get("timeout", 15),
        )
        
        # Connect
        await client.connect()
        
        # Use BGP-specific command (show ip bgp for Cisco-based route servers)
        command = f"show ip bgp {destination}"
        response = await client.send_command(command)
        
        # Close connection
        await client.close()
        
        return response
        
    except Exception as e:
        raise RuntimeError(f"Failed to query {server_name}: {str(e)}")


@mcp.tool()
async def route_lookup(destination: str, server: str = "RouteViews Linx") -> str:
    """Look up a route on a BGP looking-glass server.

    Args:
        destination: IPv4/IPv6 address or CIDR subnet (e.g., 1.1.1.1 or 1.1.1.0/24).
        server: Name of the BGP server to query. RouteViews Linx (default) is fastest at ~50ms.
                Other options: RouteViews Equinix, RouteViews ISC, RouteViews Main, 
                RouteViews WIDE, RouteViews Chicago, RouteViews Sydney.

    Returns:
        Route lookup results from the BGP server.
    """
    # Validate destination
    is_valid, message = validate_ip_or_cidr(destination)
    if not is_valid:
        return f"Error: {message}"

    ip_type = get_ip_type(destination)
    logger.info(f"Looking up {ip_type} {destination} on {server}")

    try:
        response = await query_bgp_server(server, destination)
        return response
    except ValueError as e:
        error_msg = f"Configuration error: {str(e)}"
        logger.error(error_msg)
        return error_msg
    except ConnectionError as e:
        error_msg = f"Connection error: {str(e)} - The BGP server may be unreachable or not accepting connections"
        logger.error(error_msg)
        return error_msg
    except RuntimeError as e:
        error_msg = f"Query error: {str(e)}"
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Unexpected error: {type(e).__name__}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg


@mcp.tool()
async def bgp_summary(server: str = "RouteViews Linx") -> str:
    """Get BGP summary information from a route server.

    Returns information about the BGP router including neighbor counts, 
    AS number, router ID, and other BGP statistics.

    Args:
        server: Name of the BGP server to query. RouteViews Linx (default) is fastest at ~50ms.
                Other options: RouteViews Equinix, RouteViews ISC, RouteViews Main,
                RouteViews WIDE, RouteViews Chicago, RouteViews Sydney.

    Returns:
        BGP summary output from the server showing router statistics and neighbors.
    """
    server_config = get_server_config(server)
    if not server_config:
        error_msg = f"Server '{server}' not found in configuration"
        logger.error(error_msg)
        return error_msg

    if not server_config.get("enabled", True):
        error_msg = f"Server '{server}' is disabled"
        logger.error(error_msg)
        return error_msg

    try:
        # Create on-demand connection
        client = BGPTelnetClient(
            host=server_config["host"],
            port=server_config.get("port", 23),
            username=server_config.get("username", ""),
            password=server_config.get("password", ""),
            prompt=server_config.get("prompt", "#"),
            timeout=server_config.get("timeout", 15),
        )
        
        # Connect
        await client.connect()
        
        # Send BGP summary command
        response = await client.send_command("show ip bgp summary")
        
        # Close connection
        await client.close()
        
        logger.info(f"Retrieved BGP summary from {server}")
        return response
        
    except ConnectionError as e:
        error_msg = f"Connection error to {server}: {str(e)} - The BGP server may be unreachable or not accepting connections"
        logger.error(error_msg)
        return error_msg
    except RuntimeError as e:
        error_msg = f"Query error from {server}: {str(e)}"
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Unexpected error querying {server}: {type(e).__name__}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg

    if not server_config.get("enabled", True):
        error_msg = f"Server '{server}' is disabled"
        logger.error(error_msg)
        return error_msg

    try:
        # Create on-demand connection
        client = BGPTelnetClient(
            host=server_config["host"],
            port=server_config.get("port", 23),
            username=server_config.get("username", ""),
            password=server_config.get("password", ""),
            prompt=server_config.get("prompt", "#"),
            timeout=server_config.get("timeout", 15),
        )
        
        # Connect
        await client.connect()
        
        # Send BGP summary command
        response = await client.send_command("show ip bgp summary")
        
        # Close connection
        await client.close()
        
        logger.info(f"Retrieved BGP summary from {server}")
        return response
        
    except ConnectionError as e:
        error_msg = f"Connection error to {server}: {str(e)} - The BGP server may be unreachable or not accepting connections"
        logger.error(error_msg)
        return error_msg
    except RuntimeError as e:
        error_msg = f"Query error from {server}: {str(e)}"
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Unexpected error querying {server}: {type(e).__name__}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg


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


def run_streamable_http_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Run the MCP server with streamable-http transport.

    Args:
        host: Server host address (default: 127.0.0.1).
        port: Server port (default: 8000).
    """
    import uvicorn

    # No pre-warming needed - connections are created lazily on first query
    # within the same event loop as MCP requests

    # Use FastMCP's built-in streamable-http app
    app = mcp.streamable_http_app
    
    logger.info(f"Starting MCP Server on {host}:{port}")
    logger.info(f"Endpoint: http://{host}:{port}/mcp")
    logger.info("Connections will be established lazily on first query")
    uvicorn.run(app, host=host, port=port, log_level="info")


def run_http_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Run the MCP server as an HTTP streaming server.

    Args:
        host: Server host address (default: 127.0.0.1).
        port: Server port (default: 8000).
    """
    import uvicorn
    from fastapi import FastAPI, HTTPException

    app = FastAPI(title="BGP Looking Glass MCP Server")

    @app.get("/health")
    async def health():
        """Health check endpoint."""
        return {"status": "ok"}

    @app.post("/route-lookup")
    async def api_route_lookup(destination: str, server: str = "RouteViews Linx"):
        """HTTP endpoint for route lookup."""
        # Validate destination
        is_valid, message = validate_ip_or_cidr(destination)
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Invalid destination: {message}")

        try:
            response = await query_bgp_server(server, destination)
            return {"destination": destination, "server": server, "result": response}
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except RuntimeError as e:
            raise HTTPException(status_code=503, detail=str(e))

    @app.get("/servers")
    async def api_list_servers():
        """HTTP endpoint for listing servers."""
        try:
            config_data = load_config()
            servers = config_data.get("servers", [])
            return {"servers": servers}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    logger.info(f"Starting BGP Looking Glass MCP Server on {host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    # Check for stdio mode (for MCP clients)
    if len(sys.argv) > 1 and sys.argv[1] == "--stdio":
        try:
            mcp.run()
        finally:
            pass  # No persistent sessions to clean up
    else:
        # Check for explicit http mode
        use_http_only = len(sys.argv) > 1 and sys.argv[1] == "--http-only"
        
        # Parse custom host/port arguments
        host = "127.0.0.1"
        port = 8000
        
        i = 1
        while i < len(sys.argv):
            if sys.argv[i] == "--host" and i + 1 < len(sys.argv):
                host = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--port" and i + 1 < len(sys.argv):
                port = int(sys.argv[i + 1])
                i += 2
            elif sys.argv[i] == "--http-only":
                i += 1
            else:
                i += 1
        
        try:
            # Default to streamable-http server
            if use_http_only:
                run_http_server(host, port)
            else:
                run_streamable_http_server(host, port)
        finally:
            pass  # No persistent sessions to clean up

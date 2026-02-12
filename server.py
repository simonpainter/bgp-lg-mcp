"""BGP Looking Glass MCP Server."""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP
from mcp.server.stdio import stdio_server

from bgp_client import BGPTelnetClient
from session_manager import get_session_manager, close_session_manager
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


async def query_bgp_server(server_name: str, command: str) -> str:
    """Query a BGP looking-glass server using persistent session.

    Args:
        server_name: Name of the server to query.
        command: Command to send to the server.

    Returns:
        Server response.
    """
    server_config = get_server_config(server_name)
    if not server_config:
        raise ValueError(f"Server '{server_name}' not found in configuration")

    if not server_config.get("enabled", True):
        raise ValueError(f"Server '{server_name}' is disabled")

    manager = get_session_manager()
    
    try:
        # Get or create a persistent session
        session = await manager.get_session(
            host=server_config["host"],
            port=server_config.get("port", 23),
            username=server_config.get("username", ""),
            password=server_config.get("password", ""),
            prompt=server_config.get("prompt", "#"),
            timeout=server_config.get("timeout", 20),
        )
        
        # Send command using the persistent connection
        response = await session.send_command(command)
        return response
        
    except Exception as e:
        raise RuntimeError(f"Failed to query {server_name}: {str(e)}")


@mcp.tool()
async def route_lookup(destination: str, server: str = "route-server.ip.att.net") -> str:
    """Look up a route on a BGP looking-glass server.

    Args:
        destination: IPv4/IPv6 address or CIDR subnet (e.g., 1.1.1.1 or 1.1.1.0/24).
        server: Name of the BGP server to query (default: route-server.ip.att.net).

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
        # Call async function directly (no asyncio.run needed)
        command = f"show route {destination}"
        response = await query_bgp_server(server, command)
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

    # Pre-warm connections to configured servers
    async def warmup_connections():
        """Eagerly connect to all enabled servers at startup."""
        logger.info("Pre-warming connections to enabled servers...")
        manager = get_session_manager()
        config_data = load_config()
        
        for server in config_data.get("servers", []):
            if server.get("enabled", True):
                try:
                    logger.info(f"Warming up connection to {server['name']}...")
                    session = await manager.get_session(
                        host=server["host"],
                        port=server.get("port", 23),
                        username=server.get("username", ""),
                        password=server.get("password", ""),
                        prompt=server.get("prompt", "#"),
                        timeout=server.get("timeout", 20),
                    )
                    logger.info(f"✓ {server['name']} connection ready")
                except Exception as e:
                    logger.warning(f"⚠ Failed to pre-warm {server['name']}: {e}")

    # Use FastMCP's built-in streamable-http app
    app = mcp.streamable_http_app
    
    logger.info(f"Starting BGP Looking Glass MCP Server (streamable-http) on {host}:{port}")
    logger.info(f"MCP endpoint available at http://{host}:{port}/mcp")
    
    # Start warmup in background after server starts
    def on_startup():
        asyncio.create_task(warmup_connections())
    
    # We can't easily hook into uvicorn startup, so we'll let the first request trigger it
    # But we'll add a health check endpoint that triggers warmup
    
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
    async def api_route_lookup(destination: str, server: str = "route-server.ip.att.net"):
        """HTTP endpoint for route lookup."""
        # Validate destination
        is_valid, message = validate_ip_or_cidr(destination)
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Invalid destination: {message}")

        try:
            command = f"show route {destination}"
            response = await query_bgp_server(server, command)
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
            # Clean up sessions on shutdown
            asyncio.run(close_session_manager())
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
            # Clean up sessions on shutdown
            asyncio.run(close_session_manager())

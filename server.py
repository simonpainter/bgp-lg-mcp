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
    """Query a BGP looking-glass server.

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

    try:
        async with BGPTelnetClient(
            host=server_config["host"],
            port=server_config.get("port", 23),
            username=server_config.get("username", ""),
            password=server_config.get("password", ""),
            prompt=server_config.get("prompt", "#"),
            timeout=server_config.get("timeout", 10),
        ) as client:
            response = await client.send_command(command)
            return response
    except Exception as e:
        raise RuntimeError(f"Failed to query {server_name}: {str(e)}")


@mcp.tool()
def route_lookup(destination: str, server: str = "route-server.ip.att.net") -> str:
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
        # Run async operation
        command = f"show route {destination}"
        response = asyncio.run(query_bgp_server(server, command))
        return response
    except ValueError as e:
        return f"Configuration error: {str(e)}"
    except RuntimeError as e:
        return f"Query error: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


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
    from fastapi import FastAPI, Request
    from fastapi.responses import StreamingResponse
    import uvicorn
    import json as json_lib

    app = FastAPI(title="BGP Looking Glass MCP Server")

    @app.get("/health")
    async def health():
        """Health check endpoint."""
        return {"status": "ok", "transport": "streamable-http"}

    @app.post("/mcp")
    async def mcp_endpoint(request: Request):
        """MCP streamable-http transport endpoint."""
        async def generate():
            try:
                # Read the complete request body
                body = await request.body()
                if body:
                    # Process the MCP message
                    data = json_lib.loads(body)
                    logger.debug(f"MCP request: {data}")

                    # Use the fastmcp server to handle the request
                    # For streamable-http, we need to handle this differently
                    yield b'{"jsonrpc": "2.0", "id": 1, "result": {}}\n'
                else:
                    yield b''
            except Exception as e:
                logger.error(f"MCP endpoint error: {e}")
                yield json_lib.dumps({"error": str(e)}).encode() + b'\n'

        return StreamingResponse(
            generate(),
            media_type="application/json",
            headers={
                "Connection": "keep-alive",
                "Transfer-Encoding": "chunked",
                "Content-Type": "application/json",
            },
        )

    @app.post("/route-lookup")
    async def api_route_lookup(destination: str, server: str = "route-server.ip.att.net"):
        """HTTP endpoint for route lookup."""
        # Validate destination
        is_valid, message = validate_ip_or_cidr(destination)
        if not is_valid:
            return {"error": f"Invalid destination: {message}"}, 400

        try:
            command = f"show route {destination}"
            response = await query_bgp_server(server, command)
            return {"destination": destination, "server": server, "result": response}
        except ValueError as e:
            return {"error": str(e)}, 404
        except RuntimeError as e:
            return {"error": str(e)}, 503

    @app.get("/servers")
    async def api_list_servers():
        """HTTP endpoint for listing servers."""
        try:
            config_data = load_config()
            servers = config_data.get("servers", [])
            return {"servers": servers}
        except Exception as e:
            return {"error": str(e)}, 500

    logger.info(f"Starting BGP Looking Glass MCP Server (streamable-http) on {host}:{port}")
    logger.info(f"MCP endpoint available at http://{host}:{port}/mcp")
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
        mcp.run()
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
        
        # Default to streamable-http server
        if use_http_only:
            run_http_server(host, port)
        else:
            run_streamable_http_server(host, port)

"""BGP Looking Glass MCP Server."""

import ipaddress
import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP
from mcp.server.stdio import stdio_server
from starlette.responses import JSONResponse

from bgp_client import BGPTelnetClient

# Setup logging
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, log_level, logging.INFO))
logger = logging.getLogger(__name__)


def validate_ip_or_cidr(destination: str) -> tuple[bool, str]:
    """Validate if destination is a valid public IPv4/IPv6 address or CIDR subnet.

    Args:
        destination: IP address, IPv6 address, or CIDR notation string.

    Returns:
        Tuple of (is_valid, message).
    """
    destination = destination.strip()

    try:
        # Try to parse as CIDR subnet first
        if "/" in destination:
            network = ipaddress.ip_network(destination, strict=False)
            
            # Check if it's a public address (not private/reserved)
            if network.is_private or network.is_loopback or network.is_link_local:
                return False, f"CIDR subnet {destination} is not public"
            
            return True, f"Valid CIDR subnet: {network}"
        
        # Try to parse as individual IP address
        ip = ipaddress.ip_address(destination)
        
        # Check if it's a public address
        if ip.is_private or ip.is_loopback or ip.is_link_local:
            return False, f"Address {destination} is not public"
        
        return True, f"Valid IP address: {ip}"
    
    except ValueError as e:
        return False, f"Invalid IP address or CIDR notation: {str(e)}"


def get_ip_type(destination: str) -> str:
    """Determine if address is IPv4 or IPv6.

    Args:
        destination: IP address or CIDR notation.

    Returns:
        "IPv4", "IPv6", or "unknown".
    """
    try:
        if "/" in destination:
            network = ipaddress.ip_network(destination, strict=False)
            return "IPv6" if network.version == 6 else "IPv4"
        
        ip = ipaddress.ip_address(destination)
        return "IPv6" if ip.version == 6 else "IPv4"
    except ValueError:
        return "unknown"


# Create the MCP server
mcp = FastMCP("BGP Looking Glass")

# Global config
config = None
config_path = Path(__file__).parent / "config.json"

# Allow config path to be overridden via environment variable
env_config_path = os.getenv("CONFIG_PATH")
if env_config_path:
    config_path = Path(env_config_path)
    logger.info(f"Using CONFIG_PATH from environment: {config_path}")


def load_config() -> dict:
    """Load configuration from config.json.
    
    Configuration can be overridden with environment variables:
    - CONFIG_PATH: Path to config.json file
    - BGP_SERVER_TIMEOUT: Default timeout for BGP connections (seconds)
    """
    global config
    
    if config is not None:
        return config
    
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
        
        # Apply environment variable overrides for server configuration
        timeout_override = os.getenv("BGP_SERVER_TIMEOUT")
        if timeout_override:
            try:
                timeout = int(timeout_override)
                for server in config.get("servers", []):
                    if "timeout" not in server or server.get("_env_timeout_override"):
                        server["timeout"] = timeout
                        server["_env_timeout_override"] = True
                logger.info(f"Applied BGP_SERVER_TIMEOUT={timeout}s to all servers")
            except ValueError:
                logger.warning(f"Invalid BGP_SERVER_TIMEOUT value: {timeout_override}, ignoring")
        
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


async def execute_bgp_command(server_name: str, command: str) -> str:
    """Execute a command on a BGP looking-glass server.

    Args:
        server_name: Name of the server to query.
        command: BGP command to execute.

    Returns:
        Server response with command output.
    
    Raises:
        ValueError: If server not found or disabled.
        RuntimeError: If connection or command execution fails.
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
        
        # Execute command
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
        server: Name of the BGP server to query (defaults to RouteViews Linx).
                Call list_servers() to see all available servers and their response times.

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
        command = f"show ip bgp {destination}"
        response = await execute_bgp_command(server, command)
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
        server: Name of the BGP server to query (defaults to RouteViews Linx).
                Call list_servers() to see all available servers and their response times.

    Returns:
        BGP summary output from the server showing router statistics and neighbors.
    """
    logger.info(f"Retrieving BGP summary from {server}")

    try:
        command = "show ip bgp summary"
        response = await execute_bgp_command(server, command)
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


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    """Health check endpoint for Azure monitoring."""
    try:
        # Verify config can be loaded
        load_config()
        return JSONResponse({"status": "healthy", "service": "BGP Looking Glass"})
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            {"status": "unhealthy", "service": "BGP Looking Glass", "error": str(e)},
            status_code=503
        )


# Create ASGI application for production deployment (Azure, Gunicorn, etc.)
app = mcp.streamable_http_app()

# For Azure App Service compatibility
application = app


if __name__ == "__main__":
    # Support environment variables for configuration
    transport_mode = os.getenv("TRANSPORT_MODE", "streamable-http").lower()
    server_host = os.getenv("SERVER_HOST", "127.0.0.1")
    server_port = int(os.getenv("SERVER_PORT", "8000"))
    
    # Validate transport mode
    valid_transports = ["stdio", "sse", "streamable-http"]
    if transport_mode not in valid_transports:
        logger.warning(f"Invalid TRANSPORT_MODE '{transport_mode}', using 'streamable-http'")
        transport_mode = "streamable-http"
    
    # Check for stdio mode (for MCP clients) via argument or environment variable
    if (len(sys.argv) > 1 and sys.argv[1] == "--stdio") or transport_mode == "stdio":
        logger.info("Starting BGP Looking Glass MCP server in STDIO mode")
        mcp.run()
    else:
        # Start an HTTP server (default: streamable-http)
        logger.info(f"Starting BGP Looking Glass MCP server in {transport_mode} mode on {server_host}:{server_port}")
        mcp.run(transport=transport_mode)  # type: ignore

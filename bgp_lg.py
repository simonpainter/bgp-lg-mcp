"""BGP Looking Glass library - worker functions and telnet client."""

import asyncio
import ipaddress
import json
import os
import re
from pathlib import Path
from typing import Optional

import httpx

# Telnet protocol constants
TELNET_IAC = 0xff  # Interpret As Command
TELNET_DONT = 0xfe
TELNET_DO = 0xfd
TELNET_WONT = 0xfc
TELNET_WILL = 0xfb
TELNET_SB = 0xfa  # Subnegotiation
TELNET_SE = 0xf0  # End of subnegotiation


async def _http_request_with_retry(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    max_retries: int = 3,
    initial_backoff: float = 0.5,
    **kwargs,
) -> httpx.Response:
    """Make HTTP request with exponential backoff retry logic.
    
    Retries on:
    - 429 (Rate Limit)
    - 5xx (Server Errors)
    - Timeout exceptions
    
    Args:
        client: httpx.AsyncClient instance
        method: HTTP method (GET, POST, etc)
        url: Request URL
        max_retries: Maximum number of retry attempts
        initial_backoff: Initial backoff in seconds
        **kwargs: Additional arguments to pass to client.request()
        
    Returns:
        httpx.Response object
        
    Raises:
        RuntimeError: On final failure after all retries
        httpx.TimeoutException: If timeout occurs on final attempt
    """
    backoff = initial_backoff
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            response = await client.request(method, url, **kwargs)
            
            # Don't retry on 404 or other client errors (except 429)
            if response.status_code == 429:
                if attempt < max_retries:
                    await asyncio.sleep(backoff)
                    backoff *= 2  # Exponential backoff
                    continue
                else:
                    raise RuntimeError("BGPKit API rate limit exceeded after retries, please try again later")
            
            if response.status_code >= 500:
                if attempt < max_retries:
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    continue
                else:
                    raise RuntimeError(f"BGPKit API server error (status {response.status_code}) after retries")
            
            return response
            
        except httpx.TimeoutException as e:
            last_exception = e
            if attempt < max_retries:
                await asyncio.sleep(backoff)
                backoff *= 2
                continue
            else:
                raise
    
    # This should not be reached, but added for type checking
    raise RuntimeError("HTTP request failed after retries")



class TelnetClient:
    """Async telnet client for BGP looking-glass servers."""

    def __init__(
        self,
        host: str,
        port: int = 23,
        username: str = "",
        password: str = "",
        prompt: str = "#",
        timeout: int = 15,
    ):
        """Initialize telnet client.

        Args:
            host: Hostname or IP address.
            port: Telnet port (default 23).
            username: Login username.
            password: Login password.
            prompt: Command prompt indicator.
            timeout: Connection timeout in seconds.
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.prompt = prompt
        self.timeout = timeout
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None

    def _handle_telnet_negotiation(self, data: bytes) -> tuple[bytes, bytes]:
        """Handle telnet protocol negotiation.
        
        Responds to telnet DO/DONT/WILL/WONT commands appropriately.
        
        Args:
            data: Raw bytes from server
            
        Returns:
            Tuple of (cleaned_data, response_bytes)
        """
        response = b""
        i = 0
        cleaned = b""
        
        while i < len(data):
            if data[i:i+1] == bytes([TELNET_IAC]) and i + 1 < len(data):
                cmd = data[i + 1]
                
                if cmd == TELNET_DO:
                    # Server asking if we support an option
                    if i + 2 < len(data):
                        opt = data[i + 2]
                        # Respond with WONT (we don't support most options)
                        response += bytes([TELNET_IAC, TELNET_WONT, opt])
                        i += 3
                        continue
                        
                elif cmd == TELNET_DONT:
                    # Server saying not to use an option
                    if i + 2 < len(data):
                        i += 3
                        continue
                        
                elif cmd == TELNET_WILL:
                    # Server saying it will use an option
                    if i + 2 < len(data):
                        opt = data[i + 2]
                        # Respond with DONT (we don't want most options)
                        response += bytes([TELNET_IAC, TELNET_DONT, opt])
                        i += 3
                        continue
                        
                elif cmd == TELNET_WONT:
                    # Server saying it won't use an option
                    if i + 2 < len(data):
                        i += 3
                        continue
                        
                elif cmd == TELNET_SB:
                    # Subnegotiation - skip until SE
                    i += 2
                    while i < len(data) and not (data[i:i+1] == bytes([TELNET_IAC]) and i + 1 < len(data) and data[i + 1] == TELNET_SE):
                        i += 1
                    if i < len(data):
                        i += 2
                    continue
                else:
                    cleaned += data[i:i+1]
                    i += 1
                    continue
            
            cleaned += data[i:i+1]
            i += 1
        
        return cleaned, response

    async def connect(self) -> None:
        """Connect to telnet server and authenticate."""
        try:
            self.reader, self.writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=self.timeout,
            )

            # Read initial banner/prompt
            banner = await self._read_until_prompt(max_wait=15, require_prompt=False)

            # Authenticate if credentials provided
            if self.username:
                await self._send_command(self.username)
                response = await self._read_until_prompt(max_wait=self.timeout)

            if self.password:
                await self._send_command(self.password)
                response = await self._read_until_prompt(max_wait=self.timeout)

        except asyncio.TimeoutError:
            raise ConnectionError(f"Timeout connecting to {self.host}:{self.port}")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to {self.host}: {str(e)}")

    async def _send_command(self, command: str) -> None:
        """Send a command to the server."""
        if not self.writer:
            raise ConnectionError("Not connected")

        command_bytes = f"{command}\n".encode()
        
        self.writer.write(command_bytes)
        await self.writer.drain()

    async def _read_until_prompt(self, max_wait: int = 5, require_prompt: bool = True) -> str:
        """Read from server until prompt is found or timeout.
        
        Args:
            max_wait: Maximum time to wait in seconds.
            require_prompt: If False, return after getting some data (for banners).
        """
        if not self.reader:
            raise ConnectionError("Not connected")

        output = b""
        bytes_read = 0
        start_time = asyncio.get_event_loop().time()
        read_timeout = 1.0
        had_data = False
        
        try:
            while True:
                try:
                    # Use shorter individual read timeout
                    chunk = await asyncio.wait_for(
                        self.reader.read(4096),
                        timeout=read_timeout,
                    )
                    
                    if not chunk:
                        break

                    bytes_read += len(chunk)
                    had_data = True
                    
                    # Handle telnet negotiation
                    cleaned, telnet_response = self._handle_telnet_negotiation(chunk)
                    
                    if telnet_response and self.writer:
                        self.writer.write(telnet_response)
                        await self.writer.drain()
                    
                    if cleaned:
                        output += cleaned

                    # Check for pager output and handle it
                    decoded_partial = output.decode(errors="replace")
                    if "---(more)---" in decoded_partial or "---(" in decoded_partial:
                        if self.writer:
                            self.writer.write(b"q")
                            await self.writer.drain()
                        # Clear the more marker from output
                        output = output.replace(b"---(more)---", b"")
                        continue

                    # Check if prompt is in output
                    if self.prompt.encode() in output:
                        break
                    elif cleaned and not require_prompt:
                        # For banner-like responses, return after getting some data
                        break
                        
                except asyncio.TimeoutError:
                    elapsed = asyncio.get_event_loop().time() - start_time
                    
                    # If we haven't received any data yet, keep waiting
                    if not had_data:
                        if elapsed > max_wait:
                            raise ConnectionError(f"No response from server within {max_wait}s")
                        continue
                    
                    # If we have data but no prompt, and we don't require prompt, return it
                    if output and not require_prompt:
                        break
                    
                    # If we have data but still waiting for prompt
                    if output:
                        if elapsed > max_wait:
                            break
                        continue
                    
                    # No data and no prompt yet
                    if elapsed > max_wait:
                        raise ConnectionError(f"No response from server within {max_wait}s")
                    continue
                         
        except asyncio.TimeoutError:
            if not output:
                raise ConnectionError(f"No response from server within {max_wait}s")

        decoded = output.decode(errors="replace").strip()
        return decoded

    async def send_command(self, command: str) -> str:
        """Send a command and get the response.

        Args:
            command: Command to send.

        Returns:
            Server response.
        """
        if not self.writer:
            raise ConnectionError("Not connected")
        
        try:
            await self._send_command(command)
            response = await self._read_until_prompt(max_wait=self.timeout)
            return response
        except Exception as e:
            raise

    async def close(self) -> None:
        """Close the connection."""
        if self.writer:
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except Exception as e:
                pass

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


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


# Global config
_config: Optional[dict] = None
_config_path: Optional[Path] = None


def _get_config_path() -> Path:
    """Get the configuration file path."""
    global _config_path
    
    if _config_path is not None:
        return _config_path
    
    # Check environment variable first
    env_config_path = os.getenv("CONFIG_PATH")
    if env_config_path:
        _config_path = Path(env_config_path)
    else:
        _config_path = Path(__file__).parent / "config.json"
    
    return _config_path


def load_config() -> dict:
    """Load configuration from config.json.
    
    Configuration can be overridden with environment variables:
    - CONFIG_PATH: Path to config.json file
    - BGP_SERVER_TIMEOUT: Default timeout for BGP connections (seconds)
    """
    global _config
    
    if _config is not None:
        return _config
    
    config_path = _get_config_path()
    
    try:
        with open(config_path, "r") as f:
            _config = json.load(f)
        
        # Apply environment variable overrides for server configuration
        timeout_override = os.getenv("BGP_SERVER_TIMEOUT")
        if timeout_override:
            try:
                timeout = int(timeout_override)
                for server in _config.get("servers", []):
                    if "timeout" not in server or server.get("_env_timeout_override"):
                        server["timeout"] = timeout
                        server["_env_timeout_override"] = True
            except ValueError:
                pass
        
        return _config
    except FileNotFoundError:
        raise
    except json.JSONDecodeError as e:
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
        client = TelnetClient(
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


def _parse_asn(asn_input: str) -> int:
    """Parse ASN from various formats (AS123 or 123).
    
    Args:
        asn_input: ASN as string in format "AS123" or "123"
        
    Returns:
        ASN as integer
        
    Raises:
        ValueError: If ASN format is invalid or out of range
    """
    asn_input = asn_input.strip().upper()
    
    # Remove "AS" prefix if present
    if asn_input.startswith("AS"):
        asn_input = asn_input[2:]
    
    try:
        asn = int(asn_input)
    except ValueError:
        raise ValueError(f"Invalid ASN format: must be a number, optionally prefixed with 'AS'")
    
    # Validate ASN range (0-4294967295 for 32-bit ASN)
    if asn < 0 or asn > 4294967295:
        raise ValueError(f"ASN {asn} out of valid range (0-4294967295)")
    
    return asn


async def lookup_asn_owner(asn_input: str, timeout: int = 10) -> str:
    """Look up ASN owner name using BGPKit API.
    
    Args:
        asn_input: ASN as string in format "AS123" or "123"
        timeout: Request timeout in seconds
        
    Returns:
        Owner name for the ASN
        
    Raises:
        ValueError: If ASN format is invalid
        RuntimeError: If API request fails
    """
    # Validate and parse ASN
    try:
        asn = _parse_asn(asn_input)
    except ValueError as e:
        raise ValueError(f"Invalid ASN: {str(e)}")
    
    # Call BGPKit API - GET /v3/utils/asn with asn query parameter
    api_url = "https://api.bgpkit.com/v3/utils/asn"
    params = {"asn": asn}
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await _http_request_with_retry(
                client, "GET", api_url, params=params
            )
            
            if response.status_code == 404:
                raise RuntimeError(f"ASN {asn} not found in BGPKit database")
            
            response.raise_for_status()
            
            data = response.json()
            
            # Extract owner name from response
            # API returns data array with ASN info
            data_array = data.get("data", [])
            if not data_array or len(data_array) == 0:
                raise RuntimeError(f"No data found for ASN {asn}")
            
            # Get the name field from the first element
            asn_info = data_array[0]
            owner_name = asn_info.get("name")
            if not owner_name:
                raise RuntimeError(f"No owner name found for ASN {asn}")
            
            return owner_name
            
    except httpx.TimeoutException:
        raise RuntimeError(f"BGPKit API request timed out after {timeout}s")
    except httpx.RequestError as e:
        raise RuntimeError(f"BGPKit API request failed: {str(e)}")
    except json.JSONDecodeError:
        raise RuntimeError("BGPKit API returned invalid JSON")

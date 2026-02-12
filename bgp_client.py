"""Telnet client for BGP looking-glass servers."""

import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Telnet protocol constants
TELNET_IAC = 0xff  # Interpret As Command
TELNET_DONT = 0xfe
TELNET_DO = 0xfd
TELNET_WONT = 0xfc
TELNET_WILL = 0xfb
TELNET_SB = 0xfa  # Subnegotiation
TELNET_SE = 0xf0  # End of subnegotiation


class BGPTelnetClient:
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
        self._connection_loop: Optional[asyncio.AbstractEventLoop] = None

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
                        logger.debug(f"Telnet: Server DO {opt}")
                        # Respond with WONT (we don't support most options)
                        response += bytes([TELNET_IAC, TELNET_WONT, opt])
                        i += 3
                        continue
                        
                elif cmd == TELNET_DONT:
                    # Server saying not to use an option
                    if i + 2 < len(data):
                        opt = data[i + 2]
                        logger.debug(f"Telnet: Server DONT {opt}")
                        i += 3
                        continue
                        
                elif cmd == TELNET_WILL:
                    # Server saying it will use an option
                    if i + 2 < len(data):
                        opt = data[i + 2]
                        logger.debug(f"Telnet: Server WILL {opt}")
                        # Respond with DONT (we don't want most options)
                        response += bytes([TELNET_IAC, TELNET_DONT, opt])
                        i += 3
                        continue
                        
                elif cmd == TELNET_WONT:
                    # Server saying it won't use an option
                    if i + 2 < len(data):
                        opt = data[i + 2]
                        logger.debug(f"Telnet: Server WONT {opt}")
                        i += 3
                        continue
                        
                elif cmd == TELNET_SB:
                    # Subnegotiation - skip until SE
                    logger.debug(f"Telnet: Server subnegotiation")
                    i += 2
                    while i < len(data) and not (data[i:i+1] == bytes([TELNET_IAC]) and i + 1 < len(data) and data[i + 1] == TELNET_SE):
                        i += 1
                    if i < len(data):
                        i += 2
                    continue
                else:
                    logger.debug(f"Telnet: Unknown command {cmd}")
                    cleaned += data[i:i+1]
                    i += 1
                    continue
            
            cleaned += data[i:i+1]
            i += 1
        
        return cleaned, response

    async def connect(self) -> None:
        """Connect to telnet server and authenticate."""
        try:
            logger.info(f"Connecting to {self.host}:{self.port}...")
            self.reader, self.writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=self.timeout,
            )
            # Track which event loop this connection was created in
            self._connection_loop = asyncio.get_event_loop()
            logger.info(f"✓ Connected to {self.host}:{self.port}")

            # Read initial banner/prompt
            logger.debug("Reading initial banner/prompt...")
            banner = await self._read_until_prompt(max_wait=15, require_prompt=False)
            logger.info(f"✓ Received banner ({len(banner)} bytes)")
            logger.debug(f"Banner content:\n{banner}")

            # Authenticate if credentials provided
            if self.username:
                logger.debug(f"Authenticating with username: {self.username}")
                await self._send_command(self.username)
                response = await self._read_until_prompt(max_wait=self.timeout)
                logger.info(f"✓ Username accepted")
                logger.debug(f"Username response:\n{response}")

            if self.password:
                logger.debug(f"Sending password...")
                await self._send_command(self.password)
                response = await self._read_until_prompt(max_wait=self.timeout)
                logger.info(f"✓ Password accepted")
                logger.debug(f"Password response:\n{response}")

            # Disable pager for Junos-based routers (try different syntaxes)
            logger.debug("Disabling pager...")
            for pager_cmd in ["set cli pager off", "set pager off"]:
                try:
                    await self._send_command(pager_cmd)
                    response = await self._read_until_prompt(max_wait=3)
                    if "syntax error" not in response.lower():
                        logger.info(f"✓ Pager disabled with: {pager_cmd}")
                        break
                except Exception as e:
                    logger.debug(f"Pager command '{pager_cmd}' failed: {e}")
                    continue

            logger.info(f"✓ Successfully authenticated on {self.host}")

        except asyncio.TimeoutError as e:
            logger.error(f"✗ Timeout connecting to {self.host}:{self.port}")
            raise ConnectionError(f"Timeout connecting to {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"✗ Failed to connect to {self.host}: {str(e)}", exc_info=True)
            raise ConnectionError(f"Failed to connect to {self.host}: {str(e)}")

    async def _send_command(self, command: str) -> None:
        """Send a command to the server."""
        if not self.writer:
            raise ConnectionError("Not connected")

        command_bytes = f"{command}\n".encode()
        logger.debug(f"Sending: {repr(command)}")
        logger.debug(f"Bytes ({len(command_bytes)}): {command_bytes.hex()}")
        
        self.writer.write(command_bytes)
        await self.writer.drain()
        logger.debug("✓ Command sent and drained")

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
        read_timeout = 1.0  # Shorter read timeout for faster responsiveness
        had_data = False  # Track if we've ever received data
        
        try:
            while True:
                try:
                    # Use shorter individual read timeout
                    chunk = await asyncio.wait_for(
                        self.reader.read(4096),
                        timeout=read_timeout,
                    )
                    
                    if not chunk:
                        logger.warning("✗ Connection closed by server")
                        break

                    bytes_read += len(chunk)
                    elapsed = asyncio.get_event_loop().time() - start_time
                    had_data = True
                    
                    # Handle telnet negotiation
                    cleaned, telnet_response = self._handle_telnet_negotiation(chunk)
                    
                    if telnet_response and self.writer:
                        logger.debug(f"Sending telnet response: {telnet_response.hex()}")
                        self.writer.write(telnet_response)
                        await self.writer.drain()
                    
                    if cleaned:
                        output += cleaned
                        logger.debug(f"Received: {len(cleaned)} bytes (total: {bytes_read}, elapsed: {elapsed:.2f}s)")

                    # Check for pager output and handle it
                    decoded_partial = output.decode(errors="replace")
                    if "---(more)---" in decoded_partial or "---(" in decoded_partial:
                        logger.debug("✓ Found pager marker, sending 'q' to quit paging")
                        if self.writer:
                            self.writer.write(b"q")
                            await self.writer.drain()
                        # Clear the more marker from output
                        output = output.replace(b"---(more)---", b"")
                        continue

                    # Check if prompt is in output
                    if self.prompt.encode() in output:
                        logger.debug(f"✓ Found prompt '{self.prompt}'")
                        break
                    elif cleaned and not require_prompt:
                        # For banner-like responses, return after getting some data
                        logger.debug(f"✓ Got data ({len(output)} bytes), returning (prompt not required)")
                        break
                        
                except asyncio.TimeoutError:
                    elapsed = asyncio.get_event_loop().time() - start_time
                    
                    # If we haven't received any data yet, keep waiting
                    if not had_data:
                        if elapsed > max_wait:
                            raise ConnectionError(f"No response from server within {max_wait}s")
                        logger.debug(f"No data yet at {elapsed:.2f}s, continuing...")
                        continue
                    
                    # If we have data but no prompt, and we don't require prompt, return it
                    if output and not require_prompt:
                        logger.debug(f"✓ Returning after {elapsed:.2f}s with {bytes_read} bytes (prompt not required)")
                        break
                    
                    # If we have data but still waiting for prompt
                    if output:
                        if elapsed > max_wait:
                            logger.warning(f"⚠ Timeout after {elapsed:.2f}s with {bytes_read} bytes, returning what we have")
                            break
                        # Continue waiting for more data/prompt
                        logger.debug(f"Waiting for prompt at {elapsed:.2f}s ({bytes_read} bytes)...")
                        continue
                    
                    # No data and no prompt yet
                    if elapsed > max_wait:
                        raise ConnectionError(f"No response from server within {max_wait}s")
                    logger.debug(f"Still waiting at {elapsed:.2f}s...")
                    continue
                        
        except asyncio.TimeoutError:
            logger.error(f"✗ Timeout after {max_wait}s with {bytes_read} bytes")
            if not output:
                raise ConnectionError(f"No response from server within {max_wait}s")

        decoded = output.decode(errors="replace").strip()
        logger.info(f"✓ Read: {bytes_read} bytes, {len(decoded)} chars")
        return decoded

    def _check_event_loop_mismatch(self) -> bool:
        """Check if current event loop differs from connection loop.
        
        Returns:
            True if there's a mismatch, False if loops match or connection is uninitialized.
        """
        if self._connection_loop is None or self.writer is None:
            return False
        
        try:
            current_loop = asyncio.get_event_loop()
            # Check if the loops are different
            if current_loop != self._connection_loop:
                logger.debug(f"⚠ Event loop mismatch detected")
                return True
        except RuntimeError:
            # No running event loop - this shouldn't happen but handle it
            logger.debug("No running event loop")
            return False
        
        return False

    async def send_command(self, command: str) -> str:
        """Send a command and get the response.

        Args:
            command: Command to send.

        Returns:
            Server response.
        """
        if not self.writer:
            raise ConnectionError("Not connected")
        
        # Check if event loop has changed since connection was created
        if self._check_event_loop_mismatch():
            logger.info(f"ℹ Event loop changed, clearing connection for lazy re-establishment")
            # Don't close - just mark as disconnected so session manager will reconnect
            self.reader = None
            self.writer = None
            self._connection_loop = None
            raise ConnectionError("Event loop changed - reconnecting")

        try:
            logger.info(f"Executing command: {command}")
            await self._send_command(command)
            response = await self._read_until_prompt(max_wait=self.timeout)
            logger.info(f"✓ Command completed")
            return response
        except Exception as e:
            logger.error(f"✗ Command failed: {str(e)}", exc_info=True)
            raise

    async def close(self) -> None:
        """Close the connection."""
        if self.writer:
            try:
                logger.debug("Closing connection...")
                self.writer.close()
                await self.writer.wait_closed()
                logger.info(f"✓ Disconnected from {self.host}")
            except Exception as e:
                logger.warning(f"⚠ Error closing connection: {e}")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()



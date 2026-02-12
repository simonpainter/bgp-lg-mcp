"""Telnet client for BGP looking-glass servers."""

import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


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

    async def connect(self) -> None:
        """Connect to telnet server and authenticate."""
        try:
            logger.info(f"Connecting to {self.host}:{self.port}...")
            self.reader, self.writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=self.timeout,
            )
            logger.info(f"Connected to {self.host}:{self.port}")

            # Read initial banner/prompt
            banner = await self._read_until_prompt(max_wait=self.timeout)
            logger.debug(f"Banner received: {banner[:100]}")

            # Authenticate if credentials provided
            if self.username:
                logger.debug(f"Sending username...")
                await self._send_command(self.username)
                response = await self._read_until_prompt(max_wait=self.timeout)
                logger.debug(f"Username response: {response[:100]}")

            if self.password:
                logger.debug(f"Sending password...")
                await self._send_command(self.password)
                response = await self._read_until_prompt(max_wait=self.timeout)
                logger.debug(f"Password response: {response[:100]}")

            logger.info(f"Successfully authenticated on {self.host}")

        except asyncio.TimeoutError as e:
            logger.error(f"Timeout connecting to {self.host}:{self.port}")
            raise ConnectionError(f"Timeout connecting to {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to connect to {self.host}: {str(e)}", exc_info=True)
            raise ConnectionError(f"Failed to connect to {self.host}: {str(e)}")

    async def _send_command(self, command: str) -> None:
        """Send a command to the server."""
        if not self.writer:
            raise ConnectionError("Not connected")

        logger.debug(f"Sending command: {command}")
        self.writer.write(f"{command}\n".encode())
        await self.writer.drain()

    async def _read_until_prompt(self, max_wait: int = 5) -> str:
        """Read from server until prompt is found or timeout."""
        if not self.reader:
            raise ConnectionError("Not connected")

        output = b""
        try:
            while True:
                try:
                    chunk = await asyncio.wait_for(
                        self.reader.read(4096),
                        timeout=max_wait,
                    )
                    if not chunk:
                        logger.warning("Connection closed by server")
                        break

                    output += chunk
                    logger.debug(f"Received {len(chunk)} bytes")

                    # Check if prompt is in output
                    if self.prompt.encode() in output:
                        logger.debug("Prompt found in output")
                        break
                except asyncio.TimeoutError:
                    logger.debug(f"Read timeout after receiving {len(output)} bytes")
                    if output:
                        break
                    raise
        except asyncio.TimeoutError:
            logger.warning(f"Timeout waiting for prompt after {max_wait}s")
            if not output:
                raise ConnectionError(f"No response from server within {max_wait}s")

        decoded = output.decode(errors="replace").strip()
        logger.debug(f"Total output: {len(decoded)} characters")
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
            logger.info(f"Executing command: {command}")
            await self._send_command(command)
            response = await self._read_until_prompt(max_wait=self.timeout)
            logger.info(f"Command completed, got {len(response)} bytes of response")
            return response
        except Exception as e:
            logger.error(f"Command failed: {str(e)}", exc_info=True)
            raise

    async def close(self) -> None:
        """Close the connection."""
        if self.writer:
            try:
                self.writer.close()
                await self.writer.wait_closed()
                logger.info(f"Disconnected from {self.host}")
            except Exception as e:
                logger.warning(f"Error closing connection: {e}")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

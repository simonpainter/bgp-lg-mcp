"""Telnet client for BGP looking-glass servers."""

import asyncio
import telnetlib
from typing import Optional
import logging

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
        timeout: int = 10,
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
            self.reader, self.writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=self.timeout,
            )
            logger.info(f"Connected to {self.host}:{self.port}")

            # Read initial banner
            await self._read_until_prompt()

            # Authenticate if credentials provided
            if self.username:
                await self._send_command(self.username)
                await self._read_until_prompt()

            if self.password:
                await self._send_command(self.password)
                await self._read_until_prompt()

        except asyncio.TimeoutError:
            raise ConnectionError(f"Timeout connecting to {self.host}:{self.port}")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to {self.host}: {str(e)}")

    async def _send_command(self, command: str) -> None:
        """Send a command to the server."""
        if not self.writer:
            raise ConnectionError("Not connected")

        self.writer.write(f"{command}\n".encode())
        await self.writer.drain()

    async def _read_until_prompt(self, max_wait: int = 5) -> str:
        """Read from server until prompt is found."""
        if not self.reader:
            raise ConnectionError("Not connected")

        output = b""
        try:
            while True:
                chunk = await asyncio.wait_for(
                    self.reader.read(1024),
                    timeout=max_wait,
                )
                if not chunk:
                    break

                output += chunk

                # Check if prompt is in output
                if self.prompt.encode() in output:
                    break
        except asyncio.TimeoutError:
            # Timeout is ok - we have some output
            pass

        return output.decode(errors="replace").strip()

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
            response = await self._read_until_prompt()
            return response
        except Exception as e:
            logger.error(f"Command failed: {str(e)}")
            raise

    async def close(self) -> None:
        """Close the connection."""
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
            logger.info(f"Disconnected from {self.host}")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

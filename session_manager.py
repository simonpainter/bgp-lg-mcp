"""Persistent BGP server session manager with auto-reconnection."""

import asyncio
import logging
from typing import Dict, Optional
from bgp_client import BGPTelnetClient

logger = logging.getLogger(__name__)


class BGPServerSession:
    """Maintains a persistent connection to a BGP server with auto-reconnection."""

    def __init__(
        self,
        host: str,
        port: int = 23,
        username: str = "",
        password: str = "",
        prompt: str = "#",
        timeout: int = 20,
        keepalive_interval: int = 60,
    ):
        """Initialize BGP server session.
        
        Args:
            host: Hostname or IP address.
            port: Telnet port (default 23).
            username: Login username.
            password: Login password.
            prompt: Command prompt indicator.
            timeout: Connection timeout in seconds.
            keepalive_interval: Seconds between keepalive commands (default 60).
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.prompt = prompt
        self.timeout = timeout
        self.keepalive_interval = keepalive_interval
        
        self.client: Optional[BGPTelnetClient] = None
        self._lock = asyncio.Lock()
        self._keepalive_task: Optional[asyncio.Task] = None
        self._is_running = False
        
        logger.info(f"Created session manager for {host}:{port}")

    async def connect(self) -> None:
        """Establish connection to BGP server."""
        async with self._lock:
            if self.client is not None and self.client.writer is not None:
                logger.debug(f"✓ Already connected to {self.host}")
                return
            
            try:
                logger.info(f"Connecting to {self.host}:{self.port}...")
                self.client = BGPTelnetClient(
                    host=self.host,
                    port=self.port,
                    username=self.username,
                    password=self.password,
                    prompt=self.prompt,
                    timeout=self.timeout,
                )
                await self.client.connect()
                logger.info(f"✓ Connected to {self.host}:{self.port}")
                
                # Start keepalive task
                if not self._is_running:
                    self._is_running = True
                    self._keepalive_task = asyncio.create_task(self._keepalive_loop())
                    logger.debug(f"Started keepalive task for {self.host}")
                
            except Exception as e:
                self.client = None
                logger.error(f"✗ Failed to connect to {self.host}: {e}")
                raise

    async def send_command(self, command: str) -> str:
        """Send command to BGP server, reconnecting if necessary.
        
        Args:
            command: Command to send.
            
        Returns:
            Server response.
        """
        max_retries = 2
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # Ensure connection is alive
                async with self._lock:
                    if self.client is None or self.client.writer is None:
                        logger.debug(f"Connection lost, reconnecting... (attempt {attempt + 1})")
                        self.client = None
                        await self.connect()
                
                # Send command
                logger.debug(f"Sending command: {command}")
                response = await self.client.send_command(command)
                return response
                
            except Exception as e:
                last_error = e
                logger.warning(f"✗ Command failed (attempt {attempt + 1}/{max_retries}): {e}")
                
                # Reset connection for retry
                async with self._lock:
                    if self.client:
                        try:
                            await self.client.close()
                        except Exception:
                            pass
                    self.client = None
                
                # Don't retry if this is the last attempt
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)  # Wait before retry
                    await self.connect()
        
        raise RuntimeError(f"Failed to send command after {max_retries} attempts: {last_error}")

    async def _keepalive_loop(self) -> None:
        """Periodically send keepalive commands to keep connection alive."""
        while self._is_running:
            try:
                await asyncio.sleep(self.keepalive_interval)
                
                if self.client and self.client.writer:
                    try:
                        # Send a benign command that doesn't produce output
                        logger.debug(f"Sending keepalive to {self.host}")
                        await asyncio.wait_for(
                            self.client.send_command(""),
                            timeout=5
                        )
                    except Exception as e:
                        logger.debug(f"Keepalive failed, connection may be stale: {e}")
                        # Connection will be re-established on next command
                        
            except asyncio.CancelledError:
                logger.debug(f"Keepalive task cancelled for {self.host}")
                break
            except Exception as e:
                logger.warning(f"Keepalive loop error: {e}")

    async def close(self) -> None:
        """Close the connection and stop keepalive."""
        async with self._lock:
            self._is_running = False
            
            if self._keepalive_task:
                self._keepalive_task.cancel()
                try:
                    await self._keepalive_task
                except asyncio.CancelledError:
                    pass
            
            if self.client:
                try:
                    await self.client.close()
                    logger.info(f"✓ Closed connection to {self.host}")
                except Exception as e:
                    logger.warning(f"Error closing connection: {e}")
                finally:
                    self.client = None


class SessionManager:
    """Manages persistent sessions to multiple BGP servers."""

    def __init__(self):
        """Initialize session manager."""
        self.sessions: Dict[str, BGPServerSession] = {}
        self._lock = asyncio.Lock()
        self._warmup_in_progress = False
        self._warmup_task: Optional[asyncio.Task] = None
        logger.info("Initialized global session manager")

    def _get_session_key(self, host: str, port: int, username: str) -> str:
        """Get unique key for a server session."""
        return f"{host}:{port}:{username}"

    async def warmup_all_sessions(self) -> None:
        """Pre-warm all enabled server sessions (lazy - happens once on first use)."""
        async with self._lock:
            # Only run warmup once
            if self._warmup_in_progress or self.sessions:
                return
            self._warmup_in_progress = True
        
        try:
            logger.info("Warming up connections to all enabled servers...")
            from server import load_config  # Import here to avoid circular imports
            
            config_data = load_config()
            
            for server in config_data.get("servers", []):
                if server.get("enabled", True):
                    try:
                        logger.info(f"Warming up {server['name']}...")
                        session = await self.get_session(
                            host=server["host"],
                            port=server.get("port", 23),
                            username=server.get("username", ""),
                            password=server.get("password", ""),
                            prompt=server.get("prompt", "#"),
                            timeout=server.get("timeout", 20),
                        )
                        logger.info(f"✓ {server['name']} ready (queries will be <1s)")
                    except Exception as e:
                        logger.warning(f"⚠ Failed to warm {server['name']}: {e}")
            
            logger.info("✓ Connection warmup complete")
        finally:
            async with self._lock:
                self._warmup_in_progress = False

    async def get_session(
        self,
        host: str,
        port: int = 23,
        username: str = "",
        password: str = "",
        prompt: str = "#",
        timeout: int = 20,
    ) -> BGPServerSession:
        """Get or create a persistent session to a BGP server.
        
        Args:
            host: Hostname or IP address.
            port: Telnet port (default 23).
            username: Login username.
            password: Login password.
            prompt: Command prompt indicator.
            timeout: Connection timeout in seconds.
            
        Returns:
            A BGPServerSession that maintains a persistent connection.
        """
        session_key = self._get_session_key(host, port, username)
        
        async with self._lock:
            # Return existing session if available
            if session_key in self.sessions:
                session = self.sessions[session_key]
                logger.debug(f"✓ Returning existing session for {host}")
                return session
            
            # Create new session
            logger.debug(f"Creating new session for {host}")
            session = BGPServerSession(
                host=host,
                port=port,
                username=username,
                password=password,
                prompt=prompt,
                timeout=timeout,
            )
            
            self.sessions[session_key] = session
        
        # Connect outside the lock
        await session.connect()
        return session

    async def close_all(self) -> None:
        """Close all sessions."""
        async with self._lock:
            sessions = list(self.sessions.values())
        
        for session in sessions:
            try:
                await session.close()
            except Exception as e:
                logger.warning(f"Error closing session: {e}")
        
        async with self._lock:
            self.sessions.clear()
        
        logger.info(f"✓ Closed {len(sessions)} sessions")


# Global session manager instance
_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Get or create the global session manager.
    
    Returns:
        The global SessionManager instance.
    """
    global _manager
    if _manager is None:
        _manager = SessionManager()
    return _manager


async def close_session_manager() -> None:
    """Close the global session manager."""
    global _manager
    if _manager is not None:
        await _manager.close_all()
        _manager = None

"""Simple on-demand BGP server connections (no persistent sessions)."""

import asyncio
import logging
from typing import Dict, Optional

from bgp_client import BGPTelnetClient

logger = logging.getLogger(__name__)

# Global session manager instance
_session_manager: Optional['SessionManager'] = None


def get_session_manager() -> 'SessionManager':
    """Get or create global session manager."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
        logger.info("Initialized global session manager")
    return _session_manager


def close_session_manager() -> None:
    """Close and cleanup global session manager."""
    global _session_manager
    if _session_manager:
        try:
            asyncio.run(_session_manager.close())
        except Exception:
            pass
        _session_manager = None


class SessionManager:
    """Manages on-demand connections to multiple BGP servers."""

    def __init__(self):
        """Initialize session manager."""
        self.clients: Dict[str, BGPTelnetClient] = {}
        logger.info("Initialized global session manager")

    async def get_session(
        self,
        host: str,
        port: int = 23,
        username: str = "",
        password: str = "",
        prompt: str = "#",
        timeout: int = 15,
    ) -> BGPTelnetClient:
        """Get or create a BGP client connection.
        
        Creates a new connection on each call (no persistence).
        This is fast enough for the RouteViews servers we're using.
        
        Args:
            host: Hostname or IP address.
            port: Telnet port (default 23).
            username: Login username (empty = anonymous).
            password: Login password.
            prompt: Command prompt indicator.
            timeout: Connection timeout in seconds.
            
        Returns:
            Connected BGPTelnetClient ready for commands.
        """
        # Create new client - these RouteViews servers are fast enough
        # that creating a new connection per request is acceptable
        client = BGPTelnetClient(
            host=host,
            port=port,
            username=username,
            password=password,
            prompt=prompt,
            timeout=timeout,
        )
        
        # Connect and authenticate
        await client.connect()
        
        return client

    async def close(self) -> None:
        """Close all active clients."""
        for client in self.clients.values():
            try:
                await client.close()
            except Exception:
                pass
        self.clients.clear()
        logger.info("✓ Closed all connections")

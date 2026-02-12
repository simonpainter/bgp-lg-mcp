"""Connection pool for managing BGP telnet client connections."""

import asyncio
import logging
from typing import Dict, Optional, Tuple
from bgp_client import BGPTelnetClient

logger = logging.getLogger(__name__)


class ConnectionPool:
    """Thread-safe connection pool for BGP telnet clients.
    
    Maintains a pool of authenticated telnet connections to avoid the
    overhead of authentication on every query.
    """

    def __init__(self, max_connections: int = 5, connection_timeout: int = 300):
        """Initialize connection pool.
        
        Args:
            max_connections: Maximum number of connections per server (default: 5).
            connection_timeout: How long to keep idle connections (seconds, default: 5 min).
        """
        self.max_connections = max_connections
        self.connection_timeout = connection_timeout
        
        # Maps server_key -> list of available connections
        self._pool: Dict[str, list[Tuple[BGPTelnetClient, float]]] = {}
        
        # Maps server_key -> number of active connections
        self._active: Dict[str, int] = {}
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
        
        logger.info(f"Initialized connection pool (max {max_connections} per server, {connection_timeout}s timeout)")

    def _get_server_key(self, host: str, port: int, username: str) -> str:
        """Get unique key for a server configuration."""
        return f"{host}:{port}:{username}"

    async def get_connection(
        self,
        host: str,
        port: int = 23,
        username: str = "",
        password: str = "",
        prompt: str = "#",
        timeout: int = 15,
    ) -> BGPTelnetClient:
        """Get a connection from the pool or create a new one.
        
        Args:
            host: Hostname or IP address.
            port: Telnet port (default 23).
            username: Login username.
            password: Login password.
            prompt: Command prompt indicator.
            timeout: Connection timeout in seconds.
            
        Returns:
            An authenticated BGPTelnetClient ready for use.
            
        Raises:
            ConnectionError: If unable to create or acquire a connection.
        """
        server_key = self._get_server_key(host, port, username)
        
        async with self._lock:
            # Check for available connections in pool
            if server_key in self._pool and self._pool[server_key]:
                conn, _ = self._pool[server_key].pop()
                logger.debug(f"✓ Reusing pooled connection to {server_key}")
                return conn
            
            # Check if we can create a new connection
            active_count = self._active.get(server_key, 0)
            if active_count >= self.max_connections:
                logger.warning(f"⚠ Connection pool exhausted for {server_key} ({active_count}/{self.max_connections})")
                # Wait for a connection to be returned
                # For now, raise an error - could implement queue waiting in future
                raise ConnectionError(
                    f"Connection pool exhausted for {server_key}. "
                    f"Max {self.max_connections} connections allowed."
                )
            
            # Create new connection
            self._active[server_key] = active_count + 1
            logger.debug(f"Creating new connection to {server_key} ({active_count + 1}/{self.max_connections})")
        
        # Connect outside the lock to avoid blocking other operations
        try:
            client = BGPTelnetClient(
                host=host,
                port=port,
                username=username,
                password=password,
                prompt=prompt,
                timeout=timeout,
            )
            await client.connect()
            logger.info(f"✓ Created and authenticated new connection to {server_key}")
            return client
        except Exception as e:
            async with self._lock:
                self._active[server_key] -= 1
            logger.error(f"✗ Failed to create connection to {server_key}: {e}")
            raise

    async def return_connection(
        self,
        client: BGPTelnetClient,
        host: str,
        port: int = 23,
        username: str = "",
    ) -> None:
        """Return a connection to the pool for reuse.
        
        Args:
            client: The BGPTelnetClient to return.
            host: Hostname or IP address (for pool key).
            port: Telnet port (for pool key).
            username: Login username (for pool key).
        """
        server_key = self._get_server_key(host, port, username)
        
        async with self._lock:
            if server_key not in self._pool:
                self._pool[server_key] = []
            
            import time
            self._pool[server_key].append((client, time.time()))
            logger.debug(f"✓ Returned connection to pool for {server_key} ({len(self._pool[server_key])} available)")

    async def release_connection(
        self,
        client: BGPTelnetClient,
        host: str,
        port: int = 23,
        username: str = "",
    ) -> None:
        """Release a connection without returning it to the pool.
        
        Args:
            client: The BGPTelnetClient to close.
            host: Hostname or IP address (for pool key).
            port: Telnet port (for pool key).
            username: Login username (for pool key).
        """
        server_key = self._get_server_key(host, port, username)
        
        await client.close()
        
        async with self._lock:
            active_count = self._active.get(server_key, 1)
            self._active[server_key] = max(0, active_count - 1)
            logger.debug(f"Released connection from {server_key} ({self._active[server_key]} active)")

    async def close_all(self) -> None:
        """Close all pooled connections."""
        async with self._lock:
            total = 0
            for server_key, connections in self._pool.items():
                for client, _ in connections:
                    try:
                        await client.close()
                    except Exception as e:
                        logger.warning(f"Error closing connection: {e}")
                total += len(connections)
            
            self._pool.clear()
            self._active.clear()
            logger.info(f"✓ Closed {total} pooled connections")

    async def cleanup_stale_connections(self) -> None:
        """Remove stale connections from the pool.
        
        Removes connections that have exceeded the timeout threshold.
        """
        import time
        current_time = time.time()
        
        async with self._lock:
            removed = 0
            for server_key in list(self._pool.keys()):
                connections = self._pool[server_key]
                self._pool[server_key] = []
                
                for client, last_used in connections:
                    age = current_time - last_used
                    if age < self.connection_timeout:
                        self._pool[server_key].append((client, last_used))
                    else:
                        try:
                            await client.close()
                        except Exception as e:
                            logger.debug(f"Error closing stale connection: {e}")
                        removed += 1
            
            if removed > 0:
                logger.info(f"✓ Cleaned up {removed} stale connections")


# Global connection pool instance
_pool: Optional[ConnectionPool] = None


def get_pool(max_connections: int = 5, connection_timeout: int = 300) -> ConnectionPool:
    """Get or create the global connection pool.
    
    Args:
        max_connections: Maximum connections per server.
        connection_timeout: Idle connection timeout in seconds.
        
    Returns:
        The global ConnectionPool instance.
    """
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            max_connections=max_connections,
            connection_timeout=connection_timeout,
        )
    return _pool


async def cleanup_pool() -> None:
    """Clean up the global connection pool."""
    global _pool
    if _pool is not None:
        await _pool.close_all()
        _pool = None

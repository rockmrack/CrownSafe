"""Azure Blob Storage Connection Pool Manager
Enterprise-grade connection pooling for optimal performance

Features:
- Connection pooling for Azure Blob Storage clients
- Automatic connection lifecycle management
- Thread-safe operations
- Connection health monitoring
- Configurable pool size
"""

import logging
import os
import threading
from datetime import datetime, timezone

from azure.storage.blob import BlobServiceClient

logger = logging.getLogger(__name__)


class AzureBlobConnectionPool:
    """Connection pool manager for Azure Blob Storage
    Maintains a pool of reusable BlobServiceClient instances
    """

    def __init__(
        self,
        connection_string: str | None = None,
        account_name: str | None = None,
        account_key: str | None = None,
        pool_size: int = 10,
    ) -> None:
        """Initialize connection pool

        Args:
            connection_string: Azure Storage connection string
            account_name: Storage account name
            account_key: Storage account key
            pool_size: Maximum number of connections in pool

        """
        self.connection_string = connection_string or os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        self.account_name = account_name or os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
        self.account_key = account_key or os.getenv("AZURE_STORAGE_ACCOUNT_KEY")
        self.pool_size = pool_size

        # Connection pool
        self._pool = []
        self._pool_lock = threading.Lock()
        self._in_use = set()

        # Statistics
        self.connections_created = 0
        self.connections_reused = 0
        self.pool_exhaustion_count = 0

        # Initialize pool
        self._initialize_pool()

        logger.info(f"Azure Blob connection pool initialized (size: {pool_size})")

    def _initialize_pool(self) -> None:
        """Pre-create connections in the pool"""
        with self._pool_lock:
            for _ in range(self.pool_size):
                client = self._create_client()
                if client:
                    self._pool.append(
                        {
                            "client": client,
                            "created_at": datetime.now(timezone.utc),
                            "last_used": datetime.now(timezone.utc),
                            "use_count": 0,
                        },
                    )
                    self.connections_created += 1

    def _create_client(self) -> BlobServiceClient | None:
        """Create a new BlobServiceClient"""
        try:
            if self.connection_string:
                return BlobServiceClient.from_connection_string(self.connection_string)
            elif self.account_name and self.account_key:
                account_url = f"https://{self.account_name}.blob.core.windows.net"
                return BlobServiceClient(account_url=account_url, credential=self.account_key)
            else:
                logger.error("Azure Storage credentials not configured")
                return None
        except Exception as e:
            logger.error(f"Failed to create Azure Blob client: {e}")
            return None

    def acquire(self) -> BlobServiceClient | None:
        """Acquire a connection from the pool

        Returns:
            BlobServiceClient instance or None if pool exhausted

        """
        with self._pool_lock:
            if self._pool:
                # Get connection from pool
                conn_data = self._pool.pop(0)
                conn_data["last_used"] = datetime.now(timezone.utc)
                conn_data["use_count"] += 1

                self._in_use.add(id(conn_data["client"]))
                self.connections_reused += 1

                logger.debug(f"Acquired connection from pool (pool: {len(self._pool)}, in_use: {len(self._in_use)})")
                return conn_data["client"]
            else:
                # Pool exhausted
                self.pool_exhaustion_count += 1
                logger.warning(
                    f"Connection pool exhausted "
                    f"(in_use: {len(self._in_use)}, exhaustions: {self.pool_exhaustion_count})",
                )

                # Create new connection on-demand
                client = self._create_client()
                if client:
                    self._in_use.add(id(client))
                    self.connections_created += 1
                    return client

                return None

    def release(self, client: BlobServiceClient) -> None:
        """Release a connection back to the pool

        Args:
            client: BlobServiceClient to release

        """
        if client is None:
            return

        with self._pool_lock:
            client_id = id(client)

            if client_id in self._in_use:
                self._in_use.remove(client_id)

                # Return to pool if under capacity
                if len(self._pool) < self.pool_size:
                    self._pool.append(
                        {
                            "client": client,
                            "created_at": datetime.now(timezone.utc),
                            "last_used": datetime.now(timezone.utc),
                            "use_count": 0,
                        },
                    )
                    logger.debug(f"Released connection to pool (pool: {len(self._pool)}, in_use: {len(self._in_use)})")
                else:
                    # Pool full, close connection
                    try:
                        client.close()
                    except Exception as e:
                        logger.warning(f"Error closing connection: {e}")

    def get_stats(self) -> dict:
        """Get connection pool statistics

        Returns:
            Dictionary with pool statistics

        """
        with self._pool_lock:
            return {
                "pool_size": self.pool_size,
                "available_connections": len(self._pool),
                "in_use_connections": len(self._in_use),
                "connections_created": self.connections_created,
                "connections_reused": self.connections_reused,
                "pool_exhaustion_count": self.pool_exhaustion_count,
                "reuse_rate_percent": (
                    round(
                        self.connections_reused / (self.connections_created + self.connections_reused) * 100,
                        2,
                    )
                    if (self.connections_created + self.connections_reused) > 0
                    else 0.0
                ),
            }

    def clear_pool(self) -> None:
        """Clear all connections in the pool (emergency use)"""
        with self._pool_lock:
            for conn_data in self._pool:
                try:
                    conn_data["client"].close()
                except Exception as e:
                    logger.warning(f"Error closing connection during clear: {e}")

            self._pool.clear()
            logger.warning("Connection pool cleared")


# Global connection pool instance
_connection_pool = None
_pool_lock = threading.Lock()


def get_connection_pool(
    connection_string: str | None = None,
    account_name: str | None = None,
    account_key: str | None = None,
    pool_size: int = 10,
) -> AzureBlobConnectionPool:
    """Get or create global connection pool instance

    Args:
        connection_string: Azure Storage connection string
        account_name: Storage account name
        account_key: Storage account key
        pool_size: Maximum number of connections in pool

    Returns:
        AzureBlobConnectionPool instance

    """
    global _connection_pool

    with _pool_lock:
        if _connection_pool is None:
            _connection_pool = AzureBlobConnectionPool(
                connection_string=connection_string,
                account_name=account_name,
                account_key=account_key,
                pool_size=pool_size,
            )

        return _connection_pool

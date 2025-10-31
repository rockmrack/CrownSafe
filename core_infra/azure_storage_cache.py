"""
Azure Storage SAS URL Caching with Redis
Enterprise-grade performance optimization for Azure Blob Storage

Features:
- SAS URL caching with Redis (23-hour TTL)
- Automatic cache invalidation
- Performance metrics tracking
- Cache hit/miss monitoring
- Thread-safe operations
"""

import hashlib
import json
import logging
from datetime import datetime
from typing import Optional

import redis

logger = logging.getLogger(__name__)


class AzureStorageCacheManager:
    """
    Redis-based cache manager for Azure Storage SAS URLs
    Reduces API calls and improves performance
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        default_ttl_hours: int = 23,
        key_prefix: str = "azure_sas:",
    ):
        """
        Initialize cache manager

        Args:
            redis_url: Redis connection URL (e.g., 'redis://localhost:6379/0')
            default_ttl_hours: Default cache TTL in hours (23 hours < 24h SAS expiry)
            key_prefix: Redis key prefix for SAS URLs
        """
        self.redis_url = redis_url
        self.default_ttl_hours = default_ttl_hours
        self.key_prefix = key_prefix

        # Initialize Redis client
        try:
            if redis_url:
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                # Test connection
                self.redis_client.ping()
                self.cache_enabled = True
                logger.info("Azure Storage cache initialized with Redis")
            else:
                self.cache_enabled = False
                self.redis_client = None
                logger.warning("Redis URL not provided, SAS URL caching disabled")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}. Caching disabled.")
            self.cache_enabled = False
            self.redis_client = None

        # Performance metrics
        self.cache_hits = 0
        self.cache_misses = 0
        self.cache_invalidations = 0

    def _generate_cache_key(self, blob_name: str, container_name: str, permissions: str = "r") -> str:
        """
        Generate deterministic cache key for SAS URL

        Args:
            blob_name: Blob name
            container_name: Container name
            permissions: Permission string

        Returns:
            Redis cache key
        """
        # Include permissions in key to differentiate read/write URLs
        key_components = f"{container_name}:{blob_name}:{permissions}"
        key_hash = hashlib.sha256(key_components.encode()).hexdigest()[:16]
        return f"{self.key_prefix}{key_hash}"

    def get_cached_sas_url(
        self,
        blob_name: str,
        container_name: str,
        permissions: str = "r",
    ) -> Optional[str]:
        """
        Retrieve cached SAS URL from Redis

        Args:
            blob_name: Blob name
            container_name: Container name
            permissions: Permission string

        Returns:
            Cached SAS URL or None if not found/expired
        """
        if not self.cache_enabled:
            return None

        try:
            cache_key = self._generate_cache_key(blob_name, container_name, permissions)
            cached_data = self.redis_client.get(cache_key)

            if cached_data:
                data = json.loads(cached_data)
                sas_url = data.get("sas_url")
                cached_at = datetime.fromisoformat(data.get("cached_at"))

                # Verify cache hasn't expired (double-check)
                age_hours = (datetime.utcnow() - cached_at).total_seconds() / 3600
                if age_hours < self.default_ttl_hours:
                    self.cache_hits += 1
                    logger.debug(f"Cache HIT for {blob_name} (age: {age_hours:.1f}h)")
                    return sas_url
                else:
                    # Expired cache entry (shouldn't happen with TTL)
                    self.redis_client.delete(cache_key)
                    logger.warning(f"Expired cache entry deleted: {blob_name}")

            self.cache_misses += 1
            logger.debug(f"Cache MISS for {blob_name}")
            return None

        except Exception as e:
            logger.error(f"Cache retrieval error for {blob_name}: {e}")
            self.cache_misses += 1
            return None

    def cache_sas_url(
        self,
        blob_name: str,
        container_name: str,
        sas_url: str,
        permissions: str = "r",
        ttl_hours: Optional[int] = None,
    ) -> bool:
        """
        Cache SAS URL in Redis with TTL

        Args:
            blob_name: Blob name
            container_name: Container name
            sas_url: Generated SAS URL
            permissions: Permission string
            ttl_hours: Custom TTL in hours (defaults to default_ttl_hours)

        Returns:
            True if cached successfully, False otherwise
        """
        if not self.cache_enabled:
            return False

        try:
            cache_key = self._generate_cache_key(blob_name, container_name, permissions)
            ttl = ttl_hours or self.default_ttl_hours

            cache_data = {
                "sas_url": sas_url,
                "blob_name": blob_name,
                "container_name": container_name,
                "permissions": permissions,
                "cached_at": datetime.utcnow().isoformat(),
            }

            # Set with TTL in seconds
            ttl_seconds = int(ttl * 3600)
            self.redis_client.setex(cache_key, ttl_seconds, json.dumps(cache_data))

            logger.debug(f"Cached SAS URL for {blob_name} (TTL: {ttl}h)")
            return True

        except Exception as e:
            logger.error(f"Cache storage error for {blob_name}: {e}")
            return False

    def invalidate_cache(
        self,
        blob_name: str,
        container_name: str,
        permissions: Optional[str] = None,
    ) -> bool:
        """
        Invalidate cached SAS URL (on blob delete/update)

        Args:
            blob_name: Blob name
            container_name: Container name
            permissions: Permission string (if None, invalidates all permissions)

        Returns:
            True if invalidated successfully, False otherwise
        """
        if not self.cache_enabled:
            return False

        try:
            if permissions:
                # Invalidate specific permission
                cache_key = self._generate_cache_key(blob_name, container_name, permissions)
                deleted = self.redis_client.delete(cache_key)
                if deleted:
                    self.cache_invalidations += 1
                    logger.info(f"Invalidated cache for {blob_name} (permissions: {permissions})")
                return bool(deleted)
            else:
                # Invalidate all permissions (read, write, delete)
                permissions_list = ["r", "w", "d", "rw", "rd", "wd", "rwd"]
                deleted_count = 0
                for perm in permissions_list:
                    cache_key = self._generate_cache_key(blob_name, container_name, perm)
                    deleted = self.redis_client.delete(cache_key)
                    deleted_count += deleted

                if deleted_count > 0:
                    self.cache_invalidations += deleted_count
                    logger.info(f"Invalidated {deleted_count} cache entries for {blob_name}")

                return deleted_count > 0

        except Exception as e:
            logger.error(f"Cache invalidation error for {blob_name}: {e}")
            return False

    def clear_all_cache(self) -> int:
        """
        Clear all cached SAS URLs (emergency use only)

        Returns:
            Number of keys deleted
        """
        if not self.cache_enabled:
            return 0

        try:
            pattern = f"{self.key_prefix}*"
            keys = list(self.redis_client.scan_iter(match=pattern))
            if keys:
                deleted = self.redis_client.delete(*keys)
                self.cache_invalidations += deleted
                logger.warning(f"Cleared {deleted} cached SAS URLs")
                return deleted
            return 0

        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return 0

    def get_cache_stats(self) -> dict:
        """
        Get cache performance statistics

        Returns:
            Dictionary with cache statistics
        """
        total_requests = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total_requests * 100) if total_requests > 0 else 0.0

        return {
            "cache_enabled": self.cache_enabled,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "total_requests": total_requests,
            "hit_rate_percent": round(hit_rate, 2),
            "cache_invalidations": self.cache_invalidations,
            "redis_connected": self.redis_client is not None and self.cache_enabled,
        }

    def reset_stats(self):
        """Reset performance statistics"""
        self.cache_hits = 0
        self.cache_misses = 0
        self.cache_invalidations = 0
        logger.info("Cache statistics reset")


# Global cache manager instance
azure_storage_cache = None


def get_cache_manager(redis_url: Optional[str] = None) -> AzureStorageCacheManager:
    """
    Get or create global cache manager instance

    Args:
        redis_url: Redis connection URL (optional, uses env var if not provided)

    Returns:
        AzureStorageCacheManager instance
    """
    global azure_storage_cache

    if azure_storage_cache is None:
        import os

        redis_url = redis_url or os.getenv("REDIS_URL")
        azure_storage_cache = AzureStorageCacheManager(redis_url=redis_url)

    return azure_storage_cache

"""Redis micro-cache for search results
Provides short-term caching with automatic invalidation.
"""

import hashlib
import json
import logging
import os
from typing import Any

from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class RedisSearchCache:
    """Redis-based cache for search results."""

    def __init__(self, redis_client: Redis | None = None) -> None:
        """Initialize cache with Redis client.

        Args:
            redis_client: Existing Redis client or None to create new

        """
        self.redis = redis_client
        self.ttl = int(os.getenv("SEARCH_CACHE_TTL", "60"))  # Default 60 seconds
        self.enabled = os.getenv("SEARCH_CACHE_ENABLED", "true").lower() == "true"
        self.key_prefix = "search:v1:"
        self.epoch_key = "search:epoch"

    async def connect(self) -> None:
        """Connect to Redis if not already connected."""
        if not self.redis and self.enabled:
            try:
                redis_url = os.getenv(
                    "REDIS_CACHE_URL",
                    os.getenv("RATE_LIMIT_REDIS_URL", "redis://localhost:6379/0"),
                )
                self.redis = Redis.from_url(redis_url, encoding="utf-8", decode_responses=True)
                await self.redis.ping()
                logger.info(f"Redis cache connected to {redis_url}")
            except Exception as e:
                logger.warning(f"Redis cache connection failed: {e}")
                self.enabled = False

    async def close(self) -> None:
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()

    def _make_cache_key(
        self,
        filters_hash: str,
        as_of: str,
        after_tuple: tuple | None = None,
    ) -> str:
        """Generate cache key for search results.

        Args:
            filters_hash: Hash of search filters
            as_of: Snapshot timestamp
            after_tuple: Pagination cursor tuple

        Returns:
            Redis key string

        """
        # Get current epoch for cache invalidation
        epoch = "0"  # Default if can't get from Redis

        # Build key components
        components = [
            self.key_prefix,
            epoch,
            filters_hash,
            as_of.replace(":", "-").replace(".", "-"),  # Make timestamp Redis-safe
        ]

        # Add pagination info if present
        if after_tuple:
            after_str = f"{after_tuple[0]:.6f}:{after_tuple[1]}:{after_tuple[2]}"
            after_hash = hashlib.sha256(after_str.encode()).hexdigest()[:12]
            components.append(after_hash)

        return ":".join(components)

    async def get(
        self,
        filters_hash: str,
        as_of: str,
        after_tuple: tuple | None = None,
    ) -> dict[str, Any] | None:
        """Get cached search results.

        Args:
            filters_hash: Hash of search filters
            as_of: Snapshot timestamp
            after_tuple: Pagination cursor tuple

        Returns:
            Cached results or None if not found/expired

        """
        if not self.enabled or not self.redis:
            return None

        try:
            # Get current epoch
            epoch = await self.redis.get(self.epoch_key) or "0"

            # Build key with epoch
            key = self._make_cache_key(filters_hash, as_of, after_tuple)
            # Update key with actual epoch
            key_parts = key.split(":")
            key_parts[2] = epoch  # Replace default epoch with actual
            key = ":".join(key_parts)

            # Get cached value
            cached = await self.redis.get(key)
            if cached:
                logger.debug(f"Cache hit for key: {key}")
                return json.loads(cached)
            logger.debug(f"Cache miss for key: {key}")
            return None

        except Exception as e:
            logger.warning(f"Cache get error: {e}")
            return None

    async def set(
        self,
        filters_hash: str,
        as_of: str,
        after_tuple: tuple | None,
        value: dict[str, Any],
        ttl: int | None = None,
    ) -> bool:
        """Set cached search results.

        Args:
            filters_hash: Hash of search filters
            as_of: Snapshot timestamp
            after_tuple: Pagination cursor tuple
            value: Results to cache
            ttl: Time to live in seconds

        Returns:
            True if cached successfully

        """
        if not self.enabled or not self.redis:
            return False

        try:
            # Get current epoch
            epoch = await self.redis.get(self.epoch_key) or "0"

            # Build key with epoch
            key = self._make_cache_key(filters_hash, as_of, after_tuple)
            key_parts = key.split(":")
            key_parts[2] = epoch
            key = ":".join(key_parts)

            # Serialize value
            serialized = json.dumps(value, separators=(",", ":"))

            # Set with TTL
            cache_ttl = ttl or self.ttl
            await self.redis.setex(key, cache_ttl, serialized)

            logger.debug(f"Cached results for key: {key} (TTL: {cache_ttl}s)")
            return True

        except Exception as e:
            logger.warning(f"Cache set error: {e}")
            return False

    async def invalidate_all(self) -> None:
        """Invalidate all cached search results by incrementing epoch."""
        if not self.enabled or not self.redis:
            return

        try:
            # Increment epoch to invalidate all existing cache keys
            new_epoch = await self.redis.incr(self.epoch_key)
            logger.info(f"Cache invalidated, new epoch: {new_epoch}")

            # Set TTL on epoch key to prevent it from growing forever
            await self.redis.expire(self.epoch_key, 86400)  # 24 hours

        except Exception as e:
            logger.warning(f"Cache invalidation error: {e}")

    async def invalidate_pattern(self, pattern: str) -> None:
        """Invalidate cache keys matching a pattern.

        Args:
            pattern: Redis key pattern (e.g., "search:v1:*:FDA*")

        """
        if not self.enabled or not self.redis:
            return

        try:
            # Find matching keys
            cursor = 0
            deleted = 0

            while True:
                cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)

                if keys:
                    deleted += await self.redis.delete(*keys)

                if cursor == 0:
                    break

            if deleted > 0:
                logger.info(f"Invalidated {deleted} cache keys matching pattern: {pattern}")

        except Exception as e:
            logger.warning(f"Pattern invalidation error: {e}")

    async def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats

        """
        if not self.enabled or not self.redis:
            return {"enabled": False}

        try:
            # Get info
            info = await self.redis.info("stats")
            memory = await self.redis.info("memory")

            # Count cache keys
            cursor = 0
            key_count = 0
            pattern = f"{self.key_prefix}*"

            while True:
                cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)
                key_count += len(keys)
                if cursor == 0:
                    break

            # Get epoch
            epoch = await self.redis.get(self.epoch_key) or "0"

            return {
                "enabled": True,
                "connected": True,
                "keys": key_count,
                "epoch": epoch,
                "memory_used_mb": round(memory.get("used_memory", 0) / (1024 * 1024), 2),
                "hits": info.get("keyspace_hits", 0),
                "misses": info.get("keyspace_misses", 0),
                "hit_rate": round(
                    info.get("keyspace_hits", 0)
                    / max(info.get("keyspace_hits", 0) + info.get("keyspace_misses", 1), 1)
                    * 100,
                    2,
                ),
            }

        except Exception as e:
            logger.warning(f"Stats error: {e}")
            return {"enabled": True, "connected": False, "error": str(e)}


# Global cache instance
_cache: RedisSearchCache | None = None


async def get_cache() -> RedisSearchCache:
    """Get global cache instance."""
    global _cache
    if _cache is None:
        _cache = RedisSearchCache()
        await _cache.connect()
    return _cache


async def close_cache() -> None:
    """Close global cache instance."""
    global _cache
    if _cache:
        await _cache.close()
        _cache = None

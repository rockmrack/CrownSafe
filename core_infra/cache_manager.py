#!/usr/bin/env python3
# core_infra/cache_manager.py
# Redis Cache Manager for BabyShield - Optimized for 39 International Agencies

import hashlib
import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

# Make redis optional (for test environments without Redis)
try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    redis: Optional[Any] = None
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)


class CustomJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)


class BabyShieldCacheManager:
    """
    High-performance Redis cache manager optimized for BabyShield's 39-agency recall system.
    Provides intelligent caching strategies for maximum speed with data freshness.
    """

    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.redis_client = None
        self.cache_enabled = True

        # Cache duration settings (optimized for recall data)
        self.CACHE_DURATIONS = {
            "recall_query": 3600,  # 1 hour - recall queries
            "product_lookup": 7200,  # 2 hours - product identification
            "agency_status": 300,  # 5 minutes - agency health
            "barcode_lookup": 1800,  # 30 minutes - barcode resolution
            "safety_check": 1800,  # 30 minutes - full safety check
            "user_data": 900,  # 15 minutes - user information
        }

        # Cache key prefixes
        self.PREFIXES = {
            "recall": "bsc:recall:",
            "product": "bsc:product:",
            "agency": "bsc:agency:",
            "barcode": "bsc:barcode:",
            "safety": "bsc:safety:",
            "user": "bsc:user:",
            "stats": "bsc:stats:",
        }

        self.init_redis()

    def init_redis(self):
        """Initialize Redis connection with error handling"""
        if not REDIS_AVAILABLE:
            logger.debug("Redis library not installed. Cache disabled.")
            self.cache_enabled = False
            self.redis_client = None
            return

        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30,
            )

            # Test connection
            self.redis_client.ping()
            logger.info("✅ Redis cache manager initialized successfully")

        except Exception as e:
            if os.environ.get("DISABLE_REDIS_WARNING", "false").lower() != "true":
                logger.warning(f"⚠️ Redis unavailable: {e}. Disabling cache.")
            else:
                logger.debug("Redis not configured. Cache disabled.")
            self.cache_enabled = False
            self.redis_client = None

    def _generate_cache_key(self, prefix: str, identifier: str, **kwargs) -> str:
        """Generate deterministic cache key with additional parameters"""
        # Create a hash of the identifier and any additional params
        key_data = f"{identifier}:{json.dumps(sorted(kwargs.items()), separators=(',', ':'))}"
        key_hash = hashlib.md5(key_data.encode()).hexdigest()[:12]
        return f"{prefix}{key_hash}:{identifier}"

    def get(self, cache_type: str, identifier: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Get cached data with automatic JSON deserialization"""
        if not self.cache_enabled or not self.redis_client:
            return None

        try:
            prefix = self.PREFIXES.get(cache_type, f"bsc:{cache_type}:")
            cache_key = self._generate_cache_key(prefix, identifier, **kwargs)

            cached_data = self.redis_client.get(cache_key)
            if cached_data:
                result = json.loads(cached_data)
                logger.debug(f"🎯 Cache HIT: {cache_key[:50]}...")
                return result
            else:
                logger.debug(f"❌ Cache MISS: {cache_key[:50]}...")
                return None

        except Exception as e:
            logger.warning(f"Cache get error: {e}")
            return None

    def set(
        self,
        cache_type: str,
        identifier: str,
        data: Any,
        custom_ttl: Optional[int] = None,
        **kwargs,
    ) -> bool:
        """Set cached data with automatic JSON serialization and TTL"""
        if not self.cache_enabled or not self.redis_client:
            return False

        try:
            prefix = self.PREFIXES.get(cache_type, f"bsc:{cache_type}:")
            cache_key = self._generate_cache_key(prefix, identifier, **kwargs)
            ttl = custom_ttl or self.CACHE_DURATIONS.get(cache_type, 1800)

            # Add metadata
            cache_data = {
                "data": data,
                "cached_at": datetime.now().isoformat(),
                "cache_type": cache_type,
                "ttl": ttl,
            }

            self.redis_client.setex(
                cache_key,
                ttl,
                json.dumps(cache_data, cls=CustomJsonEncoder, separators=(",", ":")),
            )

            logger.debug(f"💾 Cache SET: {cache_key[:50]}... (TTL: {ttl}s)")
            return True

        except Exception as e:
            logger.warning(f"Cache set error: {e}")
            return False

    def delete(self, cache_type: str, identifier: str, **kwargs) -> bool:
        """Delete specific cached item"""
        if not self.cache_enabled or not self.redis_client:
            return False

        try:
            prefix = self.PREFIXES.get(cache_type, f"bsc:{cache_type}:")
            cache_key = self._generate_cache_key(prefix, identifier, **kwargs)

            deleted = self.redis_client.delete(cache_key)
            if deleted:
                logger.debug(f"🗑️ Cache DELETE: {cache_key[:50]}...")
            return bool(deleted)

        except Exception as e:
            logger.warning(f"Cache delete error: {e}")
            return False

    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate multiple cache keys matching a pattern"""
        if not self.cache_enabled or not self.redis_client:
            return 0

        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                deleted = self.redis_client.delete(*keys)
                logger.info(f"🧹 Cache INVALIDATED: {deleted} keys matching '{pattern}'")
                return deleted
            return 0

        except Exception as e:
            logger.warning(f"Cache pattern invalidation error: {e}")
            return 0

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        if not self.cache_enabled or not self.redis_client:
            return {"status": "disabled"}

        try:
            info = self.redis_client.info()
            return {
                "status": "enabled",
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_human": info.get("used_memory_human", "0B"),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "total_keys": sum(
                    db.get("keys", 0) for db in info.get("keyspace", {}).values() if isinstance(db, dict)
                ),
                "hit_rate": round(
                    info.get("keyspace_hits", 0)
                    / max(1, info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0))
                    * 100,
                    2,
                ),
            }
        except Exception as e:
            logger.error(f"Cache stats error: {e}")
            return {"status": "error", "error": str(e)}

    def health_check(self) -> bool:
        """Check if Redis is healthy"""
        try:
            if not self.cache_enabled or not self.redis_client:
                return False
            self.redis_client.ping()
            return True
        except Exception:
            return False


# Global cache manager instance
cache_manager = BabyShieldCacheManager()


# Convenience functions for easy usage
def get_cached(cache_type: str, identifier: str, **kwargs) -> Optional[Dict[str, Any]]:
    """Get cached data"""
    result = cache_manager.get(cache_type, identifier, **kwargs)
    return result.get("data") if result else None


def set_cached(cache_type: str, identifier: str, data: Any, ttl: Optional[int] = None, **kwargs) -> bool:
    """Set cached data"""
    return cache_manager.set(cache_type, identifier, data, ttl, **kwargs)


def delete_cached(cache_type: str, identifier: str, **kwargs) -> bool:
    """Delete cached data"""
    return cache_manager.delete(cache_type, identifier, **kwargs)


def invalidate_pattern(pattern: str) -> int:
    """
    Invalidate multiple cache keys matching a Redis pattern.

    This is a module-level convenience function that delegates to the
    BabyShieldCacheManager instance.

    Args:
        pattern (str): Redis key pattern to match for invalidation.
            Example: "bsc:recall:*" will match all recall cache keys.

    Returns:
        int: The number of keys deleted from the cache.

    Example:
        >>> invalidate_pattern("bsc:recall:*")
        5
    """
    return cache_manager.invalidate_pattern(pattern)


def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics"""
    return cache_manager.get_cache_stats()


# Cache decorators for easy function caching
def cache_result(cache_type: str, ttl: Optional[int] = None, key_func=None):
    """Decorator to cache function results"""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Generate cache key from function arguments
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}_{hash(str(args) + str(sorted(kwargs.items())))}"

            # Try to get from cache first
            cached_result = get_cached(cache_type, cache_key)
            if cached_result is not None:
                return cached_result

            # Execute function if not cached
            result = await func(*args, **kwargs)

            # Cache the result
            set_cached(cache_type, cache_key, result, ttl)

            return result

        return wrapper

    return decorator

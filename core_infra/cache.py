"""Query Result Caching Module.

This module provides caching decorators and utilities for expensive database queries.
Uses in-memory TTL caches to reduce database load for frequently accessed data.
"""

import hashlib
import json
import logging
from collections.abc import Callable
from functools import wraps

from cachetools import TTLCache

logger = logging.getLogger(__name__)

# Cache configurations
# Recall queries cache: 1000 items, 5 minute TTL
recall_cache = TTLCache(maxsize=1000, ttl=300)

# Product safety cache: 500 items, 10 minute TTL
safety_cache = TTLCache(maxsize=500, ttl=600)

# User profile cache: 1000 items, 2 minute TTL
user_cache = TTLCache(maxsize=1000, ttl=120)

# Agency data cache: 50 items, 1 hour TTL (agency data changes infrequently)
agency_cache = TTLCache(maxsize=50, ttl=3600)


def generate_cache_key(*args, **kwargs) -> str:
    """Generate a cache key from function arguments.

    Args:
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        SHA-256 hash of serialized arguments

    """
    try:
        # Serialize arguments to JSON
        key_data = json.dumps(
            {
                "args": args,
                "kwargs": sorted(kwargs.items()),
            },
            default=str,  # Handle non-serializable objects
            sort_keys=True,
        )
        # Generate hash
        return hashlib.sha256(key_data.encode("utf-8")).hexdigest()
    except Exception as e:
        logger.warning(f"Failed to generate cache key: {e}")
        # Fallback to string representation
        return hashlib.sha256(str((args, kwargs)).encode("utf-8")).hexdigest()


def cached_query(cache: TTLCache, key_func: Callable | None = None):
    """Decorator to cache query results.

    Args:
        cache: The TTL cache to use
        key_func: Optional custom key generation function

    Returns:
        Decorated function with caching

    Example:
        @cached_query(product_cache)
        def get_products_by_barcode(barcode: str, db: Session):
            return db.query(HairProductModel).filter(...).all()

    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = generate_cache_key(*args, **kwargs)

            # Check cache
            if cache_key in cache:
                logger.debug(f"Cache HIT for {func.__name__} (key={cache_key[:8]}...)")
                return cache[cache_key]

            # Cache miss - execute function
            logger.debug(f"Cache MISS for {func.__name__} (key={cache_key[:8]}...)")
            result = func(*args, **kwargs)

            # Store in cache
            cache[cache_key] = result

            return result

        return wrapper

    return decorator


def get_cache_stats(cache: TTLCache) -> dict:
    """Get statistics about a cache.

    Args:
        cache: The TTL cache to inspect

    Returns:
        Dict with cache statistics

    """
    return {
        "size": len(cache),
        "maxsize": cache.maxsize,
        "ttl": cache.ttl,
        "utilization": f"{(len(cache) / cache.maxsize) * 100:.1f}%",
    }


def clear_cache(cache: TTLCache) -> None:
    """Clear all entries from a cache.

    Args:
        cache: The TTL cache to clear

    """
    cache.clear()
    logger.info(f"Cache cleared ({cache.maxsize} max, {cache.ttl}s TTL)")


def clear_all_caches() -> None:
    """Clear all application caches."""
    for cache_name, cache in [
        ("recall", recall_cache),
        ("safety", safety_cache),
        ("user", user_cache),
        ("agency", agency_cache),
    ]:
        cache.clear()
        logger.info(f"{cache_name} cache cleared")


# Convenience functions for common queries


def cache_recall_query(func: Callable) -> Callable:
    """Decorator for caching recall queries (5 min TTL)."""
    return cached_query(recall_cache)(func)


def cache_safety_query(func: Callable) -> Callable:
    """Decorator for caching safety check queries (10 min TTL)."""
    return cached_query(safety_cache)(func)


def cache_user_query(func: Callable) -> Callable:
    """Decorator for caching user queries (2 min TTL)."""
    return cached_query(user_cache)(func)


def cache_agency_query(func: Callable) -> Callable:
    """Decorator for caching agency data queries (1 hour TTL)."""
    return cached_query(agency_cache)(func)


# Example usage functions


@cache_recall_query
def get_recalls_by_barcode_cached(barcode: str, db):
    """REMOVED FOR CROWN SAFE: Recall functionality no longer applicable.
    This function is deprecated and returns empty list.
    """
    # from core_infra.database import RecallDB
    # return db.query(RecallDB).filter(RecallDB.upc == barcode).all()
    return []


@cache_safety_query
def get_product_safety_score_cached(product_id: int, db) -> None:
    """Get product safety score with caching.

    Example of how to cache expensive safety calculations.
    """
    # Your actual safety score calculation here


# Health check endpoint helper


def get_all_cache_stats() -> dict:
    """Get statistics for all caches.

    Returns:
        Dict with stats for each cache

    """
    return {
        "recall_cache": get_cache_stats(recall_cache),
        "safety_cache": get_cache_stats(safety_cache),
        "user_cache": get_cache_stats(user_cache),
        "agency_cache": get_cache_stats(agency_cache),
    }

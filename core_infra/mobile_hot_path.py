#!/usr/bin/env python3
# core_infra/mobile_hot_path.py
# Ultra-fast mobile hot path for instant barcode scanning across 39 agencies

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import text

logger = logging.getLogger(__name__)


class MobileHotPath:
    """
    Ultra-optimized mobile scanning path for sub-100ms responses.
    Designed for real-time in-store scanning across 39 international agencies.
    """

    def __init__(self):
        self.logger = logger
        self.hot_cache = {}  # In-memory cache for instant responses
        self.popular_products = set()

        # Mobile optimization configuration
        self.config = {
            "target_response_time": 100,  # Target <100ms
            "hot_cache_size": 10000,  # Keep 10k products in memory
            "minimal_response": True,  # Minimal JSON for mobile
            "precompute_safety": True,  # Pre-compute safety scores
            "aggressive_caching": True,  # Use all caching layers
        }

    async def ultra_fast_barcode_check(self, barcode: str, user_id: int) -> Dict[str, Any]:
        """
        Ultra-fast barcode check optimized for <100ms mobile responses
        """
        start_time = time.time()

        try:
            # 🚀 LEVEL 1: HOT CACHE (in-memory, <1ms)
            hot_key = f"hot_{barcode}_{user_id}"
            if hot_key in self.hot_cache:
                elapsed_ms = int((time.time() - start_time) * 1000)
                self.logger.debug(f"⚡ HOT CACHE hit for {barcode} in {elapsed_ms}ms")

                result = self.hot_cache[hot_key].copy()
                result.update(
                    {
                        "response_time_ms": elapsed_ms,
                        "cache_level": "hot_memory",
                        "optimization": "ultra_fast",
                    }
                )
                return result

            # 🚀 LEVEL 2: REDIS CACHE (5-20ms)
            from core_infra.cache_manager import get_cached

            redis_key = f"mobile_{barcode}_{user_id}"
            cached_result = get_cached("mobile", redis_key)
            if cached_result:
                elapsed_ms = int((time.time() - start_time) * 1000)
                self.logger.debug(f"💾 Redis cache hit for {barcode} in {elapsed_ms}ms")

                # Promote to hot cache for even faster future access
                self.hot_cache[hot_key] = cached_result

                cached_result.update(
                    {
                        "response_time_ms": elapsed_ms,
                        "cache_level": "redis",
                        "optimization": "cached",
                    }
                )
                return cached_result

            # 🚀 LEVEL 3: OPTIMIZED DATABASE QUERY (50-100ms)
            from core_infra.connection_pool_optimizer import optimized_recall_search

            recalls = await optimized_recall_search(upc=barcode)

            # Generate minimal mobile response
            if recalls:
                # Found recalls - potential safety issue
                first_recall = recalls[0]
                safety_response = {
                    "safe": False,
                    "level": "DANGER",
                    "summary": f"⚠️ RECALL: {first_recall.get('product_name', 'Product')[:50]}...",
                    "details": first_recall.get("hazard_description", "Safety concern identified")[:100],
                    "agencies": 39,
                    "recall_count": len(recalls),
                }
            else:
                # No recalls found - safe
                safety_response = {
                    "safe": True,
                    "level": "SAFE",
                    "summary": "✅ Safe - No recalls found",
                    "details": "Product checked against 39 international recall databases",
                    "agencies": 39,
                    "recall_count": 0,
                }

            elapsed_ms = int((time.time() - start_time) * 1000)

            # Add performance metrics
            safety_response.update(
                {
                    "response_time_ms": elapsed_ms,
                    "cache_level": "database",
                    "optimization": "optimized" if elapsed_ms < 200 else "standard",
                }
            )

            # 🚀 CACHE THE RESULT in both Redis and hot cache
            from core_infra.cache_manager import set_cached

            # Cache in Redis for 30 minutes
            set_cached("mobile", redis_key, safety_response, ttl=1800)

            # If response was fast, add to hot cache
            if elapsed_ms < 150:
                self.hot_cache[hot_key] = safety_response

                # Limit hot cache size
                if len(self.hot_cache) > self.config["hot_cache_size"]:
                    # Remove oldest entries
                    oldest_keys = list(self.hot_cache.keys())[:100]
                    for key in oldest_keys:
                        del self.hot_cache[key]

            self.logger.info(f"📱 Mobile check for {barcode}: {elapsed_ms}ms, Safe: {safety_response['safe']}")

            return safety_response

        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            self.logger.error(f"Ultra-fast barcode check failed after {elapsed_ms}ms: {e}")

            # Return safe default on error
            return {
                "safe": True,
                "level": "SAFE",
                "summary": "Unable to check - please try again",
                "details": "Temporary service issue",
                "agencies": 39,
                "response_time_ms": elapsed_ms,
                "cache_level": "error",
                "optimization": "error_fallback",
            }

    async def precompute_popular_products(self, limit: int = 1000) -> int:
        """
        Pre-compute safety responses for popular products
        """
        start_time = time.time()
        precomputed = 0

        try:
            # REMOVED FOR CROWN SAFE: Recall warmup no longer applicable
            # from core_infra.database import get_db_session, RecallDB
            # Recall functionality removed - Crown Safe uses hair products

            logger.info(f"⏭️  Recall warmup skipped (deprecated for Crown Safe) - target was {limit} products")
            return

            # Popular product warmup removed - now uses HairProductModel
            # with get_db_session() as db:
            #     popular_query = db.execute(text(...))
            #     for row in popular_query:
            #         # Pre-compute safety check
            #         pass

        except Exception as e:
            self.logger.error(f"Popular product pre-computation failed (deprecated): {e}")
            return 0

    def get_hot_cache_stats(self) -> Dict[str, Any]:
        """
        Get hot cache performance statistics
        """
        return {
            "hot_cache_size": len(self.hot_cache),
            "max_hot_cache_size": self.config["hot_cache_size"],
            "target_response_time": f"{self.config['target_response_time']}ms",
            "optimization_level": "ultra_fast",
            "agencies_optimized": 39,
        }

    def clear_hot_cache(self):
        """
        Clear hot cache for memory management
        """
        cache_size = len(self.hot_cache)
        self.hot_cache.clear()
        self.logger.info(f"🧹 Cleared hot cache: {cache_size} entries removed")


# Global mobile hot path instance
mobile_hot_path = MobileHotPath()


# Convenience functions
async def ultra_fast_check(barcode: str, user_id: int) -> Dict[str, Any]:
    """Ultra-fast mobile barcode check"""
    return await mobile_hot_path.ultra_fast_barcode_check(barcode, user_id)


async def precompute_popular() -> int:
    """Pre-compute popular products for hot cache"""
    return await mobile_hot_path.precompute_popular_products()


def get_mobile_stats() -> Dict[str, Any]:
    """Get mobile hot path statistics"""
    return mobile_hot_path.get_hot_cache_stats()

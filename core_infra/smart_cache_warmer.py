#!/usr/bin/env python3
# core_infra/smart_cache_warmer.py
# Smart cache warming system for 39-agency BabyShield performance optimization

import asyncio
import logging
import threading
import time
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class SmartCacheWarmer:
    """Intelligent cache warming system for BabyShield's 39-agency recall database.
    Pre-loads popular products and anticipates user queries for maximum cache hit rates.
    """

    def __init__(self) -> None:
        self.logger = logger
        self.warming_active = False
        self.last_warming = None
        self.popular_products = []
        self.popular_brands = []
        self.warming_lock = threading.Lock()

        # Cache warming configuration
        self.config = {
            "warm_top_products": 1000,  # Pre-cache top 1000 products
            "warm_top_brands": 200,  # Pre-cache top 200 brands
            "warming_interval": 1800,  # Re-warm every 30 minutes
            "concurrent_warming": 20,  # Parallel warming operations
            "popular_threshold": 2,  # Minimum mentions to be "popular"
        }

    async def analyze_popular_products(self) -> dict[str, list[str]]:
        """Analyze 3,218+ recalls to identify most popular products and brands for cache warming
        """
        start_time = time.time()

        try:
            # REMOVED FOR CROWN SAFE: Recall analytics no longer applicable
            # from core_infra.database import get_db_session, RecallDB
            # Recall functionality removed - Crown Safe uses hair products

            logger.info("⏭️  Recall analytics cache warming skipped (deprecated for Crown Safe)")

            # Return empty results for backward compatibility
            elapsed = time.time() - start_time
            return {
                "popular_products": [],
                "popular_brands": [],
                "total_analyzed": 0,
                "elapsed_time": elapsed,
            }

            # Original recall analytics removed:
            # with get_db_session() as db:
            #     products_query = db.execute(text(...))
            #     for row in products_query:
            #         # Analyze products and brands
            #         pass

        except Exception as e:
            self.logger.error(f"Popular product analysis failed: {e}")
            return {"products": [], "brands": []}

    async def warm_cache_for_products(self, products: list[str]) -> int:
        """Pre-warm cache for popular products with optimized batch operations
        """
        start_time = time.time()
        successful_warming = 0

        try:
            from core_infra.cache_manager import set_cached
            from core_infra.connection_pool_optimizer import optimized_recall_search

            # Batch products into groups for parallel processing
            batch_size = self.config["concurrent_warming"]
            product_batches = [products[i : i + batch_size] for i in range(0, len(products), batch_size)]

            for batch in product_batches:
                # Process batch in parallel
                async def warm_product(product_name) -> bool:
                    try:
                        # Get recall data for this product
                        recalls = await optimized_recall_search(product_name=product_name)

                        if recalls:
                            # Cache the search result
                            cache_key = f"product_search_{product_name.lower()}"
                            cache_data = {
                                "status": "COMPLETED",
                                "data": {"recalls": recalls},
                                "agencies_checked": 39,
                                "cached_at": datetime.now().isoformat(),
                            }

                            set_cached("recall", cache_key, cache_data, ttl=7200)  # 2 hour cache
                            return True
                    except Exception as e:
                        self.logger.warning(f"Cache warming failed for {product_name}: {e}")
                        return False
                    return False

                # Execute batch in parallel
                batch_tasks = [warm_product(product) for product in batch]
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

                # Count successful warming operations
                successful_warming += sum(1 for result in batch_results if result is True)

                # Small delay between batches to avoid overwhelming the system
                await asyncio.sleep(0.1)

            elapsed = time.time() - start_time
            self.logger.info(
                f"🔥 Cache warming: {successful_warming}/{len(products)} products warmed in {elapsed:.3f}s",
            )

            return successful_warming

        except Exception as e:
            self.logger.error(f"Cache warming failed: {e}")
            return 0

    async def warm_cache_for_autocomplete(self, products: list[str], brands: list[str]) -> int:
        """Pre-warm autocomplete cache for instant typing responses
        """
        try:
            # Pre-generate common autocomplete queries
            common_queries = []

            # Generate 2-4 character prefixes for products
            for product in products[:200]:  # Top 200 products
                words = product.split()[:3]  # First 3 words
                for word in words:
                    if len(word) >= 2:
                        for i in range(2, min(len(word) + 1, 6)):  # 2-5 character prefixes
                            prefix = word[:i].lower()
                            if prefix not in common_queries:
                                common_queries.append(prefix)

            # Generate brand prefixes
            for brand in brands[:50]:  # Top 50 brands
                if len(brand) >= 2:
                    for i in range(2, min(len(brand) + 1, 6)):
                        prefix = brand[:i].lower()
                        if prefix not in common_queries:
                            common_queries.append(prefix)

            # Warm autocomplete cache
            # REMOVED FOR CROWN SAFE: RecallDB autocomplete no longer applicable
            # from core_infra.database import get_db_session, RecallDB
            # Recall functionality removed - Crown Safe uses hair products

            logger.info("⏭️  Autocomplete cache warming skipped (deprecated for Crown Safe)")

            # Return 0 for backward compatibility
            return 0

            # Original autocomplete warming removed:
            # with get_db_session() as db:
            #     for query in common_queries[:500]:
            #         suggestions = db.query(RecallDB.product_name).filter(...).all()
            #         set_cached("autocomplete", cache_key, suggestion_list, ttl=3600)
            #         successful_warming += 1

        except Exception as e:
            self.logger.error(f"Autocomplete cache warming failed: {e}")
            return 0

    async def start_intelligent_cache_warming(self) -> dict[str, Any]:
        """Start intelligent cache warming process for maximum performance
        """
        if self.warming_active:
            self.logger.info("Cache warming already in progress...")
            return {"status": "already_running"}

        with self.warming_lock:
            self.warming_active = True

        start_time = time.time()
        self.logger.info("🚀 Starting intelligent cache warming for 39-agency system...")

        try:
            # Step 1: Analyze popular products and brands
            popular_data = await self.analyze_popular_products()

            # Step 2: Warm cache for popular products
            product_warming = await self.warm_cache_for_products(popular_data["products"])

            # Step 3: Warm autocomplete cache
            autocomplete_warming = await self.warm_cache_for_autocomplete(
                popular_data["products"], popular_data["brands"],
            )

            # Update tracking
            self.popular_products = popular_data["products"]
            self.popular_brands = popular_data["brands"]
            self.last_warming = datetime.now()

            elapsed = time.time() - start_time

            result = {
                "status": "completed",
                "total_time_seconds": round(elapsed, 2),
                "products_warmed": product_warming,
                "autocomplete_queries_warmed": autocomplete_warming,
                "popular_products_identified": len(popular_data["products"]),
                "popular_brands_identified": len(popular_data["brands"]),
                "expected_cache_hit_improvement": "60-70%",
                "agencies_optimized": 39,
            }

            self.logger.info(
                f"✅ Cache warming complete: {product_warming} products + {autocomplete_warming} autocomplete queries in {elapsed:.3f}s",  # noqa: E501
            )

            return result

        except Exception as e:
            self.logger.error(f"Intelligent cache warming failed: {e}")
            return {"status": "failed", "error": str(e)}

        finally:
            with self.warming_lock:
                self.warming_active = False

    def should_refresh_cache(self) -> bool:
        """Determine if cache should be refreshed based on time and usage patterns
        """
        if not self.last_warming:
            return True

        elapsed = (datetime.now() - self.last_warming).total_seconds()
        return elapsed > self.config["warming_interval"]

    async def background_cache_refresh(self) -> None:
        """Background task for continuous cache optimization
        """
        while True:
            try:
                if self.should_refresh_cache():
                    self.logger.info("🔄 Starting background cache refresh...")
                    await self.start_intelligent_cache_warming()

                # Wait before next check
                await asyncio.sleep(300)  # Check every 5 minutes

            except Exception as e:
                self.logger.error(f"Background cache refresh failed: {e}")
                await asyncio.sleep(600)  # Wait longer on error


# Global cache warmer instance
cache_warmer = SmartCacheWarmer()


# Convenience functions
async def warm_cache_now():
    """Start intelligent cache warming immediately"""
    return await cache_warmer.start_intelligent_cache_warming()


async def start_background_cache_warming():
    """Start background cache warming task"""
    return asyncio.create_task(cache_warmer.background_cache_refresh())

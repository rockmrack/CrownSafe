#!/usr/bin/env python3
# core_infra/memory_optimizer.py
# Memory optimization for 39-agency BabyShield system

import asyncio
import gc
import logging
import threading
import time
from typing import Dict, Any, Optional
from weakref import WeakValueDictionary
import psutil
import os

logger = logging.getLogger(__name__)

class MemoryOptimizer:
    """
    Memory optimization for BabyShield's 39-agency system.
    Manages memory usage, object pooling, and garbage collection.
    """
    
    def __init__(self):
        self.logger = logger
        self.object_pool = WeakValueDictionary()
        self.memory_stats = {}
        self.gc_threshold = 100 * 1024 * 1024  # 100MB threshold for GC
        self.last_gc = time.time()
        
    def get_memory_usage(self) -> Dict[str, Any]:
        """
        Get current memory usage statistics
        """
        try:
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            
            return {
                "rss_mb": round(memory_info.rss / 1024 / 1024, 2),
                "vms_mb": round(memory_info.vms / 1024 / 1024, 2),
                "memory_percent": round(process.memory_percent(), 2),
                "object_pool_size": len(self.object_pool),
                "gc_count": {
                    "gen0": gc.get_count()[0],
                    "gen1": gc.get_count()[1], 
                    "gen2": gc.get_count()[2]
                }
            }
        except Exception as e:
            self.logger.warning(f"Memory usage check failed: {e}")
            return {"error": str(e)}
    
    def optimize_memory_usage(self) -> Dict[str, Any]:
        """
        Perform memory optimization including garbage collection
        """
        start_time = time.time()
        before_stats = self.get_memory_usage()
        
        try:
            # Force garbage collection
            collected = gc.collect()
            
            # Clear object pool of stale references
            pool_size_before = len(self.object_pool)
            # WeakValueDictionary automatically cleans up dead references
            
            # Update last GC time
            self.last_gc = time.time()
            
            after_stats = self.get_memory_usage()
            elapsed = time.time() - start_time
            
            memory_freed = before_stats.get("rss_mb", 0) - after_stats.get("rss_mb", 0)
            
            result = {
                "optimization_completed": True,
                "time_seconds": round(elapsed, 3),
                "objects_collected": collected,
                "memory_freed_mb": round(memory_freed, 2),
                "before": before_stats,
                "after": after_stats,
                "object_pool_cleaned": pool_size_before - len(self.object_pool)
            }
            
            self.logger.info(f"🧹 Memory optimization: {memory_freed:.2f}MB freed, {collected} objects collected")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Memory optimization failed: {e}")
            return {"error": str(e)}
    
    def should_optimize_memory(self) -> bool:
        """
        Determine if memory optimization should be triggered
        """
        try:
            # Check if it's been more than 10 minutes since last GC
            if time.time() - self.last_gc > 600:
                return True
            
            # Check memory usage
            memory_stats = self.get_memory_usage()
            rss_mb = memory_stats.get("rss_mb", 0)
            
            # Trigger if using more than 500MB
            if rss_mb > 500:
                return True
                
            return False
            
        except Exception:
            return False
    
    async def background_memory_optimization(self):
        """
        Background task for continuous memory optimization
        """
        while True:
            try:
                if self.should_optimize_memory():
                    self.logger.info("🧹 Starting background memory optimization...")
                    self.optimize_memory_usage()
                
                # Wait 5 minutes between checks
                await asyncio.sleep(300)
                
            except Exception as e:
                self.logger.error(f"Background memory optimization failed: {e}")
                await asyncio.sleep(600)  # Wait longer on error

# Global memory optimizer
memory_optimizer = MemoryOptimizer()

def get_memory_stats():
    """Get current memory statistics"""
    return memory_optimizer.get_memory_usage()

def optimize_memory():
    """Trigger memory optimization"""
    return memory_optimizer.optimize_memory_usage()

async def start_memory_monitoring():
    """Start background memory monitoring"""
    return asyncio.create_task(memory_optimizer.background_memory_optimization())
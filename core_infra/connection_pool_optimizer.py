#!/usr/bin/env python3
# core_infra/connection_pool_optimizer.py
# Advanced connection pooling and batch optimization for 39-agency BabyShield system

import asyncio
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from typing import Any, Callable, Dict, List, Optional, Union

from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)


class ConnectionPoolOptimizer:
    """
    High-performance connection pool optimizer for BabyShield's 39-agency database operations.
    Implements connection pooling, batch operations, and query optimization.
    """

    def __init__(self, max_workers: int = 20):
        self.max_workers = max_workers
        self.thread_pool = ThreadPoolExecutor(max_workers=max_workers)
        self.agent_instance_pool = {}
        self.session_pool = {}
        self.pool_lock = threading.Lock()
        self.query_batch = []
        self.batch_size = 10

        self.logger = logger

    @asynccontextmanager
    async def get_optimized_db_session(self):
        """
        Get an optimized database session with connection pooling
        """
        from core_infra.database import SessionLocal

        thread_id = threading.get_ident()

        with self.pool_lock:
            if thread_id not in self.session_pool:
                self.session_pool[thread_id] = SessionLocal()
                self.logger.debug(f"Created new DB session for thread {thread_id}")

        session = self.session_pool[thread_id]

        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            self.logger.error(f"Database session error: {e}")
            raise
        finally:
            # Keep session open for reuse instead of closing
            pass

    async def batch_database_operations(self, operations: List[Callable]) -> List[Any]:
        """
        Execute multiple database operations in a single optimized batch
        """
        start_time = time.time()

        try:
            from core_infra.database import get_db_session

            results = []

            # Group operations by type for maximum efficiency
            with get_db_session() as db:
                for operation in operations:
                    try:
                        result = operation(db)
                        results.append(result)
                    except Exception as e:
                        self.logger.warning(f"Batch operation failed: {e}")
                        results.append(None)

                # Single commit for all operations
                db.commit()

            elapsed = time.time() - start_time
            self.logger.info(f"🚀 Batch operations completed: {len(results)} ops in {elapsed:.3f}s")

            return results

        except Exception as e:
            self.logger.error(f"Batch database operations failed: {e}")
            return []

    async def optimized_recall_search(
        self,
        upc: Optional[str] = None,
        model_number: Optional[str] = None,
        product_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Ultra-optimized recall search with intelligent query strategy
        """
        # REMOVED FOR CROWN SAFE: Recall search no longer applicable
        # Return empty list for backward compatibility
        start_time = time.time()

        try:
            # from core_infra.database import get_db_session, RecallDB
            # Recall search functionality removed - Crown Safe uses hair products

            elapsed = time.time() - start_time
            if self.logger.isEnabledFor(logging.DEBUG):
                self.logger.debug(f"🔍 Recall search skipped (deprecated) in {elapsed:.3f}s")
            return []

        except Exception as e:
            elapsed = time.time() - start_time
            self.logger.error(f"Recall search (deprecated) failed after {elapsed:.3f}s: {e}")
            return []

    def get_pooled_agent_instance(self, agent_class, agent_id: str):
        """
        Get a pooled agent instance to avoid re-instantiation overhead
        """
        pool_key = f"{agent_class.__name__}_{agent_id}"

        with self.pool_lock:
            if pool_key not in self.agent_instance_pool:
                self.agent_instance_pool[pool_key] = agent_class(agent_id, self.logger)
                self.logger.debug(f"Created pooled agent instance: {pool_key}")

        return self.agent_instance_pool[pool_key]

    async def parallel_agent_execution(self, agent_tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Execute multiple agent tasks in parallel for massive speedup
        """
        start_time = time.time()

        try:
            # Create async tasks for parallel execution
            async def execute_agent_task(task_info):
                try:
                    agent_instance = self.get_pooled_agent_instance(task_info["agent_class"], task_info["agent_id"])

                    # Execute the agent task
                    if hasattr(agent_instance, "process_task"):
                        if asyncio.iscoroutinefunction(agent_instance.process_task):
                            result = await agent_instance.process_task(task_info["inputs"])
                        else:
                            result = agent_instance.process_task(task_info["inputs"])
                    else:
                        result = {
                            "status": "FAILED",
                            "error": "Agent has no process_task method",
                        }

                    return {
                        "agent_name": task_info["agent_name"],
                        "result": result,
                        "execution_time": time.time() - start_time,
                    }

                except Exception as e:
                    return {
                        "agent_name": task_info.get("agent_name", "unknown"),
                        "result": {"status": "FAILED", "error": str(e)},
                        "execution_time": time.time() - start_time,
                    }

            # Execute all tasks in parallel
            tasks = [execute_agent_task(task_info) for task_info in agent_tasks]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            elapsed = time.time() - start_time
            successful = len(
                [
                    r
                    for r in results
                    if not isinstance(r, Exception) and r.get("result", {}).get("status") == "COMPLETED"
                ]
            )

            self.logger.info(
                f"🚀 Parallel agent execution: {successful}/{len(agent_tasks)} successful in {elapsed:.3f}s"
            )

            return [r for r in results if not isinstance(r, Exception)]

        except Exception as e:
            elapsed = time.time() - start_time
            self.logger.error(f"Parallel agent execution failed after {elapsed:.3f}s: {e}")
            return []

    def cleanup_connections(self):
        """
        Clean up connection pools and agent instances
        """
        try:
            with self.pool_lock:
                # Close database sessions
                for session in self.session_pool.values():
                    try:
                        session.close()
                    except:
                        pass

                self.session_pool.clear()
                self.agent_instance_pool.clear()

            # Shutdown thread pool
            self.thread_pool.shutdown(wait=True)

            self.logger.info("🧹 Connection pools cleaned up successfully")

        except Exception as e:
            self.logger.error(f"Connection cleanup failed: {e}")


# Global connection pool optimizer
connection_optimizer = ConnectionPoolOptimizer()


# Convenience functions
async def optimized_recall_search(upc=None, model_number=None, product_name=None):
    """Optimized recall search with connection pooling"""
    return await connection_optimizer.optimized_recall_search(upc, model_number, product_name)


async def batch_db_operations(operations):
    """Execute database operations in optimized batch"""
    return await connection_optimizer.batch_database_operations(operations)


async def parallel_agents(agent_tasks):
    """Execute agent tasks in parallel"""
    return await connection_optimizer.parallel_agent_execution(agent_tasks)

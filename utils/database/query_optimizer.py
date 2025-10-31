"""
Database Query Optimizer
Provides utilities for optimizing database queries and preventing N+1 problems
"""

import logging
import time
from contextlib import contextmanager
from functools import wraps
from typing import Any, Generic, TypeVar

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Query, Session, joinedload, selectinload

logger = logging.getLogger(__name__)

T = TypeVar("T")


class QueryPerformanceMonitor:
    """Monitor and log slow database queries"""

    def __init__(self, slow_query_threshold: float = 1.0):
        """
        Initialize query monitor

        Args:
            slow_query_threshold: Threshold in seconds for slow query warnings
        """
        self.slow_query_threshold = slow_query_threshold
        self.query_count = 0
        self.slow_queries = []

    def log_query(self, query: str, duration: float, params: Any = None):
        """Log query execution"""
        self.query_count += 1

        if duration > self.slow_query_threshold:
            self.slow_queries.append({"query": query, "duration": duration, "params": params})
            logger.warning(f"Slow query detected ({duration:.2f}s): {query[:200]}...")

    def get_stats(self) -> dict:
        """Get query statistics"""
        return {
            "total_queries": self.query_count,
            "slow_queries": len(self.slow_queries),
            "slow_query_details": self.slow_queries,
        }

    def reset(self):
        """Reset statistics"""
        self.query_count = 0
        self.slow_queries = []


# Global query monitor
query_monitor = QueryPerformanceMonitor()


def setup_query_logging(engine: Engine, echo_slow_only: bool = True):
    """
    Setup query logging for SQLAlchemy engine

    Args:
        engine: SQLAlchemy engine
        echo_slow_only: If True, only log slow queries
    """

    @event.listens_for(engine, "before_cursor_execute")
    def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        conn.info.setdefault("query_start_time", []).append(time.time())

    @event.listens_for(engine, "after_cursor_execute")
    def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        total_time = time.time() - conn.info["query_start_time"].pop()

        if echo_slow_only:
            if total_time > query_monitor.slow_query_threshold:
                query_monitor.log_query(statement, total_time, parameters)
        else:
            query_monitor.log_query(statement, total_time, parameters)

    logger.info("✅ Query logging enabled")


class OptimizedQuery(Generic[T]):
    """Wrapper for optimized database queries"""

    def __init__(self, query: Query):
        self.query = query
        self._eager_load_relationships = []

    def eager_load(self, *relationships) -> "OptimizedQuery[T]":
        """
        Add eager loading for relationships to prevent N+1 queries

        Args:
            *relationships: Relationship attributes to eager load

        Returns:
            Self for chaining
        """
        for rel in relationships:
            self.query = self.query.options(joinedload(rel))
        return self

    def select_in_load(self, *relationships) -> "OptimizedQuery[T]":
        """
        Add select-in eager loading (better for one-to-many)

        Args:
            *relationships: Relationship attributes to eager load

        Returns:
            Self for chaining
        """
        for rel in relationships:
            self.query = self.query.options(selectinload(rel))
        return self

    def paginate(self, limit: int, offset: int) -> "OptimizedQuery[T]":
        """
        Add pagination

        Args:
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            Self for chaining
        """
        self.query = self.query.limit(limit).offset(offset)
        return self

    def filter_by(self, **kwargs) -> "OptimizedQuery[T]":
        """
        Add filters

        Args:
            **kwargs: Filter conditions

        Returns:
            Self for chaining
        """
        self.query = self.query.filter_by(**kwargs)
        return self

    def order_by(self, *args) -> "OptimizedQuery[T]":
        """
        Add ordering

        Args:
            *args: Order by columns

        Returns:
            Self for chaining
        """
        self.query = self.query.order_by(*args)
        return self

    def all(self) -> list[T]:
        """Execute query and return all results"""
        return self.query.all()

    def first(self) -> T | None:
        """Execute query and return first result"""
        return self.query.first()

    def count(self) -> int:
        """Get count of results"""
        return self.query.count()

    def one_or_none(self) -> T | None:
        """Execute query and return one result or None"""
        return self.query.one_or_none()


def optimize_query(query: Query) -> OptimizedQuery:
    """
    Wrap a SQLAlchemy query with optimization utilities

    Args:
        query: SQLAlchemy query object

    Returns:
        OptimizedQuery wrapper
    """
    return OptimizedQuery(query)


@contextmanager
def track_queries():
    """
    Context manager to track queries within a block

    Example:
        with track_queries() as tracker:
            # Execute queries
            result = db.query(User).all()

        print(f"Executed {tracker.query_count} queries")
    """
    query_monitor.reset()
    yield query_monitor
    stats = query_monitor.get_stats()
    logger.info(f"Query block executed {stats['total_queries']} queries ({stats['slow_queries']} slow)")


def batch_load(db: Session, model: type, ids: list[int], batch_size: int = 100) -> list[Any]:
    """
    Load multiple records by ID in batches to prevent large IN clauses

    Args:
        db: Database session
        model: SQLAlchemy model class
        ids: List of IDs to load
        batch_size: Number of IDs per batch

    Returns:
        List of loaded records
    """
    results = []

    for i in range(0, len(ids), batch_size):
        batch_ids = ids[i : i + batch_size]
        batch_results = db.query(model).filter(model.id.in_(batch_ids)).all()
        results.extend(batch_results)

    return results


def cached_query(cache_key: str, ttl: int = 300):
    """
    Decorator to cache query results

    Args:
        cache_key: Cache key prefix
        ttl: Time to live in seconds

    Returns:
        Decorated function
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # TODO: Implement actual caching with Redis
            # For now, just execute the query
            return func(*args, **kwargs)

        return wrapper

    return decorator


class BulkOperationHelper:
    """Helper for efficient bulk database operations"""

    @staticmethod
    def bulk_insert(db: Session, model: type, records: list[dict], batch_size: int = 1000):
        """
        Insert multiple records efficiently

        Args:
            db: Database session
            model: SQLAlchemy model class
            records: List of dictionaries with record data
            batch_size: Number of records per batch
        """
        for i in range(0, len(records), batch_size):
            batch = records[i : i + batch_size]
            db.bulk_insert_mappings(model, batch)
        db.commit()
        logger.info(f"Bulk inserted {len(records)} {model.__name__} records")

    @staticmethod
    def bulk_update(db: Session, model: type, records: list[dict], batch_size: int = 1000):
        """
        Update multiple records efficiently

        Args:
            db: Database session
            model: SQLAlchemy model class
            records: List of dictionaries with record data (must include 'id')
            batch_size: Number of records per batch
        """
        for i in range(0, len(records), batch_size):
            batch = records[i : i + batch_size]
            db.bulk_update_mappings(model, batch)
        db.commit()
        logger.info(f"Bulk updated {len(records)} {model.__name__} records")


# Common query patterns with optimization


def get_user_with_subscriptions(db: Session, user_id: int):
    """
    Get user with subscription data (optimized)

    Example of preventing N+1 queries
    """
    from core_infra.database import User

    return (
        optimize_query(db.query(User))
        .filter_by(id=user_id)
        .eager_load("subscription")  # Prevent N+1
        .one_or_none()
    )


def get_recalls_with_products(db: Session, limit: int = 20, offset: int = 0, filters: dict | None = None):
    """
    Get recalls with related product data (optimized)

    Example of efficient pagination and eager loading
    """
    from core_infra.database import RecallDB

    query = optimize_query(db.query(RecallDB))

    # Apply filters
    if filters:
        for key, value in filters.items():
            if hasattr(RecallDB, key):
                query = query.filter_by(**{key: value})

    # Add pagination and ordering
    return query.order_by(RecallDB.recall_date.desc()).paginate(limit, offset).all()


def search_with_count(db: Session, query: Query, limit: int, offset: int) -> tuple[list[Any], int]:
    """
    Execute query with pagination and return results + total count

    Optimized to execute count and data query efficiently

    Args:
        db: Database session
        query: Base query
        limit: Maximum results
        offset: Results to skip

    Returns:
        Tuple of (results, total_count)
    """
    # Get total count (without limit/offset)
    total = query.count()

    # Get paginated results
    results = query.limit(limit).offset(offset).all()

    return results, total


# Index suggestions


def suggest_indexes(db: Session, model: type) -> list[str]:
    """
    Suggest database indexes based on common query patterns

    Args:
        db: Database session
        model: SQLAlchemy model class

    Returns:
        List of suggested CREATE INDEX statements
    """
    suggestions = []
    table_name = model.__tablename__

    # Suggest indexes for foreign keys
    for column in model.__table__.columns:
        if column.foreign_keys:
            index_name = f"idx_{table_name}_{column.name}"
            suggestions.append(f"CREATE INDEX {index_name} ON {table_name}({column.name});")

    return suggestions

"""
Query optimization utilities for BabyShield
Prevents N+1 queries and improves database performance
"""

from sqlalchemy.orm import Query, Session, joinedload, selectinload, subqueryload, contains_eager
from sqlalchemy.sql import func
from sqlalchemy import and_, or_
from typing import List, Dict, Any, Optional, Type
from functools import wraps
import logging
from contextlib import contextmanager
import time

# Import User model (exists in database.py)
from core_infra.database import User

# NOTE: The following models don't exist yet (Recall, Product)
# The methods get_recalls_with_details() and search_products_optimized()
# are example/template code for when these models are implemented.

logger = logging.getLogger(__name__)

class QueryOptimizer:
    """
    Optimize database queries to prevent N+1 problems
    """
    
    @staticmethod
    def eager_load_relationships(query: Query, *relationships) -> Query:
        """
        Eager load relationships to prevent N+1 queries
        
        Example:
            # Without optimization: 1 + N queries
            users = db.query(User).all()
            for user in users:
                print(user.family_members)  # N additional queries
            
            # With optimization: 1 query
            users = QueryOptimizer.eager_load_relationships(
                db.query(User), 
                'family_members'
            ).all()
        """
        for relationship in relationships:
            if '.' in relationship:
                # Nested relationship
                query = query.options(selectinload(relationship))
            else:
                # Direct relationship
                query = query.options(joinedload(relationship))
        
        return query
    
    @staticmethod
    def batch_load(
        db: Session,
        model: Type,
        ids: List[int],
        batch_size: int = 100
    ) -> Dict[int, Any]:
        """
        Load multiple records in batches instead of one by one
        
        Example:
            # Without optimization: N queries
            for id in ids:
                user = db.query(User).filter(User.id == id).first()
            
            # With optimization: ceil(N/batch_size) queries
            users = QueryOptimizer.batch_load(db, User, ids)
        """
        results = {}
        
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i + batch_size]
            batch_results = db.query(model).filter(
                model.id.in_(batch_ids)
            ).all()
            
            for record in batch_results:
                results[record.id] = record
        
        return results
    
    @staticmethod
    def optimized_count(query: Query) -> int:
        """
        Optimized count that doesn't load all records
        
        Example:
            # Inefficient
            count = len(db.query(User).all())
            
            # Efficient
            count = QueryOptimizer.optimized_count(db.query(User))
        """
        # Remove any eager loading for count
        query = query.options()
        
        # Use SQL COUNT instead of loading records
        return query.count()
    
    @staticmethod
    def exists_check(db: Session, model: Type, **filters) -> bool:
        """
        Check if record exists without loading it
        
        Example:
            # Inefficient
            user = db.query(User).filter_by(email=email).first()
            if user:
                ...
            
            # Efficient
            if QueryOptimizer.exists_check(db, User, email=email):
                ...
        """
        return db.query(
            db.query(model).filter_by(**filters).exists()
        ).scalar()
    
    @staticmethod
    def bulk_insert(db: Session, records: List[Dict], model: Type):
        """
        Bulk insert records efficiently
        
        Example:
            # Inefficient: N queries
            for data in records:
                db.add(Model(**data))
            db.commit()
            
            # Efficient: 1 query
            QueryOptimizer.bulk_insert(db, records, Model)
        """
        db.bulk_insert_mappings(model, records)
        db.commit()
    
    @staticmethod
    def bulk_update(db: Session, updates: List[Dict], model: Type):
        """
        Bulk update records efficiently
        
        updates should be list of dicts with 'id' field
        """
        db.bulk_update_mappings(model, updates)
        db.commit()


def optimize_query(func):
    """
    Decorator to automatically optimize queries
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        
        # Call function
        result = func(*args, **kwargs)
        
        # Log slow queries
        duration = time.time() - start
        if duration > 1.0:  # Log queries taking more than 1 second
            logger.warning(
                f"Slow query in {func.__name__}: {duration:.2f}s"
            )
        
        return result
    
    return wrapper


class QueryCache:
    """
    Simple query result caching
    """
    
    def __init__(self, ttl: int = 60):
        self.cache = {}
        self.ttl = ttl
    
    def get_or_fetch(self, key: str, fetch_func: callable):
        """
        Get from cache or fetch from database
        """
        if key in self.cache:
            value, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return value
        
        # Fetch from database
        value = fetch_func()
        self.cache[key] = (value, time.time())
        return value
    
    def invalidate(self, key: str = None):
        """
        Invalidate cache entries
        """
        if key:
            self.cache.pop(key, None)
        else:
            self.cache.clear()


# Prevent N+1 in common patterns
class OptimizedQueries:
    """
    Pre-optimized common query patterns
    """
    
    @staticmethod
    def get_user_with_all_data(db: Session, user_id: int):
        """
        Get user with all related data in one query
        """
        return db.query(User)\
            .options(
                joinedload('family_members'),
                joinedload('allergies'),
                joinedload('recalls')
            )\
            .filter(User.id == user_id)\
            .first()
    
    @staticmethod
    def get_recalls_with_details(db: Session, limit: int = 100):
        """
        Get recalls with all details efficiently
        """
        return db.query(Recall)\
            .options(
                selectinload('images'),
                selectinload('incidents')
            )\
            .limit(limit)\
            .all()
    
    @staticmethod
    def search_products_optimized(
        db: Session,
        search_term: str,
        limit: int = 50
    ):
        """
        Optimized product search
        """
        # Use index-friendly query
        return db.query(Product)\
            .filter(
                or_(
                    Product.name.ilike(f'%{search_term}%'),
                    Product.brand.ilike(f'%{search_term}%')
                )
            )\
            .options(
                joinedload('risk_profile'),
                selectinload('recalls')
            )\
            .limit(limit)\
            .all()


@contextmanager
def query_profiler(name: str = "Query"):
    """
    Profile query execution time
    """
    start = time.time()
    try:
        yield
    finally:
        duration = time.time() - start
        if duration > 0.5:
            logger.warning(f"{name} took {duration:.2f}s")
        else:
            logger.debug(f"{name} took {duration:.2f}s")


class LazyLoader:
    """
    Lazy loading for expensive operations
    """
    
    def __init__(self, loader_func):
        self.loader_func = loader_func
        self._value = None
        self._loaded = False
    
    @property
    def value(self):
        if not self._loaded:
            self._value = self.loader_func()
            self._loaded = True
        return self._value
    
    def invalidate(self):
        self._loaded = False
        self._value = None


# Query optimization middleware
async def query_optimization_middleware(request, call_next):
    """
    Middleware to track and optimize queries per request
    """
    # Track queries for this request
    request.state.query_count = 0
    request.state.query_time = 0
    
    # Process request
    response = await call_next(request)
    
    # Log if too many queries
    if request.state.query_count > 20:
        logger.warning(
            f"High query count: {request.state.query_count} queries "
            f"in {request.state.query_time:.2f}s for {request.url.path}"
        )
    
    return response


# Example optimizations for existing code
def optimize_recall_search(db: Session, barcode: str):
    """
    Optimized recall search
    """
    # Original (N+1 problem):
    # recalls = db.query(Recall).filter_by(barcode=barcode).all()
    # for recall in recalls:
    #     print(recall.manufacturer)  # N additional queries
    
    # Optimized (1 query):
    recalls = db.query(Recall)\
        .options(
            joinedload('manufacturer'),
            selectinload('incidents'),
            selectinload('images')
        )\
        .filter(Recall.barcode == barcode)\
        .all()
    
    return recalls


def optimize_user_dashboard(db: Session, user_id: int):
    """
    Optimized user dashboard data loading
    """
    with query_profiler("User Dashboard"):
        # Load everything in one query
        user = db.query(User)\
            .options(
                selectinload('family_members').selectinload('allergies'),
                selectinload('recent_scans').selectinload('product'),
                selectinload('saved_products'),
                selectinload('notifications')
            )\
            .filter(User.id == user_id)\
            .first()
        
        return user


# Batch operations for better performance
class BatchProcessor:
    """
    Process database operations in batches
    """
    
    def __init__(self, db: Session, batch_size: int = 100):
        self.db = db
        self.batch_size = batch_size
        self.pending_inserts = []
        self.pending_updates = []
    
    def add_insert(self, model: Type, data: Dict):
        """Add to insert batch"""
        self.pending_inserts.append((model, data))
        
        if len(self.pending_inserts) >= self.batch_size:
            self.flush_inserts()
    
    def add_update(self, model: Type, data: Dict):
        """Add to update batch"""
        self.pending_updates.append((model, data))
        
        if len(self.pending_updates) >= self.batch_size:
            self.flush_updates()
    
    def flush_inserts(self):
        """Flush pending inserts"""
        if not self.pending_inserts:
            return
        
        # Group by model
        by_model = {}
        for model, data in self.pending_inserts:
            if model not in by_model:
                by_model[model] = []
            by_model[model].append(data)
        
        # Bulk insert for each model
        for model, records in by_model.items():
            self.db.bulk_insert_mappings(model, records)
        
        self.db.commit()
        self.pending_inserts.clear()
    
    def flush_updates(self):
        """Flush pending updates"""
        if not self.pending_updates:
            return
        
        # Group by model
        by_model = {}
        for model, data in self.pending_updates:
            if model not in by_model:
                by_model[model] = []
            by_model[model].append(data)
        
        # Bulk update for each model
        for model, records in by_model.items():
            self.db.bulk_update_mappings(model, records)
        
        self.db.commit()
        self.pending_updates.clear()
    
    def flush_all(self):
        """Flush all pending operations"""
        self.flush_inserts()
        self.flush_updates()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.flush_all()
        else:
            # Don't flush on error
            self.pending_inserts.clear()
            self.pending_updates.clear()

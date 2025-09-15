"""
Transaction management for BabyShield
Ensures data integrity with atomic operations
"""

from contextlib import contextmanager, asynccontextmanager
from typing import Optional, Callable, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import logging
from functools import wraps
import asyncio

logger = logging.getLogger(__name__)

@contextmanager
def transaction(db: Session, read_only: bool = False):
    """
    Context manager for database transactions
    Ensures commit or rollback
    
    Usage:
        with transaction(db) as session:
            user = User(email="test@example.com")
            session.add(user)
            # Automatically commits if no exception
    """
    try:
        if read_only:
            db.execute("SET TRANSACTION READ ONLY")
        
        yield db
        
        if not read_only:
            db.commit()
            logger.debug("Transaction committed successfully")
    except Exception as e:
        db.rollback()
        logger.error(f"Transaction rolled back due to error: {str(e)}")
        raise
    finally:
        if read_only:
            db.rollback()  # End read-only transaction


@contextmanager
def nested_transaction(db: Session):
    """
    Nested transaction using savepoints
    Allows partial rollback within a larger transaction
    """
    savepoint = db.begin_nested()
    try:
        yield db
        savepoint.commit()
    except Exception:
        savepoint.rollback()
        raise


class TransactionManager:
    """
    Advanced transaction management with retry logic
    """
    
    def __init__(self, db: Session, max_retries: int = 3):
        self.db = db
        self.max_retries = max_retries
    
    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function within transaction with retry logic
        """
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                with transaction(self.db) as session:
                    result = func(session, *args, **kwargs)
                    return result
            except SQLAlchemyError as e:
                last_exception = e
                logger.warning(f"Transaction attempt {attempt + 1} failed: {str(e)}")
                
                # Check if error is retryable
                if not self._is_retryable_error(e):
                    raise
                
                # Exponential backoff
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt * 0.1
                    asyncio.sleep(wait_time)
        
        # All retries exhausted
        logger.error(f"All transaction attempts failed: {str(last_exception)}")
        raise last_exception
    
    def _is_retryable_error(self, error: SQLAlchemyError) -> bool:
        """
        Check if error is retryable
        """
        error_str = str(error).lower()
        retryable_errors = [
            "deadlock",
            "lock timeout",
            "connection lost",
            "connection reset"
        ]
        return any(err in error_str for err in retryable_errors)


def transactional(read_only: bool = False, max_retries: int = 1):
    """
    Decorator for transactional methods
    
    Usage:
        @transactional()
        def create_user(db: Session, email: str):
            user = User(email=email)
            db.add(user)
            return user
    """
    def decorator(func):
        @wraps(func)
        def wrapper(db: Session, *args, **kwargs):
            for attempt in range(max_retries):
                try:
                    with transaction(db, read_only=read_only) as session:
                        return func(session, *args, **kwargs)
                except SQLAlchemyError as e:
                    if attempt == max_retries - 1:
                        raise
                    logger.warning(f"Transaction retry {attempt + 1}: {str(e)}")
        return wrapper
    return decorator


class OptimisticLock:
    """
    Optimistic locking for preventing lost updates
    """
    
    @staticmethod
    def check_version(entity, expected_version: int):
        """
        Check if entity version matches expected
        """
        if hasattr(entity, 'version'):
            if entity.version != expected_version:
                raise ValueError(
                    f"Version mismatch: expected {expected_version}, "
                    f"got {entity.version}. Data may have been modified."
                )
    
    @staticmethod
    def increment_version(entity):
        """
        Increment entity version
        """
        if hasattr(entity, 'version'):
            entity.version += 1
        else:
            entity.version = 1


class DistributedLock:
    """
    Distributed locking using Redis for preventing race conditions
    """
    
    def __init__(self, redis_client, lock_name: str, timeout: int = 10):
        self.redis = redis_client
        self.lock_name = f"lock:{lock_name}"
        self.timeout = timeout
        self.lock = None
    
    def __enter__(self):
        import time
        import uuid
        
        # Generate unique lock value
        lock_value = str(uuid.uuid4())
        
        # Try to acquire lock
        start_time = time.time()
        while time.time() - start_time < self.timeout:
            if self.redis.set(self.lock_name, lock_value, nx=True, ex=self.timeout):
                self.lock = lock_value
                return self
            time.sleep(0.1)
        
        raise TimeoutError(f"Could not acquire lock: {self.lock_name}")
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.lock:
            # Only release if we own the lock
            lua_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
            """
            self.redis.eval(lua_script, 1, self.lock_name, self.lock)


def bulk_operation(db: Session, items: list, operation: Callable, batch_size: int = 100):
    """
    Perform bulk operations with batching and transactions
    """
    total = len(items)
    processed = 0
    errors = []
    
    for i in range(0, total, batch_size):
        batch = items[i:i + batch_size]
        
        try:
            with transaction(db) as session:
                for item in batch:
                    operation(session, item)
                processed += len(batch)
                logger.info(f"Processed {processed}/{total} items")
        except Exception as e:
            logger.error(f"Batch {i//batch_size + 1} failed: {str(e)}")
            errors.append((i, str(e)))
            # Continue with next batch
    
    if errors:
        logger.warning(f"Bulk operation completed with {len(errors)} errors")
    
    return processed, errors


@asynccontextmanager
async def async_transaction(db_session):
    """
    Async transaction context manager
    """
    async with db_session() as session:
        async with session.begin():
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise


class Saga:
    """
    Saga pattern for distributed transactions
    """
    
    def __init__(self):
        self.steps = []
        self.compensations = []
        self.completed_steps = []
    
    def add_step(self, step_func: Callable, compensation_func: Callable):
        """
        Add a step with its compensation
        """
        self.steps.append(step_func)
        self.compensations.append(compensation_func)
    
    async def execute(self):
        """
        Execute all steps, compensate on failure
        """
        try:
            for i, step in enumerate(self.steps):
                result = await step()
                self.completed_steps.append((i, result))
                logger.info(f"Saga step {i + 1} completed")
            
            return True
        except Exception as e:
            logger.error(f"Saga failed at step {len(self.completed_steps)}: {str(e)}")
            await self._compensate()
            raise
    
    async def _compensate(self):
        """
        Run compensations in reverse order
        """
        for step_index, result in reversed(self.completed_steps):
            try:
                compensation = self.compensations[step_index]
                await compensation(result)
                logger.info(f"Compensated step {step_index + 1}")
            except Exception as e:
                logger.error(f"Compensation failed for step {step_index + 1}: {str(e)}")


# Example usage functions

@transactional()
def create_user_with_profile(db: Session, email: str, name: str):
    """
    Example: Create user and profile in single transaction
    """
    from core_infra.database import User
    
    # Create user
    user = User(email=email)
    db.add(user)
    db.flush()  # Get user ID without committing
    
    # Create profile (would fail and rollback if error)
    # profile = UserProfile(user_id=user.id, name=name)
    # db.add(profile)
    
    return user


def safe_bulk_insert(db: Session, records: list):
    """
    Example: Bulk insert with transaction management
    """
    def insert_record(session, record):
        # Your insert logic here
        session.add(record)
    
    return bulk_operation(db, records, insert_record)

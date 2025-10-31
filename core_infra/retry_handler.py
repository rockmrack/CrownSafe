"""Retry and error recovery mechanisms for BabyShield
Implements exponential backoff, jitter, and intelligent retry strategies
"""

import asyncio
import logging
import random
import time
from enum import Enum
from functools import wraps
from typing import Any, Callable

logger = logging.getLogger(__name__)


class RetryStrategy(Enum):
    """Different retry strategies"""

    EXPONENTIAL_BACKOFF = "exponential"
    LINEAR_BACKOFF = "linear"
    FIXED_DELAY = "fixed"
    FIBONACCI_BACKOFF = "fibonacci"
    CUSTOM = "custom"


class RetryableError(Exception):
    """Base class for retryable errors"""

    pass


class NonRetryableError(Exception):
    """Errors that should not be retried"""

    pass


class RetryConfig:
    """Configuration for retry behavior"""

    def __init__(
        self,
        max_attempts: int = 3,
        strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: list[type[Exception]] = None,
        non_retryable_exceptions: list[type[Exception]] = None,
        on_retry: Callable = None,
        on_failure: Callable = None,
        on_success: Callable = None,
    ) -> None:
        self.max_attempts = max_attempts
        self.strategy = strategy
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions or [Exception]
        self.non_retryable_exceptions = non_retryable_exceptions or [NonRetryableError]
        self.on_retry = on_retry
        self.on_failure = on_failure
        self.on_success = on_success

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay based on strategy"""
        if self.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = self.initial_delay * (self.exponential_base ** (attempt - 1))
        elif self.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = self.initial_delay * attempt
        elif self.strategy == RetryStrategy.FIXED_DELAY:
            delay = self.initial_delay
        elif self.strategy == RetryStrategy.FIBONACCI_BACKOFF:
            delay = self._fibonacci(attempt) * self.initial_delay
        else:
            delay = self.initial_delay

        # Apply max delay cap
        delay = min(delay, self.max_delay)

        # Apply jitter
        if self.jitter:
            delay = delay * (0.5 + random.random())

        return delay

    def _fibonacci(self, n: int) -> int:
        """Calculate fibonacci number"""
        if n <= 1:
            return n
        a, b = 0, 1
        for _ in range(n - 1):
            a, b = b, a + b
        return b

    def should_retry(self, exception: Exception) -> bool:
        """Check if exception should trigger retry"""
        # Check non-retryable first
        for exc_type in self.non_retryable_exceptions:
            if isinstance(exception, exc_type):
                return False

        # Check retryable
        for exc_type in self.retryable_exceptions:
            if isinstance(exception, exc_type):
                return True

        return False


class RetryHandler:
    """Handles retry logic with various strategies"""

    def __init__(self, config: RetryConfig = None) -> None:
        self.config = config or RetryConfig()
        self.attempts = 0
        self.last_exception = None

    def retry(self, func: Callable) -> Callable:
        """Decorator for sync functions with retry"""

        @wraps(func)
        def wrapper(*args, **kwargs):
            return self._execute_with_retry(func, args, kwargs)

        return wrapper

    def async_retry(self, func: Callable) -> Callable:
        """Decorator for async functions with retry"""

        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await self._async_execute_with_retry(func, args, kwargs)

        return wrapper

    def _execute_with_retry(self, func: Callable, args, kwargs) -> Any:
        """Execute sync function with retry logic"""
        for attempt in range(1, self.config.max_attempts + 1):
            self.attempts = attempt

            try:
                # Execute function
                result = func(*args, **kwargs)

                # Success callback
                if self.config.on_success:
                    self.config.on_success(result, attempt)

                logger.debug(f"{func.__name__} succeeded on attempt {attempt}")
                return result

            except Exception as e:
                self.last_exception = e

                # Check if should retry
                if not self.config.should_retry(e):
                    logger.exception(f"{func.__name__} failed with non-retryable error: {e}")
                    raise

                if attempt == self.config.max_attempts:
                    # Final failure
                    if self.config.on_failure:
                        self.config.on_failure(e, attempt)

                    logger.exception(f"{func.__name__} failed after {attempt} attempts: {e}")
                    raise

                # Calculate delay
                delay = self.config.calculate_delay(attempt)

                # Retry callback
                if self.config.on_retry:
                    self.config.on_retry(e, attempt, delay)

                logger.warning(f"{func.__name__} failed on attempt {attempt}, retrying in {delay:.2f}s: {e}")

                # Wait before retry
                time.sleep(delay)

    async def _async_execute_with_retry(self, func: Callable, args, kwargs) -> Any:
        """Execute async function with retry logic"""
        for attempt in range(1, self.config.max_attempts + 1):
            self.attempts = attempt

            try:
                # Execute function
                result = await func(*args, **kwargs)

                # Success callback
                if self.config.on_success:
                    if asyncio.iscoroutinefunction(self.config.on_success):
                        await self.config.on_success(result, attempt)
                    else:
                        self.config.on_success(result, attempt)

                logger.debug(f"{func.__name__} succeeded on attempt {attempt}")
                return result

            except Exception as e:
                self.last_exception = e

                # Check if should retry
                if not self.config.should_retry(e):
                    logger.exception(f"{func.__name__} failed with non-retryable error: {e}")
                    raise

                if attempt == self.config.max_attempts:
                    # Final failure
                    if self.config.on_failure:
                        if asyncio.iscoroutinefunction(self.config.on_failure):
                            await self.config.on_failure(e, attempt)
                        else:
                            self.config.on_failure(e, attempt)

                    logger.exception(f"{func.__name__} failed after {attempt} attempts: {e}")
                    raise

                # Calculate delay
                delay = self.config.calculate_delay(attempt)

                # Retry callback
                if self.config.on_retry:
                    if asyncio.iscoroutinefunction(self.config.on_retry):
                        await self.config.on_retry(e, attempt, delay)
                    else:
                        self.config.on_retry(e, attempt, delay)

                logger.warning(f"{func.__name__} failed on attempt {attempt}, retrying in {delay:.2f}s: {e}")

                # Wait before retry
                await asyncio.sleep(delay)


# Convenience decorators
def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
):
    """Simple retry decorator

    Usage:
        @retry(max_attempts=3, delay=1.0, backoff=2.0)
        def flaky_function():
            ...
    """
    config = RetryConfig(
        max_attempts=max_attempts,
        initial_delay=delay,
        exponential_base=backoff,
        retryable_exceptions=list(exceptions),
    )

    handler = RetryHandler(config)

    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            return handler.async_retry(func)
        else:
            return handler.retry(func)

    return decorator


# Advanced retry patterns
class CircuitBreakerRetry:
    """Combines circuit breaker with retry logic"""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        retry_config: RetryConfig = None,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.retry_config = retry_config or RetryConfig()
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open

    def is_open(self) -> bool:
        """Check if circuit is open"""
        if self.state == "open":
            # Check if recovery timeout has passed
            if self.last_failure_time:
                elapsed = time.time() - self.last_failure_time
                if elapsed > self.recovery_timeout:
                    self.state = "half-open"
                    return False
            return True
        return False

    def record_success(self) -> None:
        """Record successful execution"""
        if self.state == "half-open":
            self.state = "closed"
        self.failure_count = 0

    def record_failure(self) -> None:
        """Record failed execution"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")

    def execute_with_circuit_breaker(self, func: Callable, *args, **kwargs):
        """Execute with circuit breaker and retry"""
        if self.is_open():
            raise Exception("Circuit breaker is open")

        try:
            handler = RetryHandler(self.retry_config)
            result = handler._execute_with_retry(func, args, kwargs)
            self.record_success()
            return result
        except Exception:
            self.record_failure()
            raise


class BulkRetry:
    """Retry logic for bulk operations"""

    def __init__(self, config: RetryConfig = None) -> None:
        self.config = config or RetryConfig()

    async def process_batch_with_retry(
        self, items: list[Any], process_func: Callable, batch_size: int = 100,
    ) -> dict[str, list]:
        """Process items in batches with retry"""
        results = {"success": [], "failed": [], "retried": []}

        for i in range(0, len(items), batch_size):
            batch = items[i : i + batch_size]

            for item in batch:
                handler = RetryHandler(self.config)

                try:
                    if asyncio.iscoroutinefunction(process_func):
                        result = await handler._async_execute_with_retry(process_func, (item,), {})
                    else:
                        result = handler._execute_with_retry(process_func, (item,), {})

                    results["success"].append((item, result))

                    if handler.attempts > 1:
                        results["retried"].append((item, handler.attempts))

                except Exception as e:
                    results["failed"].append((item, str(e)))
                    logger.exception(f"Failed to process item after retries: {e}")

        return results


# Retry with fallback
class FallbackRetry:
    """Retry with fallback options"""

    def __init__(self, primary_func: Callable, fallback_funcs: list[Callable]) -> None:
        self.primary_func = primary_func
        self.fallback_funcs = fallback_funcs

    async def execute(self, *args, **kwargs):
        """Execute with fallbacks"""
        # Try primary function
        try:
            handler = RetryHandler(RetryConfig(max_attempts=2))
            if asyncio.iscoroutinefunction(self.primary_func):
                return await handler._async_execute_with_retry(self.primary_func, args, kwargs)
            else:
                return handler._execute_with_retry(self.primary_func, args, kwargs)
        except Exception as primary_error:
            logger.warning(f"Primary function failed: {primary_error}")

            # Try fallbacks
            for fallback in self.fallback_funcs:
                try:
                    logger.info(f"Trying fallback: {fallback.__name__}")

                    if asyncio.iscoroutinefunction(fallback):
                        return await fallback(*args, **kwargs)
                    else:
                        return fallback(*args, **kwargs)

                except Exception as fallback_error:
                    logger.warning(f"Fallback {fallback.__name__} failed: {fallback_error}")

            # All fallbacks failed
            raise Exception(f"All fallbacks failed. Primary error: {primary_error}")


# Example usage
"""
# Simple retry
@retry(max_attempts=3, delay=1.0)
def unreliable_api_call():
    # This will be retried up to 3 times
    response = requests.get("https://flaky-api.com")
    return response.json()

# Custom retry configuration
config = RetryConfig(
    max_attempts=5,
    strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
    initial_delay=2.0,
    max_delay=30.0,
    retryable_exceptions=[ConnectionError, TimeoutError],
    on_retry=lambda e, attempt, delay: logger.info(f"Retry {attempt}: {e}"),
    on_failure=lambda e, attempts: logger.error(f"Failed after {attempts} attempts")
)

handler = RetryHandler(config)

@handler.async_retry
async def fetch_data():
    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.example.com") as response:
            return await response.json()
"""

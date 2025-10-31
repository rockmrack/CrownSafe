"""
Azure Blob Storage Resilience Layer
Provides retry logic, circuit breakers, and error handling for Azure storage operations
"""

import functools
import logging
import time
from datetime import datetime
from enum import Enum
from typing import Any, Callable

from azure.core.exceptions import (
    AzureError,
    HttpResponseError,
    ResourceExistsError,
    ResourceNotFoundError,
    ServiceRequestError,
    ServiceResponseError,
)

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreaker:
    """
    Circuit breaker pattern for Azure Blob Storage operations
    Prevents cascading failures by stopping requests when error rate is high
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = AzureError,
    ):
        """
        Initialize circuit breaker

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exception: Exception type to track
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time: datetime | None = None
        self.state = CircuitState.CLOSED

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection

        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            Exception: If circuit is open or function fails
        """
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker entering HALF_OPEN state - attempting recovery")
            else:
                raise Exception(
                    f"Circuit breaker is OPEN. Service unavailable. Will retry after {self.recovery_timeout} seconds."
                )

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        return (
            self.last_failure_time is not None
            and (datetime.utcnow() - self.last_failure_time).seconds >= self.recovery_timeout
        )

    def _on_success(self):
        """Handle successful operation"""
        if self.state == CircuitState.HALF_OPEN:
            logger.info("Circuit breaker recovery successful - entering CLOSED state")
        self.failure_count = 0
        self.state = CircuitState.CLOSED

    def _on_failure(self):
        """Handle failed operation"""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.error(
                f"Circuit breaker OPENED after {self.failure_count} failures. "
                f"Will attempt recovery in {self.recovery_timeout} seconds."
            )


def retry_with_exponential_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
):
    """
    Decorator for retry logic with exponential backoff

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential calculation
        jitter: Add random jitter to avoid thundering herd

    Returns:
        Decorated function with retry logic
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            import random

            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except (ServiceRequestError, ServiceResponseError, HttpResponseError) as e:
                    last_exception = e

                    if attempt == max_retries:
                        logger.error(
                            f"Failed after {max_retries} retries: {func.__name__}",
                            extra={
                                "function": func.__name__,
                                "attempt": attempt + 1,
                                "error": str(e),
                            },
                        )
                        raise

                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (exponential_base**attempt), max_delay)

                    # Add jitter to prevent thundering herd
                    if jitter:
                        delay = delay * (0.5 + random.random())

                    logger.warning(
                        f"Retry attempt {attempt + 1}/{max_retries} for {func.__name__} "
                        f"after {delay:.2f}s delay. Error: {str(e)}"
                    )
                    time.sleep(delay)
                except ResourceNotFoundError:
                    # Don't retry on 404 - resource doesn't exist
                    raise
                except ResourceExistsError:
                    # Don't retry on conflict - resource already exists
                    raise
                except Exception as e:
                    # Unexpected error - log and raise immediately
                    logger.error(
                        f"Unexpected error in {func.__name__}: {str(e)}",
                        exc_info=True,
                    )
                    raise

            # Should never reach here
            raise last_exception

        return wrapper

    return decorator


def with_correlation_id(func: Callable) -> Callable:
    """
    Decorator to add correlation ID to Azure Blob Storage operations
    Helps track requests across distributed systems

    Args:
        func: Function to decorate

    Returns:
        Decorated function with correlation ID logging
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        import uuid

        correlation_id = str(uuid.uuid4())

        # Add correlation ID to kwargs if supported
        if "metadata" in kwargs:
            kwargs["metadata"] = kwargs.get("metadata", {})
            kwargs["metadata"]["correlation_id"] = correlation_id
        elif "blob_name" in kwargs:
            # Log correlation ID for tracking
            logger.info(
                f"Azure Blob Storage operation: {func.__name__}",
                extra={
                    "correlation_id": correlation_id,
                    "function": func.__name__,
                    "blob_name": kwargs.get("blob_name"),
                },
            )

        try:
            result = func(*args, **kwargs)
            logger.debug(
                f"Operation successful: {func.__name__}",
                extra={"correlation_id": correlation_id},
            )
            return result
        except Exception as e:
            logger.error(
                f"Operation failed: {func.__name__} - {str(e)}",
                extra={
                    "correlation_id": correlation_id,
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            raise

    return wrapper


def log_azure_error(func: Callable) -> Callable:
    """
    Decorator to log Azure-specific errors with detailed context

    Args:
        func: Function to decorate

    Returns:
        Decorated function with enhanced error logging
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        try:
            return func(*args, **kwargs)
        except HttpResponseError as e:
            logger.error(
                f"Azure HTTP error in {func.__name__}",
                extra={
                    "status_code": e.status_code,
                    "error_code": e.error_code if hasattr(e, "error_code") else None,
                    "message": e.message,
                    "function": func.__name__,
                },
            )
            raise
        except ResourceNotFoundError as e:
            logger.warning(
                f"Resource not found in {func.__name__}: {str(e)}",
                extra={"function": func.__name__},
            )
            raise
        except ResourceExistsError as e:
            logger.warning(
                f"Resource already exists in {func.__name__}: {str(e)}",
                extra={"function": func.__name__},
            )
            raise
        except ServiceRequestError as e:
            logger.error(
                f"Azure service request error in {func.__name__}: {str(e)}",
                extra={"function": func.__name__},
                exc_info=True,
            )
            raise
        except AzureError as e:
            logger.error(
                f"Azure error in {func.__name__}: {str(e)}",
                extra={
                    "function": func.__name__,
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            raise

    return wrapper


# Global circuit breaker instance for Azure Blob Storage
azure_storage_circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60, expected_exception=AzureError)

"""
Circuit Breaker Pattern for BabyShield API
Prevents cascade failures and provides graceful degradation
"""

from pybreaker import CircuitBreaker, CircuitBreakerError
from typing import Callable, Any, Optional, Dict
from functools import wraps
import logging
import time
import asyncio
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
import redis

logger = logging.getLogger(__name__)

# Circuit breaker configurations for different services
BREAKER_CONFIGS = {
    "database": {
        "fail_max": 5,  # Open circuit after 5 failures
        "reset_timeout": 60,  # Try again after 60 seconds
        "exclude": [KeyError, ValueError],  # Don't count these as failures
        "name": "DatabaseBreaker",
    },
    "redis": {
        "fail_max": 10,
        "reset_timeout": 30,
        "exclude": [KeyError],
        "name": "RedisBreaker",
    },
    "external_api": {
        "fail_max": 3,
        "reset_timeout": 120,
        "exclude": [ValueError],
        "name": "ExternalAPIBreaker",
    },
    "cpsc_api": {
        "fail_max": 5,
        "reset_timeout": 300,  # 5 minutes for external APIs
        "exclude": [],
        "name": "CPSCAPIBreaker",
    },
    "google_vision": {
        "fail_max": 3,
        "reset_timeout": 180,
        "exclude": [],
        "name": "GoogleVisionBreaker",
    },
    "s3_storage": {
        "fail_max": 5,
        "reset_timeout": 60,
        "exclude": [],
        "name": "S3StorageBreaker",
    },
}

# Create circuit breakers
breakers: Dict[str, CircuitBreaker] = {}

for service, config in BREAKER_CONFIGS.items():
    breakers[service] = CircuitBreaker(
        fail_max=config["fail_max"],
        reset_timeout=config["reset_timeout"],
        exclude=config["exclude"],
        name=config["name"],
    )


# Listener functions for circuit breaker events
def breaker_opened(breaker):
    """Called when circuit breaker opens"""
    logger.error(f"Circuit breaker {breaker.name} opened! Service is failing.")


def breaker_closed(breaker):
    """Called when circuit breaker closes"""
    logger.info(f"Circuit breaker {breaker.name} closed. Service recovered.")


# Attach listeners to breakers
for breaker in breakers.values():
    breaker.add_listeners(
        {"breaker_opened": breaker_opened, "breaker_closed": breaker_closed}
    )


# Decorator for applying circuit breaker to functions
def with_circuit_breaker(service_name: str, fallback=None):
    """
    Decorator to apply circuit breaker to a function

    Args:
        service_name: Name of the service (must be in BREAKER_CONFIGS)
        fallback: Optional fallback function to call when circuit is open
    """

    def decorator(func):
        if service_name not in breakers:
            # If service not configured, return function as-is
            return func

        breaker = breakers[service_name]

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await breaker(func)(*args, **kwargs)
                else:
                    return breaker(func)(*args, **kwargs)
            except CircuitBreakerError:
                logger.warning(f"Circuit breaker {service_name} is open")
                if fallback:
                    if asyncio.iscoroutinefunction(fallback):
                        return await fallback(*args, **kwargs)
                    else:
                        return fallback(*args, **kwargs)
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return breaker(func)(*args, **kwargs)
            except CircuitBreakerError:
                logger.warning(f"Circuit breaker {service_name} is open")
                if fallback:
                    return fallback(*args, **kwargs)
                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# Specific circuit breakers for common operations
@with_circuit_breaker("database")
def database_query(query_func: Callable, *args, **kwargs):
    """Execute a database query with circuit breaker protection"""
    return query_func(*args, **kwargs)


@with_circuit_breaker("redis")
def redis_operation(operation_func: Callable, *args, **kwargs):
    """Execute a Redis operation with circuit breaker protection"""
    return operation_func(*args, **kwargs)


@with_circuit_breaker("external_api")
async def external_api_call(api_func: Callable, *args, **kwargs):
    """Make an external API call with circuit breaker protection"""
    if asyncio.iscoroutinefunction(api_func):
        return await api_func(*args, **kwargs)
    else:
        return api_func(*args, **kwargs)


# Retry decorator with exponential backoff
def with_retry(
    max_attempts: int = 3,
    wait_exponential_multiplier: int = 1,
    wait_exponential_max: int = 10,
    retry_on: tuple = (Exception,),
):
    """
    Decorator for retrying operations with exponential backoff

    Args:
        max_attempts: Maximum number of retry attempts
        wait_exponential_multiplier: Multiplier for exponential backoff
        wait_exponential_max: Maximum wait time between retries
        retry_on: Tuple of exceptions to retry on
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(
            multiplier=wait_exponential_multiplier, max=wait_exponential_max
        ),
        retry=retry_if_exception_type(retry_on),
    )


# Combined decorator for circuit breaker + retry
def resilient_operation(service_name: str, max_attempts: int = 3, fallback=None):
    """
    Combine circuit breaker with retry logic

    Args:
        service_name: Name of the service
        max_attempts: Maximum retry attempts
        fallback: Fallback function if all retries fail
    """

    def decorator(func):
        # First apply retry
        retried_func = with_retry(max_attempts=max_attempts)(func)
        # Then apply circuit breaker
        protected_func = with_circuit_breaker(service_name, fallback=fallback)(
            retried_func
        )
        return protected_func

    return decorator


# Status checking functions
def get_circuit_status(service_name: str) -> Dict[str, Any]:
    """Get the current status of a circuit breaker"""
    if service_name not in breakers:
        return {"error": f"Unknown service: {service_name}"}

    breaker = breakers[service_name]
    return {
        "service": service_name,
        "state": breaker.state.name,
        "failures": breaker.fail_counter,
        "success": breaker.success_counter,
        "fail_max": breaker.fail_max,
        "reset_timeout": breaker.reset_timeout,
        "last_failure": breaker.last_failure
        if hasattr(breaker, "last_failure")
        else None,
    }


def get_all_circuit_status() -> Dict[str, Dict[str, Any]]:
    """Get status of all circuit breakers"""
    return {service: get_circuit_status(service) for service in breakers.keys()}


def reset_circuit(service_name: str) -> bool:
    """Manually reset a circuit breaker"""
    if service_name not in breakers:
        return False

    breaker = breakers[service_name]
    breaker.close()
    return True


# Fallback functions for common operations
async def database_fallback(*args, **kwargs):
    """Fallback when database is unavailable"""
    logger.warning("Database circuit open, using fallback")
    return {
        "error": "Database temporarily unavailable",
        "fallback": True,
        "retry_after": 60,
    }


async def redis_fallback(*args, **kwargs):
    """Fallback when Redis is unavailable"""
    logger.warning("Redis circuit open, using fallback")
    # Could return cached data or proceed without cache
    return None


async def external_api_fallback(*args, **kwargs):
    """Fallback when external API is unavailable"""
    logger.warning("External API circuit open, using fallback")
    return {
        "error": "External service temporarily unavailable",
        "fallback": True,
        "retry_after": 120,
    }


# Example usage functions
@resilient_operation("database", max_attempts=3, fallback=database_fallback)
async def safe_database_query(query: str):
    """Example of a protected database query"""
    # Your database query logic here
    pass


@resilient_operation("external_api", max_attempts=2, fallback=external_api_fallback)
async def safe_api_call(url: str):
    """Example of a protected API call"""
    # Your API call logic here
    pass


# Health check for circuit breakers
def check_circuits_health() -> Dict[str, Any]:
    """Check health of all circuit breakers"""
    all_status = get_all_circuit_status()

    open_circuits = [
        service
        for service, status in all_status.items()
        if status.get("state") == "open"
    ]

    health = {
        "healthy": len(open_circuits) == 0,
        "total_circuits": len(breakers),
        "open_circuits": len(open_circuits),
        "circuits": all_status,
    }

    if open_circuits:
        health["warning"] = f"Services unavailable: {', '.join(open_circuits)}"

    return health

"""Unit tests for core_infra/retry_handler.py
Tests retry logic, strategies, circuit breaker, and bulk operations.
"""

import asyncio
import time
from typing import Never
from unittest.mock import Mock, patch

import pytest

from core_infra.retry_handler import (
    BulkRetry,
    CircuitBreakerRetry,
    FallbackRetry,
    NonRetryableError,
    RetryConfig,
    RetryHandler,
    RetryStrategy,
    retry,
)


class TestRetryStrategy:
    """Test RetryStrategy enum."""

    def test_retry_strategy_values(self) -> None:
        """Test RetryStrategy enum values."""
        assert RetryStrategy.EXPONENTIAL_BACKOFF.value == "exponential"
        assert RetryStrategy.LINEAR_BACKOFF.value == "linear"
        assert RetryStrategy.FIXED_DELAY.value == "fixed"
        assert RetryStrategy.FIBONACCI_BACKOFF.value == "fibonacci"
        assert RetryStrategy.CUSTOM.value == "custom"


class TestRetryConfig:
    """Test RetryConfig functionality."""

    def test_init_defaults(self) -> None:
        """Test RetryConfig initialization with defaults."""
        config = RetryConfig()

        assert config.max_attempts == 3
        assert config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF
        assert config.initial_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is True
        assert Exception in config.retryable_exceptions
        assert NonRetryableError in config.non_retryable_exceptions

    def test_init_custom(self) -> None:
        """Test RetryConfig initialization with custom values."""
        config = RetryConfig(
            max_attempts=5,
            strategy=RetryStrategy.LINEAR_BACKOFF,
            initial_delay=2.0,
            max_delay=30.0,
            exponential_base=3.0,
            jitter=False,
            retryable_exceptions=[ValueError],
            non_retryable_exceptions=[TypeError],
        )

        assert config.max_attempts == 5
        assert config.strategy == RetryStrategy.LINEAR_BACKOFF
        assert config.initial_delay == 2.0
        assert config.max_delay == 30.0
        assert config.exponential_base == 3.0
        assert config.jitter is False
        assert ValueError in config.retryable_exceptions
        assert TypeError in config.non_retryable_exceptions

    def test_calculate_delay_exponential(self) -> None:
        """Test exponential backoff delay calculation."""
        config = RetryConfig(
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            initial_delay=1.0,
            exponential_base=2.0,
        )

        assert config.calculate_delay(1) == 1.0
        assert config.calculate_delay(2) == 2.0
        assert config.calculate_delay(3) == 4.0
        assert config.calculate_delay(4) == 8.0

    def test_calculate_delay_linear(self) -> None:
        """Test linear backoff delay calculation."""
        config = RetryConfig(strategy=RetryStrategy.LINEAR_BACKOFF, initial_delay=1.0)

        assert config.calculate_delay(1) == 1.0
        assert config.calculate_delay(2) == 2.0
        assert config.calculate_delay(3) == 3.0
        assert config.calculate_delay(4) == 4.0

    def test_calculate_delay_fixed(self) -> None:
        """Test fixed delay calculation."""
        config = RetryConfig(strategy=RetryStrategy.FIXED_DELAY, initial_delay=2.0)

        assert config.calculate_delay(1) == 2.0
        assert config.calculate_delay(2) == 2.0
        assert config.calculate_delay(3) == 2.0

    def test_calculate_delay_fibonacci(self) -> None:
        """Test fibonacci backoff delay calculation."""
        config = RetryConfig(strategy=RetryStrategy.FIBONACCI_BACKOFF, initial_delay=1.0)

        assert config.calculate_delay(1) == 1.0
        assert config.calculate_delay(2) == 1.0
        assert config.calculate_delay(3) == 2.0
        assert config.calculate_delay(4) == 3.0
        assert config.calculate_delay(5) == 5.0

    def test_calculate_delay_max_delay(self) -> None:
        """Test max delay cap."""
        config = RetryConfig(
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            initial_delay=1.0,
            exponential_base=2.0,
            max_delay=5.0,
        )

        # Should be capped at max_delay
        delay = config.calculate_delay(10)
        assert delay <= 5.0

    def test_calculate_delay_jitter(self) -> None:
        """Test jitter application."""
        config = RetryConfig(strategy=RetryStrategy.FIXED_DELAY, initial_delay=10.0, jitter=True)

        delays = [config.calculate_delay(1) for _ in range(20)]

        # With jitter, delays should vary
        assert min(delays) < 10.0
        assert max(delays) > 10.0
        assert all(5.0 <= delay <= 15.0 for delay in delays)

    def test_calculate_delay_no_jitter(self) -> None:
        """Test no jitter."""
        config = RetryConfig(strategy=RetryStrategy.FIXED_DELAY, initial_delay=10.0, jitter=False)

        delays = [config.calculate_delay(1) for _ in range(10)]

        # Without jitter, all delays should be the same
        assert all(delay == 10.0 for delay in delays)

    def test_fibonacci_method(self) -> None:
        """Test fibonacci calculation method."""
        config = RetryConfig()

        assert config._fibonacci(0) == 0
        assert config._fibonacci(1) == 1
        assert config._fibonacci(2) == 1
        assert config._fibonacci(3) == 2
        assert config._fibonacci(4) == 3
        assert config._fibonacci(5) == 5
        assert config._fibonacci(6) == 8

    def test_should_retry_retryable_exception(self) -> None:
        """Test should_retry with retryable exception."""
        config = RetryConfig(retryable_exceptions=[ValueError])

        assert config.should_retry(ValueError("test")) is True

    def test_should_retry_non_retryable_exception(self) -> None:
        """Test should_retry with non-retryable exception."""
        config = RetryConfig(non_retryable_exceptions=[TypeError])

        assert config.should_retry(TypeError("test")) is False

    def test_should_retry_non_retryable_takes_precedence(self) -> None:
        """Test that non-retryable exceptions take precedence."""
        config = RetryConfig(retryable_exceptions=[Exception], non_retryable_exceptions=[ValueError])

        assert config.should_retry(ValueError("test")) is False

    def test_should_retry_unknown_exception(self) -> None:
        """Test should_retry with unknown exception."""
        config = RetryConfig(retryable_exceptions=[ValueError], non_retryable_exceptions=[TypeError])

        assert config.should_retry(RuntimeError("test")) is False


class TestRetryHandler:
    """Test RetryHandler functionality."""

    def test_init_default_config(self) -> None:
        """Test RetryHandler initialization with default config."""
        handler = RetryHandler()

        assert isinstance(handler.config, RetryConfig)
        assert handler.attempts == 0
        assert handler.last_exception is None

    def test_init_custom_config(self) -> None:
        """Test RetryHandler initialization with custom config."""
        config = RetryConfig(max_attempts=5)
        handler = RetryHandler(config)

        assert handler.config == config

    def test_retry_decorator_sync(self) -> None:
        """Test retry decorator for sync functions."""
        handler = RetryHandler(RetryConfig(max_attempts=2))

        @handler.retry
        def test_func() -> str:
            return "success"

        result = test_func()
        assert result == "success"
        assert handler.attempts == 1

    def test_async_retry_decorator(self) -> None:
        """Test async_retry decorator for async functions."""
        handler = RetryHandler(RetryConfig(max_attempts=2))

        @handler.async_retry
        async def test_func() -> str:
            return "success"

        result = asyncio.run(test_func())
        assert result == "success"
        assert handler.attempts == 1

    def test_execute_with_retry_success(self) -> None:
        """Test successful execution with retry."""
        handler = RetryHandler(RetryConfig(max_attempts=3))

        def test_func() -> str:
            return "success"

        result = handler._execute_with_retry(test_func, (), {})

        assert result == "success"
        assert handler.attempts == 1
        assert handler.last_exception is None

    def test_execute_with_retry_failure_then_success(self) -> None:
        """Test retry with failure then success."""
        handler = RetryHandler(RetryConfig(max_attempts=3))
        call_count = 0

        def test_func() -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("First attempt fails")
            return "success"

        with patch("time.sleep") as mock_sleep:
            result = handler._execute_with_retry(test_func, (), {})

            assert result == "success"
            assert handler.attempts == 2
            assert call_count == 2
            mock_sleep.assert_called_once()

    def test_execute_with_retry_max_attempts(self) -> None:
        """Test retry with max attempts exceeded."""
        handler = RetryHandler(RetryConfig(max_attempts=2))

        def test_func() -> Never:
            raise ValueError("Always fails")

        with patch("time.sleep") as mock_sleep:
            with pytest.raises(ValueError):
                handler._execute_with_retry(test_func, (), {})

            assert handler.attempts == 2
            assert handler.last_exception is not None
            mock_sleep.assert_called_once()

    def test_execute_with_retry_non_retryable_exception(self) -> None:
        """Test retry with non-retryable exception."""
        handler = RetryHandler(RetryConfig(max_attempts=3, non_retryable_exceptions=[TypeError]))

        def test_func() -> Never:
            raise TypeError("Non-retryable error")

        with pytest.raises(TypeError):
            handler._execute_with_retry(test_func, (), {})

        assert handler.attempts == 1
        assert handler.last_exception is not None

    def test_async_execute_with_retry_success(self) -> None:
        """Test successful async execution with retry."""
        handler = RetryHandler(RetryConfig(max_attempts=3))

        async def test_func() -> str:
            return "success"

        result = asyncio.run(handler._async_execute_with_retry(test_func, (), {}))

        assert result == "success"
        assert handler.attempts == 1

    def test_async_execute_with_retry_failure_then_success(self) -> None:
        """Test async retry with failure then success."""
        handler = RetryHandler(RetryConfig(max_attempts=3))
        call_count = 0

        async def test_func() -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("First attempt fails")
            return "success"

        with patch("asyncio.sleep") as mock_sleep:
            result = asyncio.run(handler._async_execute_with_retry(test_func, (), {}))

            assert result == "success"
            assert handler.attempts == 2
            assert call_count == 2
            mock_sleep.assert_called_once()

    def test_execute_with_callbacks(self) -> None:
        """Test execution with callbacks."""
        on_retry = Mock()
        on_failure = Mock()
        on_success = Mock()

        handler = RetryHandler(
            RetryConfig(
                max_attempts=2,
                on_retry=on_retry,
                on_failure=on_failure,
                on_success=on_success,
            ),
        )

        def test_func() -> Never:
            raise ValueError("Test error")

        with patch("time.sleep"):
            with pytest.raises(ValueError):
                handler._execute_with_retry(test_func, (), {})

            # Should call on_retry once and on_failure once
            assert on_retry.call_count == 1
            assert on_failure.call_count == 1
            assert on_success.call_count == 0


class TestRetryDecorator:
    """Test retry decorator function."""

    def test_retry_decorator_sync(self) -> None:
        """Test retry decorator with sync function."""
        call_count = 0

        @retry(max_attempts=3, delay=0.1, backoff=2.0)
        def test_func() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Not ready yet")
            return "success"

        with patch("time.sleep"):
            result = test_func()

            assert result == "success"
            assert call_count == 3

    def test_retry_decorator_async(self) -> None:
        """Test retry decorator with async function."""
        call_count = 0

        @retry(max_attempts=3, delay=0.1, backoff=2.0)
        async def test_func() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Not ready yet")
            return "success"

        with patch("asyncio.sleep"):
            result = asyncio.run(test_func())

            assert result == "success"
            assert call_count == 3

    def test_retry_decorator_specific_exceptions(self) -> None:
        """Test retry decorator with specific exceptions."""
        call_count = 0

        @retry(max_attempts=2, exceptions=(ValueError,))
        def test_func() -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("Retryable")
            return "success"

        with patch("time.sleep"):
            result = test_func()

            assert result == "success"
            assert call_count == 2


class TestCircuitBreakerRetry:
    """Test CircuitBreakerRetry functionality."""

    def test_init(self) -> None:
        """Test CircuitBreakerRetry initialization."""
        breaker = CircuitBreakerRetry(failure_threshold=3, recovery_timeout=60)

        assert breaker.failure_threshold == 3
        assert breaker.recovery_timeout == 60
        assert breaker.failure_count == 0
        assert breaker.last_failure_time is None
        assert breaker.state == "closed"

    def test_is_open_closed_state(self) -> None:
        """Test is_open with closed state."""
        breaker = CircuitBreakerRetry()

        assert breaker.is_open() is False

    def test_is_open_open_state(self) -> None:
        """Test is_open with open state."""
        breaker = CircuitBreakerRetry(failure_threshold=1, recovery_timeout=60)
        breaker.state = "open"
        breaker.last_failure_time = time.time() - 30  # 30 seconds ago

        assert breaker.is_open() is True

    def test_is_open_half_open_state(self) -> None:
        """Test is_open with half-open state."""
        breaker = CircuitBreakerRetry(failure_threshold=1, recovery_timeout=60)
        breaker.state = "half-open"

        assert breaker.is_open() is False

    def test_record_success_closed_state(self) -> None:
        """Test record_success with closed state."""
        breaker = CircuitBreakerRetry()
        breaker.failure_count = 5

        breaker.record_success()

        assert breaker.failure_count == 0
        assert breaker.state == "closed"

    def test_record_success_half_open_state(self) -> None:
        """Test record_success with half-open state."""
        breaker = CircuitBreakerRetry()
        breaker.state = "half-open"
        breaker.failure_count = 5

        breaker.record_success()

        assert breaker.failure_count == 0
        assert breaker.state == "closed"

    def test_record_failure(self) -> None:
        """Test record_failure."""
        breaker = CircuitBreakerRetry(failure_threshold=2)

        breaker.record_failure()

        assert breaker.failure_count == 1
        assert breaker.last_failure_time is not None
        assert breaker.state == "closed"

        breaker.record_failure()

        assert breaker.failure_count == 2
        assert breaker.state == "open"

    def test_execute_with_circuit_breaker_success(self) -> None:
        """Test execute_with_circuit_breaker with success."""
        breaker = CircuitBreakerRetry()

        def test_func() -> str:
            return "success"

        result = breaker.execute_with_circuit_breaker(test_func)

        assert result == "success"
        assert breaker.failure_count == 0

    def test_execute_with_circuit_breaker_failure(self) -> None:
        """Test execute_with_circuit_breaker with failure."""
        breaker = CircuitBreakerRetry(failure_threshold=1)

        def test_func() -> Never:
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            breaker.execute_with_circuit_breaker(test_func)

        assert breaker.failure_count == 1
        assert breaker.state == "open"

    def test_execute_with_circuit_breaker_open(self) -> None:
        """Test execute_with_circuit_breaker with open circuit."""
        breaker = CircuitBreakerRetry(failure_threshold=1)
        breaker.state = "open"

        def test_func() -> str:
            return "success"

        with pytest.raises(Exception, match="Circuit breaker is open"):
            breaker.execute_with_circuit_breaker(test_func)


class TestBulkRetry:
    """Test BulkRetry functionality."""

    def test_init(self) -> None:
        """Test BulkRetry initialization."""
        bulk_retry = BulkRetry()

        assert isinstance(bulk_retry.config, RetryConfig)

    def test_init_custom_config(self) -> None:
        """Test BulkRetry initialization with custom config."""
        config = RetryConfig(max_attempts=5)
        bulk_retry = BulkRetry(config)

        assert bulk_retry.config == config

    @pytest.mark.asyncio
    async def test_process_batch_with_retry_success(self) -> None:
        """Test process_batch_with_retry with success."""
        bulk_retry = BulkRetry()

        async def process_func(item):
            return item * 2

        items = [1, 2, 3]
        result = await bulk_retry.process_batch_with_retry(items, process_func, batch_size=10)

        assert len(result["success"]) == 3
        assert len(result["failed"]) == 0
        assert len(result["retried"]) == 0
        assert result["success"][0] == (1, 2)
        assert result["success"][1] == (2, 4)
        assert result["success"][2] == (3, 6)

    @pytest.mark.asyncio
    async def test_process_batch_with_retry_failure(self) -> None:
        """Test process_batch_with_retry with failure."""
        bulk_retry = BulkRetry()

        async def process_func(item):
            if item == 2:
                raise ValueError("Item 2 fails")
            return item * 2

        items = [1, 2, 3]
        result = await bulk_retry.process_batch_with_retry(items, process_func, batch_size=10)

        assert len(result["success"]) == 2
        assert len(result["failed"]) == 1
        assert len(result["retried"]) == 0
        assert result["success"][0] == (1, 2)
        assert result["success"][1] == (3, 6)
        assert result["failed"][0][0] == 2
        assert "Item 2 fails" in result["failed"][0][1]

    @pytest.mark.asyncio
    async def test_process_batch_with_retry_sync_func(self) -> None:
        """Test process_batch_with_retry with sync function."""
        bulk_retry = BulkRetry()

        def process_func(item):
            return item * 2

        items = [1, 2, 3]
        result = await bulk_retry.process_batch_with_retry(items, process_func, batch_size=10)

        assert len(result["success"]) == 3
        assert len(result["failed"]) == 0
        assert result["success"][0] == (1, 2)
        assert result["success"][1] == (2, 4)
        assert result["success"][2] == (3, 6)


class TestFallbackRetry:
    """Test FallbackRetry functionality."""

    def test_init(self) -> None:
        """Test FallbackRetry initialization."""
        primary_func = Mock()
        fallback_funcs = [Mock(), Mock()]

        fallback_retry = FallbackRetry(primary_func, fallback_funcs)

        assert fallback_retry.primary_func == primary_func
        assert fallback_retry.fallback_funcs == fallback_funcs

    @pytest.mark.asyncio
    async def test_execute_primary_success(self) -> None:
        """Test execute with primary function success."""
        primary_func = Mock(return_value="primary_success")
        fallback_funcs = [Mock(return_value="fallback_success")]

        fallback_retry = FallbackRetry(primary_func, fallback_funcs)

        result = await fallback_retry.execute("test_arg")

        assert result == "primary_success"
        primary_func.assert_called_once_with("test_arg")
        fallback_funcs[0].assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_primary_failure_fallback_success(self) -> None:
        """Test execute with primary failure and fallback success."""
        primary_func = Mock(side_effect=ValueError("Primary failed"))
        fallback_funcs = [Mock(return_value="fallback_success")]

        fallback_retry = FallbackRetry(primary_func, fallback_funcs)

        result = await fallback_retry.execute("test_arg")

        assert result == "fallback_success"
        primary_func.assert_called_once_with("test_arg")
        fallback_funcs[0].assert_called_once_with("test_arg")

    @pytest.mark.asyncio
    async def test_execute_all_failures(self) -> None:
        """Test execute with all functions failing."""
        primary_func = Mock(side_effect=ValueError("Primary failed"))
        fallback_funcs = [
            Mock(side_effect=RuntimeError("Fallback 1 failed")),
            Mock(side_effect=TypeError("Fallback 2 failed")),
        ]

        fallback_retry = FallbackRetry(primary_func, fallback_funcs)

        with pytest.raises(Exception, match="All fallbacks failed"):
            await fallback_retry.execute("test_arg")

        primary_func.assert_called_once_with("test_arg")
        fallback_funcs[0].assert_called_once_with("test_arg")
        fallback_funcs[1].assert_called_once_with("test_arg")

    @pytest.mark.asyncio
    async def test_execute_async_functions(self) -> None:
        """Test execute with async functions."""

        async def async_primary_func(arg) -> Never:
            raise ValueError("Async primary failed")

        async def async_fallback_func(arg) -> str:
            return "async_fallback_success"

        fallback_retry = FallbackRetry(async_primary_func, [async_fallback_func])

        result = await fallback_retry.execute("test_arg")

        assert result == "async_fallback_success"


if __name__ == "__main__":
    pytest.main([__file__])

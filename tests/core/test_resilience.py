import time
from unittest.mock import patch

import pytest

from core.resilience import CircuitBreaker, call_with_timeout


def test_circuit_breaker_allows_initially():
    """Test that circuit breaker allows requests initially"""
    cb = CircuitBreaker(threshold=3, window_sec=60, cooldown_sec=30)
    assert cb.allow("test_key")


def test_circuit_breaker_opens_after_failures():
    """Test that circuit breaker opens after threshold failures"""
    cb = CircuitBreaker(threshold=2, window_sec=60, cooldown_sec=30)

    # Should allow initially
    assert cb.allow("test_key")

    # Record failures
    cb.record_failure("test_key")
    assert cb.allow("test_key")  # Still allows after 1 failure

    cb.record_failure("test_key")
    assert not cb.allow("test_key")  # Opens after threshold reached


def test_circuit_breaker_resets_on_success():
    """Test that circuit breaker resets failure count on success"""
    cb = CircuitBreaker(threshold=3, window_sec=60, cooldown_sec=30)

    # Record some failures
    cb.record_failure("test_key")
    cb.record_failure("test_key")
    assert cb.allow("test_key")  # Still below threshold

    # Record success - should reset
    cb.record_success("test_key")

    # Should allow after reset
    assert cb.allow("test_key")


def test_circuit_breaker_window_reset():
    """Test that circuit breaker resets after window expires"""
    cb = CircuitBreaker(threshold=2, window_sec=1, cooldown_sec=30)

    # Record failures
    cb.record_failure("test_key")
    cb.record_failure("test_key")
    assert not cb.allow("test_key")  # Circuit opens

    # Wait for window to expire and record another failure (should reset window)
    time.sleep(1.1)
    cb.record_failure("test_key")  # This should reset the window

    # Should allow since we're in a new window with only 1 failure
    assert cb.allow("test_key")


def test_call_with_timeout_success():
    """Test successful function call with timeout"""

    def quick_function():
        return "success"

    result = call_with_timeout(quick_function, 1.0)
    assert result == "success"


def test_call_with_timeout_timeout():
    """Test that timeout raises TimeoutError"""

    def slow_function():
        time.sleep(2.0)
        return "too_late"

    with pytest.raises(TimeoutError, match="operation timed out after 0.10s"):
        call_with_timeout(slow_function, 0.1)


def test_call_with_timeout_exception():
    """Test that exceptions are propagated"""

    def failing_function():
        raise ValueError("test error")

    with pytest.raises(ValueError, match="test error"):
        call_with_timeout(failing_function, 1.0)


def test_circuit_breaker_different_keys():
    """Test that circuit breaker tracks different keys independently"""
    cb = CircuitBreaker(threshold=2, window_sec=60, cooldown_sec=30)

    # Fail key1
    cb.record_failure("key1")
    cb.record_failure("key1")
    assert not cb.allow("key1")  # key1 opens

    # key2 should still work
    assert cb.allow("key2")

    # Fail key2
    cb.record_failure("key2")
    cb.record_failure("key2")
    assert not cb.allow("key2")  # key2 also opens

    # Both should be closed
    assert not cb.allow("key1")
    assert not cb.allow("key2")


@patch("core.resilience.monotonic")
def test_circuit_breaker_cooldown_recovery(mock_monotonic):
    """Test that circuit breaker recovers after cooldown period"""
    # Mock time progression: 2 failures at time 0, check at time 0, then check at time 150
    mock_times = [0, 0, 0, 150]  # 150 seconds later (after 120s cooldown)
    mock_monotonic.side_effect = mock_times

    cb = CircuitBreaker(threshold=2, window_sec=60, cooldown_sec=120)

    # Trigger circuit opening
    cb.record_failure("test_key")  # time=0
    cb.record_failure("test_key")  # time=0, opens circuit with open_until=120
    assert not cb.allow("test_key")  # time=0, circuit is open (120 > 0)

    # After cooldown period, should allow again
    assert cb.allow("test_key")  # time=150, circuit should be closed (120 < 150)

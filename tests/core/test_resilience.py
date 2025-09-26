import pytest
import time
from unittest.mock import patch
from core.resilience import CircuitBreaker, call_with_timeout

def test_circuit_breaker_allows_initially():
    """Test that circuit breaker allows requests initially"""
    cb = CircuitBreaker(threshold=3, window_sec=60, cooldown_sec=30)
    assert cb.allow("test_key") == True

def test_circuit_breaker_opens_after_failures():
    """Test that circuit breaker opens after threshold failures"""
    cb = CircuitBreaker(threshold=2, window_sec=60, cooldown_sec=30)
    
    # Should allow initially
    assert cb.allow("test_key") == True
    
    # Record failures
    cb.record_failure("test_key")
    assert cb.allow("test_key") == True  # Still allows after 1 failure
    
    cb.record_failure("test_key")
    assert cb.allow("test_key") == False  # Opens after threshold reached

def test_circuit_breaker_resets_on_success():
    """Test that circuit breaker resets failure count on success"""
    cb = CircuitBreaker(threshold=3, window_sec=60, cooldown_sec=30)
    
    # Record some failures
    cb.record_failure("test_key")
    cb.record_failure("test_key")
    assert cb.allow("test_key") == True  # Still below threshold
    
    # Record success - should reset
    cb.record_success("test_key")
    
    # Should allow after reset
    assert cb.allow("test_key") == True

def test_circuit_breaker_window_reset():
    """Test that circuit breaker resets after window expires"""
    cb = CircuitBreaker(threshold=2, window_sec=1, cooldown_sec=30)
    
    # Record failures
    cb.record_failure("test_key")
    cb.record_failure("test_key")
    assert cb.allow("test_key") == False  # Circuit opens
    
    # Wait for window to expire and record another failure (should reset window)
    time.sleep(1.1)
    cb.record_failure("test_key")  # This should reset the window
    
    # Should allow since we're in a new window with only 1 failure
    assert cb.allow("test_key") == True

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
    assert cb.allow("key1") == False  # key1 opens
    
    # key2 should still work
    assert cb.allow("key2") == True
    
    # Fail key2
    cb.record_failure("key2")
    cb.record_failure("key2")
    assert cb.allow("key2") == False  # key2 also opens
    
    # Both should be closed
    assert cb.allow("key1") == False
    assert cb.allow("key2") == False

@patch('time.monotonic')
def test_circuit_breaker_cooldown_recovery(mock_monotonic):
    """Test that circuit breaker recovers after cooldown period"""
    # Mock time progression
    mock_times = [0, 0, 0, 0, 0, 150]  # 150 seconds later
    mock_monotonic.side_effect = mock_times
    
    cb = CircuitBreaker(threshold=2, window_sec=60, cooldown_sec=120)
    
    # Trigger circuit opening
    cb.record_failure("test_key")
    cb.record_failure("test_key")
    assert cb.allow("test_key") == False  # Circuit opens
    
    # After cooldown period, should allow again
    assert cb.allow("test_key") == True  # Should be open after cooldown

# core/resilience.py
from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from time import monotonic
from typing import Any
from collections.abc import Callable

_EXEC = ThreadPoolExecutor(max_workers=32)
_lock = threading.Lock()


class CircuitBreaker:
    """Simple in-memory circuit breaker.
    Opens when failures >= threshold within 'window_sec'; stays open for cooldown_sec.
    """

    def __init__(self, threshold: int = 5, window_sec: int = 60, cooldown_sec: int = 120) -> None:
        self.threshold = threshold
        self.window = window_sec
        self.cooldown = cooldown_sec
        self.state: dict[str, dict[str, float]] = {}  # key -> {"fails": int, "window_start": ts, "open_until": ts}

    def allow(self, key: str) -> bool:
        now = monotonic()
        with _lock:
            s = self.state.get(key)
            if not s:
                return True
            if s.get("open_until", 0.0) > now:
                return False
            return True

    def record_success(self, key: str) -> None:
        with _lock:
            self.state.pop(key, None)

    def record_failure(self, key: str) -> None:
        now = monotonic()
        with _lock:
            s = self.state.setdefault(key, {"fails": 0, "window_start": now, "open_until": 0.0})
            # reset window if expired
            if now - s["window_start"] > self.window:
                s["fails"] = 0
                s["window_start"] = now
                s["open_until"] = 0.0  # Reset open state when window resets
            s["fails"] += 1
            if s["fails"] >= self.threshold:
                s["open_until"] = now + self.cooldown


breaker = CircuitBreaker()


def call_with_timeout(fn: Callable[[], Any], timeout_sec: float) -> Any:
    fut = _EXEC.submit(fn)
    try:
        return fut.result(timeout=timeout_sec)
    except FuturesTimeout:
        fut.cancel()
        raise TimeoutError(f"operation timed out after {timeout_sec:.2f}s")

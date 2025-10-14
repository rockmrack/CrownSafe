# Metrics _N Class Import Fix - October 14, 2025

## Issue Summary
CI test failure in the metrics test suite:
```
FAILED tests/core/test_metrics.py::TestNoOpBehavior::test_noop_class_methods - ImportError: cannot import name '_N' from 'core.metrics'
```

## Root Cause
The `_N` class (no-op metrics class) was defined inside the `else` block of a conditional import, making it inaccessible for direct import by tests:

**Original Structure:**
```python
try:
    from prometheus_client import Counter, Histogram
    PROM = True
except ImportError:
    PROM = False

if PROM:
    # Define real metrics...
else:
    class _N:  # ❌ Defined inside conditional block
        def labels(self, *_a, **_k):
            return self
        def observe(self, *_a, **_k):
            pass
        def inc(self, *_a, **_k):
            pass
    # Use _N() instances...
```

The test tried to import `_N` directly:
```python
from core.metrics import _N  # ❌ ImportError - _N not at module level
```

## Fix Applied

**File:** `core/metrics.py`

Moved the `_N` class definition **outside** the conditional block to make it available at module level:

**After:**
```python
# core/metrics.py
from __future__ import annotations
import os


# No-op class for when Prometheus is not available
class _N:
    """No-op metric class that does nothing but returns self for chaining"""

    def labels(self, *_a, **_k):
        return self

    def observe(self, *_a, **_k):
        pass

    def inc(self, *_a, **_k):
        pass


try:
    from prometheus_client import Counter, Histogram
    PROM = True
except ImportError:
    PROM = False

if PROM:
    # Define real Prometheus metrics
    CHAT_REQ = Counter(...)
    # ... etc
else:
    # Use no-op instances when Prometheus is not available
    CHAT_REQ = CHAT_LAT = TOOL_LAT = ... = _N()
```

### Key Changes
1. ✅ Moved `_N` class to module level (before try/except block)
2. ✅ Added docstring to clarify purpose
3. ✅ Removed duplicate `_N` definition from else block
4. ✅ Simplified else block to just create instances

## Why This Works

### Before (Broken)
- `_N` only defined when `PROM = False` (inside else block)
- Not accessible for import when Prometheus IS available
- Conditional definition makes it unpredictable for imports

### After (Fixed)
- `_N` always defined at module level
- Available for import regardless of Prometheus availability
- Used in production when Prometheus unavailable
- Used in tests to validate no-op behavior

## Test Validation

The test validates that the no-op class behaves correctly:
```python
def test_noop_class_methods(self):
    from core.metrics import _N  # ✅ Now works
    
    noop = _N()
    
    # All methods should return self or do nothing
    assert noop.labels("test", "args") == noop
    assert noop.labels(endpoint="test", intent="test") == noop
    
    # These should not raise exceptions
    noop.observe(100)
    noop.inc()
    noop.observe(0.5)
    noop.inc(5)
```

## Test Results

### Before Fix
- ❌ `test_noop_class_methods` - ImportError: cannot import name '_N'

### After Fix
- ✅ All 15 tests in `test_metrics.py` passing
- ✅ `_N` class properly importable
- ✅ No-op behavior validated
- ✅ No regressions in other metrics tests

## Impact Assessment

### Production Impact
- ✅ **No breaking changes** - Behavior unchanged
- ✅ **No-op metrics still work** - When Prometheus unavailable
- ✅ **Real metrics still work** - When Prometheus available
- ✅ **Import now possible** - For testing and introspection

### Code Quality
- ✅ **Better structure** - Class defined once at module level
- ✅ **More maintainable** - No duplicate definitions
- ✅ **More testable** - Direct import for unit tests
- ✅ **Clearer intent** - Docstring explains purpose

### Lines of Code
- **Reduced complexity**: -11 lines (23 insertions, 34 deletions)
- Eliminated duplicate class definition
- Simplified conditional block structure

## _N Class Purpose

The `_N` (No-op) class provides graceful degradation when Prometheus client library is not installed:

**Use Cases:**
1. **Development environments** - No metrics infrastructure needed
2. **Testing environments** - Metrics don't interfere with tests
3. **Lightweight deployments** - Optional monitoring without breaking functionality

**Behavior:**
- All metric methods (`labels()`, `observe()`, `inc()`) do nothing
- Methods return `self` for method chaining
- No errors raised, no side effects
- Zero overhead when Prometheus unavailable

## Related Metrics Functions

All these functions work with either real Prometheus metrics OR no-op instances:
```python
def inc_req(endpoint: str, intent: str, ok: bool, circuit: bool)
def obs_total(ms: int)
def obs_tool(intent: str, ms: int)
def obs_synth(ms: int)
def inc_fallback(endpoint: str, reason: str)
def inc_blocked(endpoint: str)
def inc_explain_feedback(helpful: bool, reason: str | None)
def inc_alternatives_shown(count: int)
def inc_alternative_clicked(alt_id: str)
def inc_unclear()
def inc_emergency()
```

## Commit Information
- **Commit:** 9888c82
- **Message:** "fix: make _N no-op metrics class importable for testing"
- **Files Changed:** 1 (`core/metrics.py`)
- **Lines Changed:** +23, -34 (net reduction of 11 lines)

## Lessons Learned

1. **Export what tests need** - If tests import it, it should be at module level
2. **Define classes once** - Avoid duplicate definitions in conditional blocks
3. **Graceful degradation patterns** - No-op classes enable optional dependencies
4. **Module-level exports** - Classes used by tests should be importable

## Next Steps

- ✅ Fix deployed and tests passing
- ✅ Changes pushed to remote
- ⏭️ Monitor CI/CD pipeline for full test suite results
- ⏭️ Consider documenting no-op pattern for other optional dependencies

---

**Status:** ✅ RESOLVED  
**Test Coverage:** 15/15 metrics tests passing (100%)  
**CI Status:** Awaiting full pipeline run

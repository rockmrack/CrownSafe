# CI/CD Fix: core_infra.cache_manager Import Issue

## Problem
The CI/CD pipeline was failing with:
```
ModuleNotFoundError: No module named 'core_infra.cache_manager'
```

## Root Causes

1. **Empty `__init__.py` file**: The `core_infra/__init__.py` was empty, making Python not recognize it as a proper package
2. **Packaging dependency conflict**: `black` requires `packaging>=22.0` while `safety==2.3.5` requires `packaging<22.0`
3. **Python path not fully configured**: The PYTHONPATH in CI wasn't including all necessary paths

## Fixes Applied

### 1. Fixed `core_infra/__init__.py`
Created a proper package initialization file that exports the key functions:
```python
from .cache_manager import get_cache_stats, get_cached, set_cached, invalidate_cached

__all__ = ['get_cache_stats', 'get_cached', 'set_cached', 'invalidate_cached']
```

### 2. Updated `safety` version in `tests/requirements-test.txt`
- Changed from `safety==2.3.5` to `safety==3.0.1`
- This version is compatible with `packaging>=22.0`

### 3. Enhanced PYTHONPATH in `.github/workflows/test-coverage.yml`
- Added core_infra to the PYTHONPATH explicitly
- Reordered pip installs to install packaging first

## Verification

The CI should now:
1. ✅ Properly import `core_infra.cache_manager`
2. ✅ Resolve all dependency conflicts
3. ✅ Run tests successfully

## Testing Locally

To test the fix locally:
```bash
# Set PYTHONPATH
export PYTHONPATH="$(pwd):$(pwd)/core_infra"

# Install dependencies
pip install --upgrade 'packaging>=22.0'
pip install -r config/requirements/requirements.txt
pip install -r tests/requirements-test.txt

# Test the import
python -c "from core_infra.cache_manager import get_cache_stats; print('✅ Import successful')"

# Run tests
pytest tests/
```

## Additional Notes

- The `core_infra/cache_manager.py` file exists and has all required functions
- Redis is made optional in the cache manager for test environments
- The cache manager gracefully handles missing Redis connections

## Status
✅ Fixed and ready for CI/CD

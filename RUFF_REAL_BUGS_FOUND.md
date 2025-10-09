# Real Bugs Found by Ruff (F821 - Undefined Names)

**Date**: October 9, 2025  
**Total**: 15 real bugs found  
**Status**: 🚨 REQUIRES FIXING

## Summary

Out of 759 Ruff violations, **only 15 are actual bugs** that could cause runtime crashes. All are missing imports.

---

## 🐛 Bug #1-3: Missing `asyncio` import

**File**: `core_infra/memory_optimizer.py`  
**Lines**: 126, 130, 145  
**Severity**: **HIGH** - Will crash if memory monitoring is started

### Current Code (BROKEN):
```python
# Line 1-12: imports
import gc
import logging
# ... other imports
# ❌ MISSING: import asyncio

# Line 126, 130, 145:
await asyncio.sleep(300)  # ❌ NameError: name 'asyncio' is not defined
```

### Fix:
```python
# Add at top of file (after line 6):
import asyncio
```

---

## 🐛 Bug #4-14: Missing model imports

**File**: `core_infra/query_optimizer.py`  
**Lines**: 212, 218, 226, 244, 247, 248, 330, 336, 348, 355  
**Severity**: **HIGH** - Will crash when query optimizer is used

### Current Code (BROKEN):
```python
# Line 1-13: imports
from sqlalchemy.orm import Query, Session, joinedload, selectinload, subqueryload, contains_eager
from sqlalchemy.sql import func
from sqlalchemy import and_, or_
# ❌ MISSING: from core_infra.database import User, Recall, Product

# Line 212, 218:
return db.query(User)  # ❌ NameError: name 'User' is not defined

# Line 226, 330, 336:
return db.query(Recall)  # ❌ NameError: name 'Recall' is not defined

# Line 244, 247, 248:
return db.query(Product)  # ❌ NameError: name 'Product' is not defined
```

### Fix:
```python
# Add after line 13:
from core_infra.database import User, Recall, Product
```

---

## 🐛 Bug #15-16: Missing `datetime` imports (TEST FILE)

**File**: `tests/core_infra/mcp_router_service/router.py`  
**Lines**: 161 (two uses)  
**Severity**: **MEDIUM** - Test file only, won't affect production

### Current Code (BROKEN):
```python
# Missing imports
# Line 161:
... datetime.now(timezone.utc)  # ❌ NameError: name 'datetime' is not defined
```

### Fix:
```python
# Add at top:
from datetime import datetime, timezone
```

---

## 📊 Impact Analysis

### Production Impact
- **HIGH RISK**: `memory_optimizer.py` - Used in production for memory management
- **HIGH RISK**: `query_optimizer.py` - Used in production for database queries
- **LOW RISK**: Test file - Not used in production

### Why Hasn't Production Crashed?
These features might not be actively used yet:
1. **Memory monitoring** - May not be started in production
2. **Query optimizer** - May not be called yet
3. **Test file** - Only runs during testing

### Recommendation
**FIX IMMEDIATELY** - These will cause crashes if/when these features are used.

---

## 🔧 Quick Fix Commands

```powershell
# 1. Fix memory_optimizer.py
# Add after line 6: import asyncio

# 2. Fix query_optimizer.py  
# Add after line 13: from core_infra.database import User, Recall, Product

# 3. Fix test file (optional)
# Add at top: from datetime import datetime, timezone
```

---

## ✅ After Fixing

Run to verify:
```powershell
ruff check . --select F821
```

Should show: **"All checks passed!"**

---

## 📈 Violation Breakdown

**Before**: 2055 total violations  
**After ignoring intentional patterns**: 759 violations  
**Real bugs**: **15 (2% of remaining)**  

The other 744 are just style issues (f-strings, semicolons, etc.) - not bugs.

---

## 🎯 Conclusion

**YES, you should fix these 15 bugs!** They're easy to fix (just add 3 import statements) and could prevent production crashes.

**Priority**:
1. 🔴 HIGH: Fix `memory_optimizer.py` and `query_optimizer.py` 
2. 🟡 LOW: Fix test file when convenient

**Time to fix**: ~2 minutes  
**Risk if not fixed**: Production crashes when these features are used

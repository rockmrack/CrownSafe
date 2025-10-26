# Crown Safe Cleanup Guide - Baby/Recall Code Removal

## Date: October 24, 2025

## Status: MANUAL INTERVENTION REQUIRED

Due to terminal encoding issues and file locking by VS Code, some cleanup tasks require manual intervention.

---

## ✅ COMPLETED TASKS

### 1. Database Cleanup (DONE)
- ✅ Removed RecallDB import and alias from `core_infra/database.py`
- ✅ Removed LegacyRecallDB class (35 lines)
- ✅ Removed is_pregnant field from User model
- ✅ Deleted commented FamilyMember and Allergy models (50+ lines)
- ✅ Deleted commented helper functions (40+ lines)
- ✅ Updated test functions to remove baby references

**Verification:**
```python
python -c "from core_infra.database import User; print([c.name for c in User.__table__.columns])"
# Output: ['id', 'email', 'stripe_customer_id', 'hashed_password', 'is_subscribed', 'is_active']
```

### 2. Visual Recognition System (DONE)
- ✅ Created `api/crown_safe_visual_endpoints.py` (630 lines)
- ✅ Implemented 7 API endpoints for hair product label scanning
- ✅ Registered visual router in `api/main_babyshield.py` (lines 4253-4260)

---

## ⚠️ MANUAL TASKS REQUIRED

### Task 1: Remove Baby/Recall Router Registrations

**File:** `api/main_babyshield.py`

**Lines to DELETE:**

#### Section 1: Lines 1269-1286 (Recall Alert System)
```python
# Include Recall Alert System
try:
    from api.recall_alert_system import recall_alert_router

    app.include_router(recall_alert_router)
    logging.info("✅ Recall Alert System registered")
except Exception as e:
    logging.error(f"Failed to register recall alert system: {e}")

# Include Recall Search System
try:
    from api.recalls_endpoints import router as recalls_router

    app.include_router(recalls_router)
    logging.info("✅ Recall Search System registered")
except Exception as e:
    logging.error(f"Failed to register recall search system: {e}")
```

**Action:** Delete these 18 lines completely.

---

#### Section 2: Lines ~1535-1540 (Recall Detail Endpoints)
```python
# Include recall detail endpoints
try:
    from api.recall_detail_endpoints import router as recall_detail_router

    app.include_router(recall_detail_router)
    logging.info("✅ Recall detail endpoints registered")
except Exception as e:
    logging.error(f"Failed to register recall detail endpoints: {e}")
```

**Action:** Delete these ~8 lines completely.

---

#### Section 3: Lines ~1651-1656 (Baby Safety Features)
```python
# Include Baby Safety Features (Alternatives, Notifications, Reports) endpoints
try:
    from api.baby_features_endpoints import router as baby_router

    app.include_router(baby_router)
    logging.info("✅ Baby Safety Features (Alternatives, Notifications, Reports) endpoints registered")
except (ImportError, FileNotFoundError) as e:
    logging.warning(f"Baby Safety Features not available (missing dependency pylibdmtx): {e}")
    # Continue without baby features - they're optional
```

**Action:** Delete these ~8 lines completely.

---

### Task 2: Remove Baby/Recall Pydantic Models

**File:** `api/main_babyshield.py`

**Models to DELETE or MODIFY:**

#### 1. SafetyCheckRequest (Lines ~295-297)
**Remove these fields:**
```python
check_pregnancy: Optional[bool] = Field(False, description="Include pregnancy safety check")
pregnancy_trimester: Optional[int] = Field(None, ge=1, le=3, description="If pregnant, specify trimester (1-3)")
check_allergies: Optional[bool] = Field(False, description="Include family allergy check")
```

**Keep only Crown Safe-relevant fields:**
```python
class SafetyCheckRequest(BaseModel):
    model_config = {"protected_namespaces": ()}

    barcode: Optional[str] = Field(
        None,
        pattern=r"^\d{8,14}$",
        example="012345678905",
        description="UPC/EAN barcode for direct lookup",
    )
    model_number: Optional[str] = Field(
        None,
        example="HC-2000X",
        description="Product model number",
    )
    lot_number: Optional[str] = Field(
        None,
        example="LOT2023-05-A",
        description="Lot or batch identifier",
    )
    product_name: Optional[str] = Field(
        None,
        example="Moisturizing Shampoo",
        description="Product name for text-based search",
    )
    image_url: Optional[str] = Field(None, example="https://example.com/img.jpg")
```

---

#### 2. RecallSearchRequest (Lines ~330-395) - ENTIRE CLASS
**DELETE THIS ENTIRE CLASS** - It's specific to recall searches:
```python
class RecallSearchRequest(BaseModel):
    # ... entire class definition ...
```

---

#### 3. RecallAnalyticsResponse (Lines ~405-415) - ENTIRE CLASS
**DELETE THIS ENTIRE CLASS** - It's specific to recall analytics:
```python
class RecallAnalyticsResponse(BaseModel):
    total_recalls: int
    agencies_active: int
    recent_recalls: int
```

---

### Task 3: Remove RecallDB Imports and Endpoints

**File:** `api/main_babyshield.py`

**Search for and remove all instances of:**
```python
from core_infra.database import RecallDB
```

**Locations (line numbers approximate):**
- Line 2726
- Line 2880
- Line 3251
- Line 3315
- Line 3444
- Line 4059

**For each import:**
1. Find the import statement
2. Identify the endpoint/function using RecallDB
3. Delete the entire endpoint/function
4. Delete the route decorator

**Example endpoints to DELETE:**
- `/search-recalls` endpoint
- `/recall-analytics` endpoint
- `/recall/{recall_id}` endpoint
- Any endpoint querying `recalls_enhanced` or `recalls` tables

---

### Task 4: Remove Connection Pool Optimizer

**File:** `api/main_babyshield.py`
**Line:** ~210

**DELETE:**
```python
try:
    from core_infra.connection_pool_optimizer import (
        optimized_recall_search,
        connection_optimizer,
    )
except ImportError:

    def optimized_recall_search(*args, **kwargs):
        return []

    connection_optimizer = None
    if not _in_test_env:
        raise
```

**REPLACE WITH:**
```python
# Connection pool optimizer removed (Crown Safe doesn't use recalls)
```

---

### Task 5: Delete Locked Files

**Files to DELETE** (when unlocked by closing in VS Code):
- `api/recall_detail_endpoints.py`
- `api/recall_alert_system.py`
- `api/recalls_endpoints.py`
- `api/baby_features_endpoints.py`
- `api/premium_features_endpoints.py`
- `core_infra/enhanced_database_schema.py`

**Steps:**
1. Close all open files in VS Code
2. Open PowerShell in project root
3. Run:
```powershell
Remove-Item "api\recall_detail_endpoints.py" -Force
Remove-Item "api\recall_alert_system.py" -Force
Remove-Item "api\recalls_endpoints.py" -Force
Remove-Item "api\baby_features_endpoints.py" -Force
Remove-Item "api\premium_features_endpoints.py" -Force
Remove-Item "core_infra\enhanced_database_schema.py" -Force
```

---

## 🧪 TESTING AFTER CLEANUP

### Test 1: Server Startup
```bash
python -m uvicorn api.main_babyshield:app --reload --port 8001
```

**Expected:**
- ✅ Server starts without errors
- ✅ No import errors for recall/baby modules
- ✅ Swagger docs load at http://localhost:8001/docs

### Test 2: Crown Safe Endpoints
**Test these endpoints in Swagger:**
1. `POST /api/v1/crown-safe/barcode/scan`
2. `POST /api/v1/crown-safe/visual/upload`
3. `POST /api/v1/crown-safe/visual/analyze`
4. `GET /api/v1/crown-safe/visual/scan-history`

**Expected:**
- ✅ All Crown Safe endpoints are visible
- ✅ No baby/recall endpoints are present
- ✅ Visual recognition endpoints work

### Test 3: Database Verification
```python
python -c "from core_infra.database import User, HairProductModel, IngredientModel; print('✅ Crown Safe models import successfully')"
```

**Expected:**
- ✅ No import errors
- ✅ User model has only Crown Safe fields
- ✅ Hair product models are available

---

## 📊 CLEANUP SUMMARY

### Files Modified
- ✅ `core_infra/database.py` - Removed all baby/recall code
- ⚠️ `api/main_babyshield.py` - Requires manual router removal
- ✅ `api/crown_safe_visual_endpoints.py` - Created (630 lines)

### Files to Delete
- ⏳ 6 files locked by VS Code (see Task 5)

### Lines of Code Removed
- Database: ~150 lines (RecallDB, is_pregnant, FamilyMember, Allergy)
- Main app (pending): ~50 lines (router registrations)
- Models (pending): ~100 lines (RecallSearchRequest, RecallAnalyticsResponse)
- Endpoints (pending): ~500+ lines (recall search, analytics, detail endpoints)

### Lines of Code Added
- Visual recognition: 630 lines (complete Crown Safe visual system)

---

## 🎯 NEXT STEPS

1. **PRIORITY 1:** Manually remove baby/recall router registrations (Tasks 1-2)
2. **PRIORITY 2:** Remove RecallDB imports and endpoints (Task 3)
3. **PRIORITY 3:** Delete locked files (Task 5)
4. **PRIORITY 4:** Test server startup and Crown Safe endpoints
5. **PRIORITY 5:** Integrate actual OCR service (Google Cloud Vision or AWS Textract)

---

## 📝 NOTES

### Why Manual Intervention?
- Terminal encoding issues with UTF-8 checkmark emojis (✅)
- Files locked by VS Code editor process
- OneDrive sync conflicts preventing automated file operations

### Automation Script Available
- `scripts/remove_baby_routers.py` - Identifies sections to remove
- Failed due to file descriptor issues (OneDrive/VS Code locking)
- Can be used as a reference for what needs to be removed

### Estimated Time
- Manual router removal: 5-10 minutes
- Model cleanup: 5-10 minutes
- Endpoint removal: 15-20 minutes
- File deletion: 2 minutes
- Testing: 10-15 minutes
- **Total: 40-60 minutes**

---

**Created:** October 24, 2025  
**Status:** Ready for manual cleanup  
**Priority:** HIGH - Blocking server startup and Crown Safe deployment

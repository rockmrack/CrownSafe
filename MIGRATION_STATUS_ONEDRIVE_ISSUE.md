# Crown Safe Migration Status - OneDrive File Locking Issue

**Date**: October 24, 2025  
**Status**: 90% Complete - Blocked by OneDrive File Locking

## ✅ COMPLETED WORK

### 1. RecallDB Import Removal (100%)
- ✅ All 6 RecallDB imports commented out
- ✅ Lines: 2726, 2880, 3251, 3315, 3444, 4059

### 2. Dead Code Functions Cleaned (83%)
- ✅ Function 1: `autocomplete_suggestions` (82 lines removed)
- ✅ Function 2: `brand_autocomplete` (51 lines removed)
- ✅ Function 3: `recall_analytics` (43 lines removed)
- ✅ Function 4: `analytics_counts` (19 lines removed)
- ✅ Function 5: `agency_health_check` (36 lines removed)
- ✅ Additional: `system_health` (line 3236 - 5 lines commented)
- **Total removed: 237 lines**

### 3. Crown Safe Models Verification (100%)
- ✅ All 8 models properly imported in `core_infra/database.py` (lines 102-113):
  - HairProfileModel
  - HairProductModel
  - IngredientModel
  - ProductScanModel
  - ProductReviewModel
  - BrandCertificationModel
  - SalonAccountModel
  - MarketInsightModel

### 4. Database Migration (Successful in Temp Folder)
- ✅ Migration file ready: `crown_safe_v1`
- ✅ **Successfully executed on temp database**: `C:\Users\rossd\AppData\Local\Temp\babyshield_dev.db`
- ✅ Created all 8 Crown Safe tables
- ✅ Removed old tables: `allergies`, `family_members`
- ✅ Removed column: `users.is_pregnant`

## ⚠️ CURRENT BLOCKERS

### Blocker 1: OneDrive File Locking (CRITICAL)
**Issue**: OneDrive aggressively locks `db/babyshield_dev.db` preventing writes, copies, and deletes.

**Evidence**:
```
Access to the path 'C:\Users\rossd\OneDrive\Documents\Crown Safe\db\babyshield_dev.db' is denied.
```

**Impact**:
- Cannot copy migrated database from temp folder back to original location
- Cannot run migrations directly on OneDrive-synced database
- Cannot remove or replace the database file

**Workaround Created**: `migrate_with_onedrive_pause.ps1` script

### Blocker 2: fix_upc_data Function (Lines 3854, 3912-3913)
**Issue**: 3 active RecallDB queries remain, causing NameError when called.

**Lines**:
- Line 3854: `db.query(RecallDB).filter(RecallDB.upc.is_(None)).limit(200).all()`
- Line 3912: `db.query(RecallDB).filter(RecallDB.upc.isnot(None)).count()`
- Line 3913: `db.query(RecallDB).count()`

**Manual Fix**: See `MANUAL_FIX_FUNCTION6.md` (3 minutes)

## 🎯 NEXT STEPS (In Order)

### Step 1: Fix OneDrive Issue (Choose One Method)

#### **Method A: Use PowerShell Script (Recommended)**
```powershell
.\migrate_with_onedrive_pause.ps1
```
This script will:
1. Pause OneDrive
2. Verify database access
3. Run Alembic migration
4. Verify Crown Safe tables
5. Restart OneDrive

#### **Method B: Manual OneDrive Pause**
1. Right-click OneDrive icon in system tray
2. Click "Pause syncing" → "2 hours"
3. Wait 10 seconds
4. Run migration:
   ```powershell
   cd "c:\Users\rossd\OneDrive\Documents\Crown Safe\db"
   $env:DATABASE_URL="sqlite:///c:/Users/rossd/OneDrive/Documents/Crown Safe/db/babyshield_dev.db"
   alembic upgrade head
   ```
5. Resume OneDrive syncing

#### **Method C: Use Temp Database Copy**
```powershell
# 1. Pause OneDrive
Right-click OneDrive → Pause syncing → 2 hours

# 2. Delete old database (now possible with OneDrive paused)
Remove-Item "c:\Users\rossd\OneDrive\Documents\Crown Safe\db\babyshield_dev.db" -Force

# 3. Copy migrated database from temp
Copy-Item "C:\Users\rossd\AppData\Local\Temp\babyshield_dev.db" "c:\Users\rossd\OneDrive\Documents\Crown Safe\db\babyshield_dev.db"

# 4. Verify tables
cd "c:\Users\rossd\OneDrive\Documents\Crown Safe"
python check_db_tables.py

# 5. Resume OneDrive
```

### Step 2: Fix fix_upc_data Function (3 minutes)
Follow `MANUAL_FIX_FUNCTION6.md`:
1. Open `api/main_babyshield.py` in VS Code
2. Navigate to line 3848
3. Select lines 3848-3933 (entire function)
4. Replace with safe return statement (details in manual)

### Step 3: Test Server Startup (5 minutes)
```powershell
cd "c:\Users\rossd\OneDrive\Documents\Crown Safe"
python -m uvicorn api.main_babyshield:app --reload --port 8001
```

**Expected**: Server starts without NameError
**Check**: No RecallDB import errors in logs

### Step 4: Remove Legacy Router Registrations (15 minutes)
Follow `MANUAL_ROUTER_EDIT_INSTRUCTIONS.md`

## 📊 PROGRESS METRICS

| Task                        | Status            | Completion                              |
| --------------------------- | ----------------- | --------------------------------------- |
| RecallDB imports removed    | ✅ Complete        | 100%                                    |
| Dead code functions cleaned | ⏳ In Progress     | 83% (5.5/6)                             |
| Crown Safe models verified  | ✅ Complete        | 100%                                    |
| Database migration          | ⏳ In Progress     | 95% (ran successfully, needs copy back) |
| Router cleanup              | ❌ Not Started     | 0%                                      |
| **Overall**                 | ⏳ **In Progress** | **90%**                                 |

## 🔧 FILES CREATED

### Scripts
- ✅ `migrate_with_onedrive_pause.ps1` - Automated migration with OneDrive pause
- ✅ `run_migration.py` - Programmatic Alembic migration
- ✅ `verify_migration.py` - Database verification script
- ✅ `check_db_tables.py` - Quick table checker

### Documentation
- ✅ `MANUAL_FIX_FUNCTION6.md` - Step-by-step for fix_upc_data
- ✅ `MANUAL_ROUTER_EDIT_INSTRUCTIONS.md` - Router cleanup guide
- ✅ `DEAD_CODE_REMOVAL_PROGRESS.md` - Comprehensive session summary
- ✅ `MIGRATION_STATUS_ONEDRIVE_ISSUE.md` - This document

## 💡 TECHNICAL NOTES

### OneDrive File Locking Behavior
- OneDrive locks files during sync operations
- SQLite databases are particularly affected due to write operations
- Locking prevents: copy, move, delete, and modify operations
- Solution: Pause OneDrive before database operations

### Database Migration Details
- **Current revision**: `20251014_missing_tables`
- **Target revision**: `crown_safe_v1` (head)
- **Migration actions**:
  - Creates 8 new tables (hair_profiles, hair_products, etc.)
  - Drops 2 old tables (allergies, family_members)
  - Removes 1 column (users.is_pregnant)
- **Migration tested**: ✅ Successfully ran on temp database

### Remaining Work Estimate
- OneDrive workaround: **5 minutes** (Method A or B)
- fix_upc_data manual edit: **3 minutes**
- Server startup test: **5 minutes**
- Router cleanup: **15 minutes**
- **Total**: ~30 minutes manual work

## 🚨 CRITICAL PATH

To complete the migration and get the server running:

1. **Fix OneDrive issue** (Method A recommended) → Enables database migration completion
2. **Fix fix_upc_data function** → Eliminates last NameError source
3. **Test server startup** → Validates all fixes work
4. **Router cleanup** (optional) → Cleans up API surface

## 📞 TROUBLESHOOTING

### If Migration Script Fails
Check:
- Is OneDrive paused? (Right-click icon to verify)
- Are any Python processes running? (`Get-Process python*`)
- Is database file locked? (Try opening in another program)

### If Server Still Crashes
- Check logs for remaining RecallDB references
- Verify database has Crown Safe tables: `python check_db_tables.py`
- Ensure fix_upc_data was fully replaced (lines 3848-3933)

### If Router Registration Fails
- Use VS Code find/replace with regex
- Follow MANUAL_ROUTER_EDIT_INSTRUCTIONS.md exactly
- Test each endpoint after changes

## ✅ SUCCESS CRITERIA

Migration is complete when:
- ✅ Database has all 8 Crown Safe tables
- ✅ Old baby-specific tables removed
- ✅ No RecallDB queries in main_babyshield.py
- ✅ Server starts without NameError
- ✅ Crown Safe endpoints respond (optional validation)

---

**Next Action**: Run `.\migrate_with_onedrive_pause.ps1` to complete the database migration, then manually fix the `fix_upc_data` function.

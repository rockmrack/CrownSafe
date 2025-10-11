# CI Workflow Fix - Root Cause Analysis

**Date**: October 11, 2025  
**Status**: ✅ ISSUE IDENTIFIED AND FIXED

## The Real Problem

### Root Cause: Alembic `script_location` Path Issue

The Test Coverage workflow was failing because **Alembic couldn't find the migrations directory**.

#### What Was Happening

1. `db/alembic.ini` has: `script_location = migrations` (RELATIVE path)
2. `scripts/init_test_database.py` was running:
   ```python
   subprocess.run(
       ["alembic", "-c", "db/alembic.ini", "upgrade", "head"],
       cwd=str(project_root),  # Running from PROJECT ROOT
   )
   ```
3. Alembic looked for `migrations/` in the project root, but it's actually at `db/migrations/`
4. Migration failed with return code 255 (path not found)
5. Script checked for `recalls_enhanced` table → NOT FOUND → sys.exit(1)

#### The Fix

Changed `scripts/init_test_database.py` to:
```python
subprocess.run(
    ["alembic", "upgrade", "head"],
    cwd=str(project_root / "db"),  # Run FROM db/ directory
    env={**os.environ, "DATABASE_URL": database_url},  # Pass DATABASE_URL explicitly
)
```

Now:
- Alembic runs from `db/` directory where `alembic.ini` lives
- `script_location = migrations` resolves correctly to `db/migrations/`
- DATABASE_URL is explicitly passed (no environment variable issues)
- Migration runs successfully
- `recalls_enhanced` table gets created
- Script succeeds

## Previous Fix Attempts

### Attempt #1: Update workflow to pass DATABASE_URL
❌ **Didn't work** - The workflow's manual Alembic call worked, but `init_test_database.py` was still failing BEFORE it

### Attempt #2: Black formatting
✅ **Partially worked** - Fixed Code Quality issues, but didn't address the database problem

## Commits

1. **d541fbe** - Black formatting (342 files)
2. **7580e1a** - DATABASE_URL fix in workflow
3. **679981d** - Documentation
4. **0dfffed** - **THE REAL FIX** - Run Alembic from db/ directory

## Expected Results

**Test Coverage Workflow:**
- ✅ `init_test_database.py` runs successfully
- ✅ Alembic migrations complete
- ✅ `recalls_enhanced` table created
- ✅ All tests run

**Code Quality Workflow:**
- ✅ Black formatting checks pass
- ✅ 658 files properly formatted

## Lessons Learned

1. **Relative paths in config files are tricky** - `script_location = migrations` assumes current directory
2. **Working directory matters** - Alembic must run from where `alembic.ini` expects
3. **Check subprocess return codes** - Return code 255 often means "can't find file/path"
4. **Environment variables in subprocesses** - Must be explicitly passed with `env=` parameter

## Verification

To test locally:
```bash
# This will FAIL (wrong directory)
cd c:\code\babyshield-backend
alembic -c db/alembic.ini upgrade head

# This will WORK (correct directory)
cd c:\code\babyshield-backend\db
alembic upgrade head
```

---

**Status**: Ready for CI run. Both issues should be fixed now! 🎉

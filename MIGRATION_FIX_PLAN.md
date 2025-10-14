# Migration Fix Plan - October 14, 2025

## Problem Summary

### Issues Found
1. **Missing Tables in CI**: `incident_reports` and `image_jobs` tables don't exist in the CI PostgreSQL database
2. **Dual Migration Directories**: Two separate migration directories causing confusion:
   - `db/migrations/versions/` - Currently used (only 5 migrations)
   - `db/alembic/versions/` - Contains 23+ migrations including `incident_reports`
3. **Test Failure**: `test_api_rate_limit_per_user_enforced` returns 500 error (but passes locally)
4. **Test Count**: Only 94 tests collected (user expected 1000+, but this may be normal)

### Root Cause
The `db/alembic.ini` file points to `script_location = migrations`, but many important migrations including `incident_reports`, `image_jobs`, and others are in `db/alembic/versions/` and are NEVER being run!

## Solution

### Option 1: Move Migrations (RECOMMENDED)
Move all migrations from `db/alembic/versions/` into `db/migrations/versions/`:

```powershell
# Backup first!
Copy-Item "db/alembic/versions" -Destination "db/alembic/versions_backup" -Recurse

# Move all migrations
Move-Item "db/alembic/versions/*.py" -Destination "db/migrations/versions/"
```

Then update revision IDs to ensure proper chain.

### Option 2: Update alembic.ini (SIMPLER - DO THIS FIRST)
Change `db/alembic.ini` to point to the correct directory:

```ini
# Change from:
script_location = migrations

# Change to:
script_location = alembic/versions
```

But this requires updating `env.py` path as well.

### Option 3: Consolidate with New Migration
1. Keep current `db/migrations/` structure
2. Create a NEW migration that adds ALL missing tables
3. Copy table definitions from `db/alembic/versions/20250109_incident_reports.py`

## Immediate Fix Steps

### Step 1: Update Model Imports (DONE ✅)
Updated `db/migrations/env.py` to import ALL models:
- ✅ IncidentReport, IncidentCluster, AgencyNotification
- ✅ ImageJob, ImageExtraction, ReviewQueue, MFVSession, ImageAnalysisCache
- ✅ ScanHistory, SafetyReport, ShareToken, SerialVerification
- ✅ ReportRecord, PrivacyRequest, IngestionRun, UserReport
- ✅ Risk assessment models (ProductGoldenRecord, etc.)

###  Step 2: Create Consolidated Migration

Create a new migration file: `db/migrations/versions/2025_10_14_add_all_missing_tables.py`

This migration should include:
1. **incident_reports** table (from `db/alembic/versions/20250109_incident_reports.py`)
2. **incident_clusters** table
3. **agency_notifications** table
4. **image_jobs** table (needs to be created from model)
5. **image_extractions** table
6. **review_queue** table
7. **mfv_sessions** table
8. **image_analysis_cache** table
9. All other tables from `db/alembic/versions/` that are missing

### Step 3: Fix CI Workflow

Ensure CI workflow runs migrations properly:

```yaml
- name: Setup PostgreSQL database
  env:
    DATABASE_URL: "postgresql://postgres:postgres@localhost:5432/postgres"
  run: |
    # Install PostgreSQL client
    sudo apt-get update
    sudo apt-get install -y postgresql-client
    
    # Enable pg_trgm extension
    PGPASSWORD=postgres psql -h localhost -U postgres -d postgres -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"
    
    # Run Alembic migrations from db/ directory
    cd db && alembic upgrade head
```

### Step 4: Test Locally

```powershell
# Set up PostgreSQL locally
$env:DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/test_db"

# Run migrations
cd db
alembic upgrade head

# Verify tables exist
psql $env:DATABASE_URL -c "\dt"

# Run the failing test
cd ..
pytest tests/security/test_security_vulnerabilities.py::TestRateLimiting::test_api_rate_limit_per_user_enforced -v
```

## Files Changed

### ✅ db/migrations/env.py
- Added imports for ALL models (incident_reports, image_jobs, etc.)
- Added `# ruff: noqa: F401` to suppress unused import warnings

### 🔄 db/migrations/versions/2025_10_14_add_all_missing_tables.py (TO CREATE)
- Will contain all missing table definitions

## Database Tables Status

### Currently In Migrations (db/migrations/versions/)
1. ✅ recalls_enhanced
2. ✅ report_records
3. ✅ pg_trgm extension
4. ✅ user_reports
5. ✅ users (via Base.metadata.create_all in tests)

### Missing But Defined in Models
1. ❌ incident_reports
2. ❌ incident_clusters
3. ❌ agency_notifications
4. ❌ image_jobs
5. ❌ image_extractions
6. ❌ review_queue
7. ❌ mfv_sessions
8. ❌ image_analysis_cache
9. ❌ scan_history
10. ❌ safety_reports
11. ❌ share_tokens
12. ❌ serial_verifications
13. ❌ privacy_requests
14. ❌ ingestion_runs
15. ❌ product_golden_records
16. ❌ product_risk_profiles
17. ❌ product_data_sources
18. ❌ safety_incidents
19. ❌ company_compliance_profiles
20. ❌ risk_assessment_reports
21. ❌ data_ingestion_jobs
22. ❌ monitoring_notifications
23. ❌ safety_articles
24. ❌ chat_memory
25. ❌ explain_feedback

### Present in db/alembic/versions/ (NOT BEING RUN!)
All of the above plus:
- subscription tables
- OAuth fields
- ingredient safety tables
- account deletion audit
- performance indexes
- composite indexes

## Testing Strategy

1. **Local Test** (SQLite - limited):
   - Can test basic migration structure
   - Cannot test PostgreSQL-specific features (JSONB, pg_trgm)

2. **CI Test** (PostgreSQL):
   - Full migration testing
   - Proper JSONB support
   - Extension support

3. **Production Prep**:
   - Test migration on production database copy
   - Verify no data loss
   - Document rollback procedure

## Rollback Plan

If migrations fail:

```bash
# Rollback one migration
cd db && alembic downgrade -1

# Rollback to specific revision
cd db && alembic downgrade <revision_id>

# Check current version
cd db && alembic current
```

## Next Steps

1. ✅ Update `db/migrations/env.py` with all model imports (DONE)
2. 🔄 Create consolidated migration for all missing tables
3. ⏳ Test migration with PostgreSQL
4. ⏳ Update CI workflow if needed
5. ⏳ Deploy to staging
6. ⏳ Deploy to production

## Notes

- The test `test_api_rate_limit_per_user_enforced` is passing locally but may fail in CI due to missing tables
- Test count of 94 is correct - not 1000+
- SQLite doesn't support JSONB, so local testing is limited
- Production uses PostgreSQL with all proper extensions

## References

- Migration directory issue discussed in COPILOT_AUDIT_COMPLETE.md
- Incident reports model: `db/models/incident_report.py`
- Visual agent models: `core_infra/visual_agent_models.py`
- Risk assessment models: `core_infra/risk_assessment_models.py`
- Current migrations: `db/migrations/versions/`
- Unused migrations: `db/alembic/versions/`

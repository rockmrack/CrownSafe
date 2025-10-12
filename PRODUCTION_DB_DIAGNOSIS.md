# Production Deployment Status - is_active Column Issue

## Current Status

### ✅ Confirmed Working:
1. **Docker Image Built**: `is-active-fix-20251012-1648`
2. **Image Pushed to ECR**: October 12, 2025, 16:49:55 UTC+02
3. **Image Digest**: `sha256:a737ea774794a1326760c993c416031036bfea1131505060200f308df162e36f`
4. **ECS Deployment**: Image IS running in production (you confirmed this)
5. **Database Column Added**: We ran `add_is_active_column.py` and it confirmed column was added

### ❌ Still Failing:
- Production API still returns: "column users.is_active does not exist"

## Root Cause Analysis

There are only a few possible explanations:

### 1. **Different Database** (Most Likely)
The production ECS container might be connecting to a **different database** than the one where we added the column.

**Check:**
- Local script connected to: `babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com`
- ECS container connecting to: **???** (might be different endpoint or database name)

**Solution:** Verify ECS environment variables:
```powershell
aws ecs describe-task-definition `
  --task-definition babyshield-backend-task `
  --region eu-north-1 `
  --query 'taskDefinition.containerDefinitions[0].environment'
```

Look for `DATABASE_URL`, `DB_HOST`, `DB_NAME` environment variables.

### 2. **Read Replica Connection**
The application might be using a **read replica** that hasn't synced yet, or a connection pool that cached the old schema.

**Solution:** Restart ALL database connections by forcing new ECS tasks.

### 3. **Wrong Database Name**
We might have added the column to `babyshield_db` but the app connects to `babyshield_prod` or vice versa.

**Solution:** Check which database the app actually uses:
```sql
-- Connect to production RDS and run:
SELECT current_database();

-- Then check if is_active exists in that specific database:
SELECT column_name, data_type, is_nullable, column_default 
FROM information_schema.columns 
WHERE table_name = 'users' AND column_name = 'is_active' 
  AND table_schema = 'public';
```

### 4. **Schema/Namespace Issue**
PostgreSQL might be looking in a different schema (e.g., `public` vs custom schema).

**Solution:** Explicitly check schema:
```sql
SELECT schemaname, tablename 
FROM pg_tables 
WHERE tablename = 'users';
```

### 5. **SQLAlchemy Metadata Cache**
The ORM might have cached the old table metadata before the column was added.

**Solution:** This should be cleared by restarting containers, which we did.

## Recommended Next Steps

### Step 1: Verify Database Connection (CRITICAL)

Create a diagnostic endpoint to check what database the production app is actually connected to:

Add to `api/main_babyshield.py`:
```python
@app.get("/debug/db-info")
async def debug_db_info(db: Session = Depends(get_db)):
    """Debug endpoint to verify database connection"""
    result = db.execute(text("SELECT current_database(), current_schema(), version()"))
    row = result.fetchone()
    
    # Check if is_active column exists
    columns_result = db.execute(text("""
        SELECT column_name, data_type, is_nullable, column_default 
        FROM information_schema.columns 
        WHERE table_name = 'users' AND table_schema = 'public'
        ORDER BY ordinal_position
    """))
    columns = [dict(row) for row in columns_result]
    
    return {
        "current_database": row[0],
        "current_schema": row[1],
        "postgres_version": row[2],
        "users_table_columns": columns,
        "is_active_exists": any(col["column_name"] == "is_active" for col in columns)
    }
```

Then call: `https://babyshield.cureviax.ai/debug/db-info`

### Step 2: Check ECS Environment Variables

```powershell
# Get task definition
aws ecs describe-task-definition `
  --task-definition babyshield-backend-task `
  --region eu-north-1 `
  --query 'taskDefinition.containerDefinitions[0].{secrets:secrets,environment:environment}' `
  --output json
```

Look for database connection strings.

### Step 3: Verify Column in Correct Database

```powershell
# Connect to production database
# Use the EXACT connection string the ECS app uses
psql "postgresql://babyshield_user:MandarunLabadiena25!@babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com:5432/babyshield_db"

# Then run:
\d users
-- This shows the users table structure
-- Verify is_active column is there
```

### Step 4: Force Schema Refresh

If the column exists but app doesn't see it:

```sql
-- In production database:
VACUUM ANALYZE users;
-- This refreshes table statistics
```

Then restart ECS tasks again:
```powershell
# Stop all tasks to force complete restart
$tasks = aws ecs list-tasks `
  --cluster babyshield-cluster `
  --service-name babyshield-backend-task-service-0l41s2a9 `
  --region eu-north-1 `
  --query 'taskArns' `
  --output json | ConvertFrom-Json

foreach ($task in $tasks) {
    aws ecs stop-task --cluster babyshield-cluster --task $task --region eu-north-1
}
```

## Most Likely Issue

Based on the error pattern, I suspect **the ECS app is connecting to a different database than where we added the column**.

The script we ran locally connected to:
- Host: `babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com`
- Database: `babyshield_db` (probably)

But the ECS app might be connecting to:
- Same host, **different database name** (e.g., `babyshield_prod`, `postgres`, etc.)
- Or using AWS Secrets Manager that points to different credentials

**ACTION NEEDED:**
1. Check the actual database name the ECS app connects to
2. Add the `is_active` column to THAT specific database
3. Then the app will work immediately

---

**Next Action:** Add the debug endpoint and call it to see which database the production app is actually using.

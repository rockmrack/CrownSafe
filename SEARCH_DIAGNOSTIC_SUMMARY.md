# Production Search Diagnostic Summary

**Date**: October 16, 2025  
**Status**: pg_trgm enabled on `babyshield_db`, search still returns 0 results

## ✅ What We've Confirmed

1. **Extension Enabled**: pg_trgm v1.6 installed on `babyshield_db` ✅
2. **Indexes Created**: All 4 GIN indexes created ✅  
3. **Data Exists**: 131,743 records in `babyshield_db.recalls_enhanced` ✅
4. **Code Uses pg_trgm**: SearchService has `similarity()` function calls ✅

## ❌ The Problem

**Search still returns 0 results** despite extension being enabled.

## 🔍 Root Cause Analysis

The code in `api/services/search_service.py` (lines 142-168) has this logic:

```python
# Check if pg_trgm is available before using it
use_pg_trgm = False
if dialect == "postgresql":
    try:
        use_pg_trgm = self.check_pg_trgm_enabled()
        if not use_pg_trgm:
            logger.warning("[WARN] pg_trgm extension not enabled, falling back to LIKE search")
    except Exception as e:
        logger.warning(f"[WARN] pg_trgm check failed: {e}, falling back to LIKE search")

if dialect == "postgresql" and use_pg_trgm:
    # Use pg_trgm similarity for fuzzy matching
    similarity_expressions = [
        f"similarity(lower({table}.product_name), :search_text)",
        f"similarity(lower({table}.brand), :search_text)",
        ...
    ]
    score_expression = f"GREATEST({', '.join(similarity_expressions)})"
    where_conditions.append(f"{score_expression} >= 0.08")  # 8% threshold
```

**Possible Causes:**

### 1. DATABASE_URL Points to Wrong Database
- **Issue**: Environment variable `DATABASE_URL` might point to `postgres` database (0 records)
- **Check**: Look at ECS task definition environment variables
- **Fix**: Change DATABASE_URL to use `babyshield_db` instead of `postgres`

### 2. Extension Check Runs on Wrong Database
- **Issue**: `check_pg_trgm_enabled()` queries current connection
- **Code**: 
  ```python
  def check_pg_trgm_enabled(self) -> bool:
      result = self.db.execute(
          text("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm')")
      )
      return result.scalar()
  ```
- **If DATABASE_URL = postgres**: Check returns `true` (we enabled it there first)
- **If DATA in babyshield_db**: Search returns 0 (wrong database queried)

### 3. Similarity Threshold Too High
- **Threshold**: `>= 0.08` (8% similarity minimum)
- **Issue**: "baby" might not match products with <8% similarity
- **Test**: Lower threshold or test exact match

## 🎯 Most Likely Fix

**DATABASE_URL is pointing to `postgres` database instead of `babyshield_db`**

### How to Verify

Check ECS task definition environment:
```bash
aws ecs describe-task-definition \
  --task-definition babyshield-backend-task-definition \
  --region eu-north-1 \
  --query 'taskDefinition.containerDefinitions[0].environment[?name==`DATABASE_URL`].value' \
  --output text
```

Expected output should include `babyshield_db`:
```
postgresql://babyshield_user:MandarunLabadiena25!@babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com:5432/babyshield_db
```

If it shows `postgres` instead of `babyshield_db`, that's the problem!

### How to Fix

**Option 1: Update ECS Task Definition** (Proper Way)
1. Download current task definition
2. Change DATABASE_URL from `/postgres` to `/babyshield_db`
3. Register new task definition revision
4. Update ECS service to use new revision
5. Wait for deployment

**Option 2: Use Parameter Store/Secrets Manager** (Best Practice)
1. Store DATABASE_URL in AWS Systems Manager Parameter Store
2. Reference in task definition as secret
3. Update parameter value to point to `babyshield_db`
4. Restart ECS service

## 🔧 Quick Test Commands

### Test database connection from CloudShell:
```bash
# Re-add IP
MY_IP=$(curl -s https://checkip.amazonaws.com)
SG_ID=sg-0e2aed27cbf2213ed
aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 5432 --cidr $MY_IP/32 --region eu-north-1

# Test search query on correct database
PGPASSWORD='MandarunLabadiena25!' psql -h babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com -U babyshield_user -d babyshield_db << 'SQL'
-- Test if pg_trgm works
SELECT 
    product_name, 
    brand,
    similarity(lower(product_name), 'baby') as score
FROM recalls_enhanced
WHERE similarity(lower(product_name), 'baby') >= 0.08
ORDER BY score DESC
LIMIT 5;
SQL

# Remove IP
aws ec2 revoke-security-group-ingress --group-id $SG_ID --protocol tcp --port 5432 --cidr $MY_IP/32 --region eu-north-1
```

This will show if similarity search actually works on the database.

## 📋 Next Steps

1. **Check DATABASE_URL** in ECS task definition
2. **If wrong database**: Update task definition
3. **Deploy new revision**
4. **Test search again**

---

**Current Blocker**: Need to verify which database the application is actually connecting to.

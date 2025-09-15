# 🚨 URGENT: Fix BabyShield API Deployment

## Problem
The `/api/v1/search/advanced` endpoint returns 404 on production but exists in code.

## Root Cause
The deployed version is **outdated** and missing recent changes including:
- Search endpoint (`/api/v1/search/advanced`)
- Search service (`services/search_service.py`)
- Database migrations for pg_trgm indexes
- All Task 1-9 improvements

## 🔧 IMMEDIATE FIX INSTRUCTIONS

### Step 1: Commit All Changes (Local)
```bash
# Check what's not committed
git status

# Add all new/modified files
git add .

# Commit with clear message
git commit -m "feat: Add search/advanced endpoint with pg_trgm support + Tasks 1-9 complete"

# Push to your repository
git push origin main  # or your deployment branch
```

### Step 2: Update Production Server

SSH into your production server and run:

```bash
# Navigate to app directory
cd /path/to/babyshield-backend  # Update with your actual path

# Pull latest code
git pull origin main

# Install/update dependencies
pip install -r requirements.txt

# CRITICAL: Run database migrations
alembic upgrade head
# This will create pg_trgm indexes needed for search

# Restart the application
# Option 1: If using systemd
sudo systemctl restart babyshield

# Option 2: If using PM2
pm2 restart babyshield

# Option 3: If using supervisor
sudo supervisorctl restart babyshield

# Option 4: If using Docker
docker-compose down
docker-compose up -d

# Option 5: If using Gunicorn directly
pkill gunicorn
gunicorn api.main_babyshield:app --bind 0.0.0.0:8000 --workers 4 &
```

### Step 3: Clear CDN/Proxy Cache (if applicable)

If using CloudFront:
```bash
aws cloudfront create-invalidation --distribution-id YOUR_DIST_ID --paths "/*"
```

If using Nginx:
```bash
sudo nginx -s reload
```

### Step 4: Verify Deployment

Test the endpoints:

```bash
# 1. Health check
curl https://babyshield.cureviax.ai/api/v1/healthz

# 2. Test search endpoint
curl -X POST https://babyshield.cureviax.ai/api/v1/search/advanced \
  -H "Content-Type: application/json" \
  -d '{"product": "pacifier", "limit": 5}'

# 3. Check OpenAPI docs
curl https://babyshield.cureviax.ai/docs
```

## 📋 Files That Must Be Deployed

### Critical Files for Search Endpoint:
- ✅ `api/main_babyshield.py` (line 899 has the endpoint)
- ✅ `services/search_service.py` (search logic)
- ✅ `api/models/search_validation.py` (request validation)
- ✅ `alembic/versions/20250826_search_trgm_indexes.py` (database indexes)

### Other Important Files from Tasks:
- `api/middleware/` (correlation, access_log, etc.)
- `api/errors.py` (unified error handling)
- `api/routes/` (system, privacy, admin)
- `api/utils/` (cursor, http_cache, privacy)
- `models/` (IngestionRun, PrivacyRequest)
- `core_infra/upsert_handler.py`

## 🐛 Common Issues & Solutions

### Issue 1: ModuleNotFoundError
```
ImportError: No module named 'services.search_service'
```
**Solution:** Ensure `services/` directory is in the deployment and Python path is correct.

### Issue 2: Database Error
```
ProgrammingError: function similarity(text, text) does not exist
```
**Solution:** Run migrations to install pg_trgm:
```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

### Issue 3: Permission Denied
```
Permission denied: '/var/log/babyshield.log'
```
**Solution:** Fix permissions:
```bash
sudo chown -R www-data:www-data /var/log/babyshield
```

## 🔍 Debugging Commands

Check if service is running:
```bash
# Check process
ps aux | grep babyshield

# Check logs
tail -f /var/log/babyshield/api.log  # or your log location

# Check port
netstat -tlnp | grep 8000  # or your port
```

Test locally first:
```bash
# Start API locally
uvicorn api.main_babyshield:app --reload --port 8000

# Test local endpoint
curl -X POST http://localhost:8000/api/v1/search/advanced \
  -H "Content-Type: application/json" \
  -d '{"product": "test"}'
```

## 📊 Expected Result After Fix

```json
{
  "ok": true,
  "data": {
    "query": {
      "product": "pacifier",
      "limit": 5
    },
    "results": [...],
    "total": 123,
    "page": 1,
    "hasMore": true
  },
  "traceId": "trace_abc123..."
}
```

## ⚡ Quick Deployment Script

Save this as `deploy.sh` on your server:

```bash
#!/bin/bash
echo "🚀 Deploying BabyShield API..."

cd /path/to/babyshield-backend
git pull origin main

echo "📦 Installing dependencies..."
pip install -r requirements.txt

echo "🗄️ Running migrations..."
alembic upgrade head

echo "🔄 Restarting service..."
sudo systemctl restart babyshield

echo "✅ Deployment complete!"

# Test the endpoint
sleep 5
curl -X POST https://babyshield.cureviax.ai/api/v1/search/advanced \
  -H "Content-Type: application/json" \
  -d '{"product": "test", "limit": 1}'
```

Make it executable: `chmod +x deploy.sh`
Run it: `./deploy.sh`

## 🆘 If Still Not Working

1. **Check Docker logs** (if using Docker):
   ```bash
   docker logs babyshield-api
   ```

2. **Check Python path**:
   ```python
   import sys
   print(sys.path)
   ```

3. **Verify file exists on server**:
   ```bash
   ls -la api/main_babyshield.py
   grep -n "search/advanced" api/main_babyshield.py
   ```

4. **Check environment variables**:
   ```bash
   env | grep DATABASE_URL
   env | grep REDIS_URL
   ```

5. **Test import manually**:
   ```python
   from services.search_service import SearchService
   ```

## 📞 Contact for Help

If you need assistance with deployment:
1. Check server logs first
2. Verify all files are present
3. Ensure migrations ran successfully
4. Contact your DevOps team with this document

---

**Priority: HIGH** - The mobile app depends on this endpoint working!

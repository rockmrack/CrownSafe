# Azure Migration: Redis & Celery Configuration Guide

**Date:** October 17, 2025  
**Prepared for:** Azure Infrastructure Migration Team  
**Repository:** BabyShield Backend  

---

## Executive Summary

The BabyShield backend uses Redis for **two primary purposes**:
1. **Caching** (search results, session data, rate limiting)
2. **Celery Message Broker & Result Backend** (background task queue)

**Authentication Method:** Redis URL with embedded password (standard format)  
**Critical:** Both API and Celery worker containers require identical Redis configuration.

---

## Redis Authentication Design

### How Redis Authentication Works

The BabyShield system uses **standard Redis URL format with embedded authentication**:

```bash
# Format:
redis://:password@host:port/db

# Example (no password - localhost):
REDIS_URL=redis://localhost:6379/0

# Example (with password - production/Azure):
REDIS_URL=redis://:MySecureP@ssw0rd@redis-cache.azure.example.com:6379/0

# Azure Redis Cache (typical format):
REDIS_URL=redis://:YourPrimaryAccessKey@your-redis-name.redis.cache.windows.net:6380/0?ssl=true
```

### Important Notes on `REDIS_PASSWORD` Variable

**The `REDIS_PASSWORD` environment variable is ONLY used in `core_infra/redis_manager.py`** for low-level async Redis operations. However, **most of the application uses `REDIS_URL`** directly.

**You do NOT need a separate `REDIS_PASSWORD` variable if you embed the password in the Redis URL.**

---

## Complete Environment Variables for Azure

### Required Environment Variables

Here are **ALL** environment variables related to Redis and Celery that you need to set:

```bash
# ================================
# REDIS CONFIGURATION (PRIMARY)
# ================================
# This is the MAIN Redis URL used by the application
# Include password embedded in URL for Azure Redis Cache
REDIS_URL=redis://:YOUR_AZURE_REDIS_ACCESS_KEY@your-redis-name.redis.cache.windows.net:6380/0?ssl=true

# ================================
# CELERY CONFIGURATION (REQUIRED)
# ================================
# Celery uses these for message broker and result backend
# These should point to the SAME Redis instance
CELERY_BROKER_URL=redis://:YOUR_AZURE_REDIS_ACCESS_KEY@your-redis-name.redis.cache.windows.net:6380/0?ssl=true
CELERY_RESULT_BACKEND=redis://:YOUR_AZURE_REDIS_ACCESS_KEY@your-redis-name.redis.cache.windows.net:6380/0?ssl=true

# ================================
# OPTIONAL: Rate Limiting Redis
# ================================
# If not set, falls back to REDIS_URL
RATE_LIMIT_REDIS_URL=redis://:YOUR_AZURE_REDIS_ACCESS_KEY@your-redis-name.redis.cache.windows.net:6380/0?ssl=true

# ================================
# OPTIONAL: Separate Password (Advanced)
# ================================
# Only needed if using core_infra/redis_manager.py directly with host/port/password separately
# Most components use REDIS_URL instead
REDIS_HOST=your-redis-name.redis.cache.windows.net
REDIS_PORT=6380
REDIS_PASSWORD=YOUR_AZURE_REDIS_ACCESS_KEY
REDIS_DB=0
```

---

## Azure Redis Cache Specific Configuration

### Azure Redis Cache Connection String Format

Azure Redis Cache uses **port 6380 with SSL** by default:

```bash
# Azure Redis Cache Format:
redis://:ACCESS_KEY@CACHE_NAME.redis.cache.windows.net:6380/0?ssl=true

# Where:
# - ACCESS_KEY: Your Primary or Secondary access key from Azure portal
# - CACHE_NAME: Your Azure Redis Cache resource name
# - 6380: Default SSL port (6379 for non-SSL, but SSL is recommended)
# - /0: Database number (Redis supports 0-15)
# - ?ssl=true: Enable SSL/TLS encryption
```

### Getting Your Azure Redis Access Key

1. Go to Azure Portal → Your Redis Cache resource
2. Navigate to **"Access keys"** under Settings
3. Copy the **Primary** or **Secondary** connection string
4. Use the **Access Key** (not the full connection string) in the URL format above

### SSL/TLS Considerations

**Azure Redis Cache requires SSL by default.** The Python `redis` library supports SSL through URL parameters:

```bash
# SSL enabled (recommended for Azure):
redis://:ACCESS_KEY@your-cache.redis.cache.windows.net:6380/0?ssl=true&ssl_cert_reqs=none

# Parameters:
# - ssl=true: Enable SSL/TLS
# - ssl_cert_reqs=none: Skip certificate verification (Azure uses valid certs, but this prevents issues)
```

---

## Complete docker-compose.yml for Azure

Here's a **production-ready docker-compose configuration** for Azure deployment:

```yaml
version: '3.8'

services:
  # BabyShield API
  api:
    image: your-acr-name.azurecr.io/babyshield-backend:latest
    container_name: babyshield-api
    ports:
      - "8001:8001"
    environment:
      # Database (Azure PostgreSQL Flexible Server)
      DATABASE_URL: postgresql://babyshield_user:${DB_PASSWORD}@your-postgres.postgres.database.azure.com:5432/babyshield?sslmode=require
      
      # Redis (Azure Redis Cache)
      REDIS_URL: redis://:${REDIS_ACCESS_KEY}@your-redis.redis.cache.windows.net:6380/0?ssl=true&ssl_cert_reqs=none
      
      # Celery (same Redis instance)
      CELERY_BROKER_URL: redis://:${REDIS_ACCESS_KEY}@your-redis.redis.cache.windows.net:6380/0?ssl=true&ssl_cert_reqs=none
      CELERY_RESULT_BACKEND: redis://:${REDIS_ACCESS_KEY}@your-redis.redis.cache.windows.net:6380/0?ssl=true&ssl_cert_reqs=none
      
      # Rate Limiting (optional, falls back to REDIS_URL)
      RATE_LIMIT_REDIS_URL: redis://:${REDIS_ACCESS_KEY}@your-redis.redis.cache.windows.net:6380/0?ssl=true&ssl_cert_reqs=none
      
      # Application Settings
      SECRET_KEY: ${SECRET_KEY}
      JWT_SECRET_KEY: ${JWT_SECRET_KEY}
      ENVIRONMENT: production
      DEBUG: false
      LOG_LEVEL: INFO
      
      # AWS (if still using S3 for images)
      AWS_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID}
      AWS_SECRET_ACCESS_KEY: ${AWS_SECRET_ACCESS_KEY}
      AWS_DEFAULT_REGION: ${AWS_DEFAULT_REGION:-us-east-1}
      S3_BUCKET: ${S3_BUCKET}
      
      # Firebase (for mobile push notifications)
      FIREBASE_CREDENTIALS_PATH: /app/secrets/serviceAccountKey.json
      
      # Features
      ENABLE_CACHE: "true"
      ENABLE_BACKGROUND_TASKS: "true"
      TEST_MODE: "false"
    
    volumes:
      - ./secrets:/app/secrets:ro
      - ./logs:/app/logs
    
    restart: unless-stopped
    
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/healthz"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # Celery Worker (Background Tasks)
  celery-worker:
    image: your-acr-name.azurecr.io/babyshield-backend:latest
    container_name: babyshield-celery-worker
    command: celery -A core_infra.celery_tasks worker --loglevel=info --pool=solo
    environment:
      # Database (same as API)
      DATABASE_URL: postgresql://babyshield_user:${DB_PASSWORD}@your-postgres.postgres.database.azure.com:5432/babyshield?sslmode=require
      
      # Redis (MUST match API configuration exactly)
      REDIS_URL: redis://:${REDIS_ACCESS_KEY}@your-redis.redis.cache.windows.net:6380/0?ssl=true&ssl_cert_reqs=none
      CELERY_BROKER_URL: redis://:${REDIS_ACCESS_KEY}@your-redis.redis.cache.windows.net:6380/0?ssl=true&ssl_cert_reqs=none
      CELERY_RESULT_BACKEND: redis://:${REDIS_ACCESS_KEY}@your-redis.redis.cache.windows.net:6380/0?ssl=true&ssl_cert_reqs=none
      
      # Application Settings
      SECRET_KEY: ${SECRET_KEY}
      ENVIRONMENT: production
      LOG_LEVEL: INFO
      
      # AWS (if using S3)
      AWS_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID}
      AWS_SECRET_ACCESS_KEY: ${AWS_SECRET_ACCESS_KEY}
      AWS_DEFAULT_REGION: ${AWS_DEFAULT_REGION:-us-east-1}
      S3_BUCKET: ${S3_BUCKET}
    
    volumes:
      - ./logs:/app/logs
    
    restart: unless-stopped
    
    depends_on:
      - api

  # Celery Beat (Scheduled Tasks)
  celery-beat:
    image: your-acr-name.azurecr.io/babyshield-backend:latest
    container_name: babyshield-celery-beat
    command: celery -A core_infra.celery_tasks beat --loglevel=info
    environment:
      # Same configuration as celery-worker
      DATABASE_URL: postgresql://babyshield_user:${DB_PASSWORD}@your-postgres.postgres.database.azure.com:5432/babyshield?sslmode=require
      REDIS_URL: redis://:${REDIS_ACCESS_KEY}@your-redis.redis.cache.windows.net:6380/0?ssl=true&ssl_cert_reqs=none
      CELERY_BROKER_URL: redis://:${REDIS_ACCESS_KEY}@your-redis.redis.cache.windows.net:6380/0?ssl=true&ssl_cert_reqs=none
      CELERY_RESULT_BACKEND: redis://:${REDIS_ACCESS_KEY}@your-redis.redis.cache.windows.net:6380/0?ssl=true&ssl_cert_reqs=none
      SECRET_KEY: ${SECRET_KEY}
      ENVIRONMENT: production
      LOG_LEVEL: INFO
    
    restart: unless-stopped
    
    depends_on:
      - api
```

---

## Environment Variables File (.env)

Create a `.env` file with your Azure-specific values:

```bash
# Azure PostgreSQL
DB_PASSWORD=your_secure_postgres_password

# Azure Redis Cache
REDIS_ACCESS_KEY=your_redis_primary_access_key_from_azure_portal

# Application Secrets
SECRET_KEY=your_jwt_secret_key_change_in_production
JWT_SECRET_KEY=another_secure_jwt_secret

# AWS (if still using S3)
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_DEFAULT_REGION=us-east-1
S3_BUCKET=babyshield-images

# Optional: Firebase (for push notifications)
# FIREBASE_CREDENTIALS_PATH=/app/secrets/serviceAccountKey.json
```

---

## Code Components That Use Redis

### 1. **core_infra/redis_manager.py** (Async Redis)
- Uses: `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`, `REDIS_DB`
- Purpose: Low-level async Redis operations
- **Note:** Most of the application doesn't use this directly

### 2. **core_infra/celery_tasks.py** (Celery)
- Uses: `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`
- Purpose: Background task queue (image processing, notifications)
- **Critical:** Celery worker must have identical Redis config as API

### 3. **core_infra/cache_manager.py** (Application Cache)
- Uses: `REDIS_URL`
- Purpose: Caching search results, product data
- Gracefully degrades if Redis unavailable

### 4. **api/rate_limiting.py** (Rate Limiter)
- Uses: `RATE_LIMIT_REDIS_URL` or `REDIS_URL`
- Purpose: API rate limiting by user/IP
- Optional (disables if Redis unavailable)

### 5. **api/utils/redis_cache.py** (Search Cache)
- Uses: `REDIS_CACHE_URL`, `RATE_LIMIT_REDIS_URL`, or `REDIS_URL`
- Purpose: Fast search result caching
- Optional (falls back to database)

---

## Common Issues and Troubleshooting

### Issue 1: "Celery worker can't connect to Redis"

**Symptoms:**
```
[ERROR] Celery worker: Cannot connect to redis://redis:6379/0
Connection refused
```

**Solutions:**
1. **Check Redis URL format** - Must include password:
   ```bash
   redis://:ACCESS_KEY@host:6380/0?ssl=true
   ```

2. **Verify port** - Azure uses **6380** (SSL), not 6379

3. **Check SSL parameter** - Azure requires `?ssl=true`

4. **Verify both containers have identical config**:
   ```bash
   # Check API container
   docker exec babyshield-api env | grep REDIS
   
   # Check Celery container
   docker exec babyshield-celery-worker env | grep REDIS
   
   # They MUST match exactly
   ```

### Issue 2: "SSL certificate verification failed"

**Solution:** Add `ssl_cert_reqs=none` to Redis URL:
```bash
redis://:KEY@host:6380/0?ssl=true&ssl_cert_reqs=none
```

### Issue 3: "Authentication failed" or "NOAUTH"

**Symptoms:**
```
redis.exceptions.AuthenticationError: Authentication failed
```

**Solutions:**
1. Check access key is correct (copy from Azure Portal)
2. Ensure `:` before password in URL: `redis://:PASSWORD@host`
3. URL-encode password if it contains special characters

### Issue 4: Different Redis databases

The application uses different Redis databases for different purposes:

```bash
# Cache and general use
REDIS_URL=redis://:KEY@host:6380/0?ssl=true  # Database 0

# Celery broker
CELERY_BROKER_URL=redis://:KEY@host:6380/1?ssl=true  # Database 1 (optional)

# Celery results
CELERY_RESULT_BACKEND=redis://:KEY@host:6380/2?ssl=true  # Database 2 (optional)
```

**Recommendation for Azure:** Use **Database 0 for everything** to simplify configuration. Azure Redis Cache supports databases 0-15.

---

## Testing Redis Connectivity

### Test 1: Direct Redis Connection (from container)

```bash
# Test from API container
docker exec -it babyshield-api python -c "
import redis
import os
r = redis.from_url(os.getenv('REDIS_URL'))
print('PING response:', r.ping())
r.set('test_key', 'test_value')
print('GET test_key:', r.get('test_key'))
"
```

### Test 2: Celery Worker Connection

```bash
# Test from Celery container
docker exec -it babyshield-celery-worker python -c "
from celery import Celery
import os
app = Celery('test', broker=os.getenv('CELERY_BROKER_URL'))
result = app.control.inspect().stats()
print('Celery connection OK:', result is not None)
"
```

### Test 3: Using redis-cli

```bash
# Connect with redis-cli (replace with your values)
redis-cli -h your-redis.redis.cache.windows.net -p 6380 --tls -a YOUR_ACCESS_KEY

# Once connected:
PING
SET test_key "hello from Azure"
GET test_key
```

---

## Recommended Azure Redis Cache Configuration

### Pricing Tier Recommendations

- **Development/Testing:** Basic C1 (1 GB, $36/month)
- **Production:** Standard C2 or C3 (2.5-6 GB, replicated, $100-200/month)
- **High Traffic:** Premium P1+ (6+ GB, clustering, persistence)

### Important Settings in Azure Portal

1. **Access keys:** Use **Primary key** for production, rotate to Secondary during maintenance
2. **SSL Port:** Use **6380** (default SSL port)
3. **Non-SSL Port:** Disabled (recommended for security)
4. **Firewall:** Configure to allow your Azure Container Instances/App Service IPs
5. **Advanced settings:**
   - `maxmemory-policy`: **allkeys-lru** (recommended for cache)
   - `notify-keyspace-events`: **Ex** (for key expiration events)

---

## Minimal Environment Variables (Quick Start)

If you want to get started quickly, here are the **absolute minimum** variables needed:

```bash
# .env file for Azure deployment
DATABASE_URL=postgresql://user:pass@your-postgres.postgres.database.azure.com:5432/babyshield?sslmode=require
REDIS_URL=redis://:YOUR_ACCESS_KEY@your-redis.redis.cache.windows.net:6380/0?ssl=true&ssl_cert_reqs=none
CELERY_BROKER_URL=redis://:YOUR_ACCESS_KEY@your-redis.redis.cache.windows.net:6380/0?ssl=true&ssl_cert_reqs=none
CELERY_RESULT_BACKEND=redis://:YOUR_ACCESS_KEY@your-redis.redis.cache.windows.net:6380/0?ssl=true&ssl_cert_reqs=none
SECRET_KEY=change-this-to-secure-random-string
JWT_SECRET_KEY=change-this-to-another-secure-random-string
```

---

## Code References

The following files contain Redis/Celery configuration:

- **Main Celery config:** `core_infra/celery_tasks.py` (line 34-39)
- **Redis manager:** `core_infra/redis_manager.py` (line 25-28)
- **Cache manager:** `core_infra/cache_manager.py` (line 75-86)
- **Rate limiter:** `api/rate_limiting.py` (line 50-52)
- **Docker compose:** `docker-compose.yml` (line 43, 77-79, 97-99)
- **Config class:** `core_infra/config.py` (line 27-28, 50-51)

---

## Summary Checklist for Azure Migration

- [ ] Create Azure Redis Cache resource (Standard tier recommended)
- [ ] Copy Primary Access Key from Azure Portal
- [ ] Set `REDIS_URL` with format: `redis://:KEY@HOST:6380/0?ssl=true&ssl_cert_reqs=none`
- [ ] Set `CELERY_BROKER_URL` (same as REDIS_URL)
- [ ] Set `CELERY_RESULT_BACKEND` (same as REDIS_URL)
- [ ] Configure Azure firewall to allow container IPs
- [ ] Test Redis connectivity with `redis-cli`
- [ ] Deploy API container with Redis environment variables
- [ ] Deploy Celery worker container with **identical** Redis configuration
- [ ] Verify Celery worker connects: `docker logs babyshield-celery-worker`
- [ ] Test background task: Submit image processing job via API
- [ ] Monitor Redis metrics in Azure Portal

---

## Additional Resources

- **Azure Redis Cache Documentation:** https://docs.microsoft.com/azure/azure-cache-for-redis/
- **Python Redis Library:** https://redis-py.readthedocs.io/
- **Celery Documentation:** https://docs.celeryproject.org/
- **BabyShield CONTRIBUTING.md:** See repository for development guidelines

---

## Contact

If you encounter issues not covered in this guide:

- **Repository:** https://github.com/BabyShield/babyshield-backend
- **Issues:** https://github.com/BabyShield/babyshield-backend/issues
- **Security:** security@babyshield.dev
- **Development:** dev@babyshield.dev

---

**Document Version:** 1.0  
**Last Updated:** October 17, 2025  
**Maintained By:** BabyShield Development Team

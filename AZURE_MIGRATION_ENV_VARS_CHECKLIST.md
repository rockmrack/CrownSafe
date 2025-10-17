# Azure Migration: Complete Environment Variables Checklist

**Date:** October 17, 2025  
**Purpose:** Comprehensive list of ALL environment variables for API and Celery Worker  
**Migration Target:** Azure Container Instances / Azure App Service  

---

## ✅ Default Branch Confirmation

**Question:** *"Is the development branch the default one in the backend repo? Can I use for CI/CD work?"*

**Answer:**
- **Default Branch:** `main` (confirmed via `gh repo view`)
- **Active Branch:** `main` (production)
- **Development Branch:** `development` (exists but NOT default)
- **For CI/CD:** Use `main` branch - it's the default and production branch
- **Branch Protection:** `main` is protected, requires pull requests

---

## 🔑 CRITICAL: Environment Variables Both API and Celery Worker Need

Both containers **MUST have IDENTICAL values** for these variables:

### **Database (Required)**
```bash
DATABASE_URL=postgresql://user:pass@host.postgres.database.azure.com:5432/babyshield?sslmode=require
```

### **Redis & Celery (Required)**
```bash
REDIS_URL=redis://:ACCESS_KEY@name.redis.cache.windows.net:6380/0?ssl=true&ssl_cert_reqs=none
CELERY_BROKER_URL=redis://:ACCESS_KEY@name.redis.cache.windows.net:6380/0?ssl=true&ssl_cert_reqs=none
CELERY_RESULT_BACKEND=redis://:ACCESS_KEY@name.redis.cache.windows.net:6380/0?ssl=true&ssl_cert_reqs=none
```

### **Security (Required)**
```bash
SECRET_KEY=your-application-secret-key-minimum-32-characters
JWT_SECRET_KEY=your-jwt-signing-key-minimum-32-characters
```

### **Environment Control (Required)**
```bash
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
```

---

## 📋 Complete Environment Variables by Category

### 1. **Core Application Settings**

#### API Container
```bash
# Server Configuration
HOST=0.0.0.0
PORT=8001
API_HOST=0.0.0.0
API_PORT=8001
RELOAD=false

# Environment
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
TEST_MODE=false
```

#### Celery Worker
```bash
# Environment (same as API)
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
```

---

### 2. **Database Configuration**

#### Both Containers (MUST BE IDENTICAL)
```bash
# Primary Database URL
DATABASE_URL=postgresql://babyshield_user:PASSWORD@your-postgres.postgres.database.azure.com:5432/babyshield?sslmode=require

# Connection Pool Settings (Optional - has defaults)
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600
DATABASE_ECHO=false

# Alternative format (if not using DATABASE_URL)
DB_HOST=your-postgres.postgres.database.azure.com
DB_NAME=babyshield
DB_USER=babyshield_user
DB_PASSWORD=your-secure-password
```

---

### 3. **Redis & Caching**

#### Both Containers (MUST BE IDENTICAL)
```bash
# Primary Redis URL
REDIS_URL=redis://:ACCESS_KEY@your-redis.redis.cache.windows.net:6380/0?ssl=true&ssl_cert_reqs=none

# Alternative Redis Connection (if using host/port/password format)
REDIS_HOST=your-redis.redis.cache.windows.net
REDIS_PORT=6380
REDIS_PASSWORD=your-azure-redis-access-key
REDIS_DB=0
REDIS_MAX_CONNECTIONS=20
REDIS_CONNECTION_TIMEOUT=5
REDIS_RETRY_ATTEMPTS=3
REDIS_RETRY_DELAY=0.5

# Rate Limiting Redis (Optional - falls back to REDIS_URL)
RATE_LIMIT_REDIS_URL=redis://:ACCESS_KEY@your-redis.redis.cache.windows.net:6380/0?ssl=true&ssl_cert_reqs=none

# Cache Settings (Optional)
REDIS_CACHE_TTL=3600
SEARCH_CACHE_TTL=60
SEARCH_CACHE_ENABLED=true
ENABLE_CACHE=true
DISABLE_REDIS_WARNING=false
```

---

### 4. **Celery Configuration**

#### Both Containers (MUST BE IDENTICAL)
```bash
# Celery Broker & Backend
CELERY_BROKER_URL=redis://:ACCESS_KEY@your-redis.redis.cache.windows.net:6380/0?ssl=true&ssl_cert_reqs=none
CELERY_RESULT_BACKEND=redis://:ACCESS_KEY@your-redis.redis.cache.windows.net:6380/0?ssl=true&ssl_cert_reqs=none

# Celery Worker Settings (Optional - has defaults)
ENABLE_BACKGROUND_TASKS=true
```

---

### 5. **Authentication & Security**

#### Both Containers (MUST BE IDENTICAL)
```bash
# JWT Tokens (Required)
SECRET_KEY=your-application-secret-key-minimum-32-characters-change-in-production
JWT_SECRET_KEY=your-jwt-signing-key-minimum-32-characters-change-in-production

# JWT Algorithm (Optional - defaults to HS256)
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

---

### 6. **AWS Services (S3 for Images)**

#### Both Containers (if using S3 for image storage)
```bash
# AWS Credentials
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_DEFAULT_REGION=us-east-1
AWS_REGION=us-east-1

# S3 Buckets
S3_BUCKET=babyshield-images
S3_UPLOAD_BUCKET=babyshield-images
S3_BUCKET_REGION=us-east-1

# Report Storage (Optional)
REPORTS_STORAGE=s3
DELETE_LOCAL_AFTER_S3=true
```

**Note:** If migrating to Azure Blob Storage, these will need to be replaced with Azure Storage equivalents.

---

### 7. **Firebase (Push Notifications)**

#### Both Containers (if using Firebase for mobile notifications)
```bash
# Firebase Credentials
FIREBASE_CREDENTIALS_PATH=/app/secrets/serviceAccountKey.json
```

**Important:** Mount the Firebase service account JSON file as a secret/volume at this path.

---

### 8. **Third-Party API Keys**

#### API Container Only (Celery may need some for background tasks)
```bash
# OpenAI (for AI features - Visual Search, Hazard Analysis)
OPENAI_API_KEY=sk-your-openai-api-key
OPENAI_TIMEOUT=10

# Stripe (for payments/subscriptions)
STRIPE_SECRET_KEY=sk_live_your-stripe-secret-key

# Mixpanel (for analytics)
MIXPANEL_PROJECT_TOKEN=your-mixpanel-token

# UPC Database (for product identification)
USE_TRIAL_UPCITEMDB=false

# FDA API (for recall data)
FDA_API_KEY=your-fda-api-key

# NCBI/PubMed (for research agent)
NCBI_API_KEY=your-ncbi-api-key
PUBMED_USE_MOCK=false
```

#### Celery Worker (needs these if processing images/AI tasks)
```bash
# OpenAI (Required for Visual Agent tasks)
OPENAI_API_KEY=sk-your-openai-api-key
OPENAI_TIMEOUT=10

# AWS (Required for S3 image processing)
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_REGION=us-east-1
S3_BUCKET=babyshield-images
```

---

### 9. **Email/SMTP (for feedback/support)**

#### API Container Only
```bash
# SMTP Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=support@babyshield.app
SMTP_PASSWORD=your-smtp-password

# Support Email Addresses
SUPPORT_MAILBOX=support@babyshield.app
ESCALATION_EMAIL=escalation@babyshield.app
SECURITY_EMAIL=security@babyshield.app
```

---

### 10. **File Upload & Storage**

#### API Container
```bash
# Local File Storage
UPLOAD_DIR=/app/uploads
MAX_FILE_SIZE=52428800
MODEL_CACHE_DIR=/app/models
REPORTS_DIR=/app/generated_reports
```

---

### 11. **Rate Limiting**

#### API Container Only
```bash
# Rate Limiter Settings
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_PERIOD=60
```

---

### 12. **Monitoring & Metrics**

#### API Container
```bash
# Metrics/Prometheus
ENABLE_METRICS=false
METRICS_PORT=9090

# Sentry Error Tracking
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
SENTRY_TRACES_SAMPLE_RATE=0.1
SENTRY_PROFILES_SAMPLE_RATE=0.1
```

---

### 13. **Feature Flags**

#### Both Containers (for consistency)
```bash
# Core Features
ENABLE_CACHE=true
ENABLE_BACKGROUND_TASKS=true

# OCR Features
ENABLE_TESSERACT=false
ENABLE_EASYOCR=false
ENABLE_DATAMATRIX=false
ENABLE_RECEIPT_VALIDATION=false

# Product Identification
USE_MOCK_INGREDIENT_DB=false

# Chat Features
BS_FEATURE_CHAT_ENABLED=true
BS_FEATURE_CHAT_ROLLOUT_PCT=1.0

# Development/Testing
USE_TRIAL_UPCITEMDB=false
PUBMED_USE_MOCK=false
```

---

### 14. **Agent Configuration (Advanced)**

#### Both Containers (if using RossNet agents)
```bash
# MCP Server
MCP_SERVER_URL=ws://127.0.0.1:8001

# Report Builder Agent
REPORTBUILDER_MAX_RETRIES=10
REPORTBUILDER_RETRY_DELAY=2.0
REPORTBUILDER_MAX_RETRY_DELAY=60.0
REPORTBUILDER_HEALTH_CHECK=30
REPORTBUILDER_STARTUP_DELAY=5.0

# HTML Renderer
HTML_RENDERER=weasyprint
```

---

### 15. **Entitlements (Optional)**

#### API Container
```bash
# User Entitlements (comma-separated user IDs)
ENTITLEMENTS_ALLOWLIST=999,1234,5678

# Available Features (comma-separated)
ENTITLEMENTS_FEATURES=safety.check,premium.report,visual.search
```

---

## 🎯 Minimal Production Configuration (Quick Start)

If you want to get started with the **absolute minimum** variables:

### API Container
```bash
# Core
DATABASE_URL=postgresql://user:pass@host.postgres.database.azure.com:5432/babyshield?sslmode=require
SECRET_KEY=your-secret-key-32-chars-min
JWT_SECRET_KEY=your-jwt-secret-32-chars-min
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Redis & Celery
REDIS_URL=redis://:KEY@redis.redis.cache.windows.net:6380/0?ssl=true&ssl_cert_reqs=none
CELERY_BROKER_URL=redis://:KEY@redis.redis.cache.windows.net:6380/0?ssl=true&ssl_cert_reqs=none
CELERY_RESULT_BACKEND=redis://:KEY@redis.redis.cache.windows.net:6380/0?ssl=true&ssl_cert_reqs=none

# Optional but Recommended
ENABLE_CACHE=true
ENABLE_BACKGROUND_TASKS=true
```

### Celery Worker Container
```bash
# Core (MUST match API)
DATABASE_URL=postgresql://user:pass@host.postgres.database.azure.com:5432/babyshield?sslmode=require
SECRET_KEY=your-secret-key-32-chars-min
JWT_SECRET_KEY=your-jwt-secret-32-chars-min
ENVIRONMENT=production
LOG_LEVEL=INFO

# Redis & Celery (MUST match API)
REDIS_URL=redis://:KEY@redis.redis.cache.windows.net:6380/0?ssl=true&ssl_cert_reqs=none
CELERY_BROKER_URL=redis://:KEY@redis.redis.cache.windows.net:6380/0?ssl=true&ssl_cert_reqs=none
CELERY_RESULT_BACKEND=redis://:KEY@redis.redis.cache.windows.net:6380/0?ssl=true&ssl_cert_reqs=none

# AWS (if processing images)
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
AWS_REGION=us-east-1
S3_BUCKET=babyshield-images

# OpenAI (if processing AI tasks)
OPENAI_API_KEY=sk-your-openai-key
```

---

## ⚠️ Common Mistakes to Avoid

### 1. **Different Redis URLs**
❌ **WRONG:**
- API: `REDIS_URL=redis://redis-prod:6380/0`
- Celery: `REDIS_URL=redis://redis-worker:6380/0`

✅ **CORRECT:**
- Both use: `REDIS_URL=redis://:KEY@same-redis.redis.cache.windows.net:6380/0?ssl=true`

### 2. **Missing SSL Parameter for Azure Redis**
❌ **WRONG:**
```bash
REDIS_URL=redis://:KEY@redis.redis.cache.windows.net:6379/0
```

✅ **CORRECT:**
```bash
REDIS_URL=redis://:KEY@redis.redis.cache.windows.net:6380/0?ssl=true&ssl_cert_reqs=none
```

### 3. **Different SECRET_KEY Values**
❌ **WRONG:**
- API: `SECRET_KEY=api-secret-123`
- Celery: `SECRET_KEY=worker-secret-456`

✅ **CORRECT:**
- Both use: `SECRET_KEY=same-secret-key-for-both-containers`

### 4. **Missing DATABASE_URL in Celery**
❌ **WRONG:**
- API has `DATABASE_URL`, Celery doesn't

✅ **CORRECT:**
- Both containers have identical `DATABASE_URL`

---

## 🧪 Testing Environment Variables

### Test 1: Verify API Container Has All Variables
```bash
# SSH/exec into API container
docker exec -it babyshield-api env | sort | grep -E "DATABASE|REDIS|CELERY|SECRET"
```

### Test 2: Verify Celery Worker Has All Variables
```bash
# SSH/exec into Celery container
docker exec -it babyshield-celery-worker env | sort | grep -E "DATABASE|REDIS|CELERY|SECRET"
```

### Test 3: Compare API vs Celery (Should Be Identical)
```bash
# API
docker exec babyshield-api env | grep -E "REDIS_URL|CELERY|DATABASE_URL|SECRET_KEY" | sort > api-env.txt

# Celery
docker exec babyshield-celery-worker env | grep -E "REDIS_URL|CELERY|DATABASE_URL|SECRET_KEY" | sort > celery-env.txt

# Compare
diff api-env.txt celery-env.txt
# Should show NO differences for critical variables
```

---

## 📝 Environment File Templates

### `.env` File for Azure (Use Azure Key Vault in production)

```bash
# ================================
# CORE APPLICATION
# ================================
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
HOST=0.0.0.0
PORT=8001

# ================================
# DATABASE (Azure PostgreSQL)
# ================================
DATABASE_URL=postgresql://babyshield_user:${DB_PASSWORD}@your-postgres.postgres.database.azure.com:5432/babyshield?sslmode=require
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40

# ================================
# REDIS (Azure Redis Cache)
# ================================
REDIS_URL=redis://:${REDIS_ACCESS_KEY}@your-redis.redis.cache.windows.net:6380/0?ssl=true&ssl_cert_reqs=none

# ================================
# CELERY (Same Redis)
# ================================
CELERY_BROKER_URL=${REDIS_URL}
CELERY_RESULT_BACKEND=${REDIS_URL}
ENABLE_BACKGROUND_TASKS=true

# ================================
# SECURITY
# ================================
SECRET_KEY=${SECRET_KEY}
JWT_SECRET_KEY=${JWT_SECRET_KEY}

# ================================
# THIRD-PARTY SERVICES
# ================================
OPENAI_API_KEY=${OPENAI_API_KEY}
AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
S3_BUCKET=babyshield-images
AWS_REGION=us-east-1

# ================================
# FEATURES
# ================================
ENABLE_CACHE=true
SEARCH_CACHE_ENABLED=true
RATE_LIMIT_ENABLED=true
```

---

## 🔐 Azure Key Vault Integration (Recommended)

For production, use **Azure Key Vault** to manage secrets:

```bash
# Reference secrets from Azure Key Vault
DATABASE_URL=@Microsoft.KeyVault(SecretUri=https://your-vault.vault.azure.net/secrets/database-url/)
REDIS_URL=@Microsoft.KeyVault(SecretUri=https://your-vault.vault.azure.net/secrets/redis-url/)
SECRET_KEY=@Microsoft.KeyVault(SecretUri=https://your-vault.vault.azure.net/secrets/app-secret-key/)
JWT_SECRET_KEY=@Microsoft.KeyVault(SecretUri=https://your-vault.vault.azure.net/secrets/jwt-secret-key/)
OPENAI_API_KEY=@Microsoft.KeyVault(SecretUri=https://your-vault.vault.azure.net/secrets/openai-api-key/)
```

---

## 📊 Variables Summary Table

| Variable                    | API | Celery | Required    | Category   |
| --------------------------- | --- | ------ | ----------- | ---------- |
| `DATABASE_URL`              | ✅   | ✅      | **YES**     | Database   |
| `REDIS_URL`                 | ✅   | ✅      | **YES**     | Redis      |
| `CELERY_BROKER_URL`         | ✅   | ✅      | **YES**     | Celery     |
| `CELERY_RESULT_BACKEND`     | ✅   | ✅      | **YES**     | Celery     |
| `SECRET_KEY`                | ✅   | ✅      | **YES**     | Security   |
| `JWT_SECRET_KEY`            | ✅   | ✅      | **YES**     | Security   |
| `ENVIRONMENT`               | ✅   | ✅      | **YES**     | Core       |
| `LOG_LEVEL`                 | ✅   | ✅      | **YES**     | Core       |
| `OPENAI_API_KEY`            | ✅   | ✅*     | Conditional | AI/ML      |
| `AWS_ACCESS_KEY_ID`         | ✅   | ✅*     | Conditional | AWS        |
| `AWS_SECRET_ACCESS_KEY`     | ✅   | ✅*     | Conditional | AWS        |
| `S3_BUCKET`                 | ✅   | ✅*     | Conditional | AWS        |
| `FIREBASE_CREDENTIALS_PATH` | ✅   | ❌      | No          | Firebase   |
| `STRIPE_SECRET_KEY`         | ✅   | ❌      | No          | Payments   |
| `SMTP_HOST`                 | ✅   | ❌      | No          | Email      |
| `SENTRY_DSN`                | ✅   | ✅      | No          | Monitoring |

**Legend:**
- ✅ = Required for this container
- ✅* = Required if using the feature (image processing, AI tasks)
- ❌ = Not needed for this container

---

## 🚀 Deployment Checklist

- [ ] Azure PostgreSQL database created
- [ ] Azure Redis Cache created (Standard tier or higher)
- [ ] Redis access key copied from Azure Portal
- [ ] All critical variables set in Azure App Service/Container Instances
- [ ] **API and Celery have IDENTICAL values for critical variables**
- [ ] Azure Key Vault configured (recommended)
- [ ] Secrets mounted as files (for Firebase credentials)
- [ ] Port 6380 used for Redis (not 6379)
- [ ] `?ssl=true&ssl_cert_reqs=none` added to Redis URLs
- [ ] Database connection string includes `?sslmode=require`
- [ ] Test API health endpoint: `/healthz`
- [ ] Test API readiness endpoint: `/api/v1/readyz`
- [ ] Verify Celery worker logs show successful Redis connection
- [ ] Submit test background task via API
- [ ] Monitor Azure Redis Cache metrics

---

## 🆘 Troubleshooting Quick Reference

### "Celery can't connect to Redis"
✅ Check: Both containers have identical `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`  
✅ Check: Using port 6380 (not 6379)  
✅ Check: `?ssl=true` is in Redis URL

### "Authentication failed" 
✅ Check: Access key is correct (copy from Azure Portal)  
✅ Check: Format is `redis://:ACCESS_KEY@host` (note the `:` before key)

### "Database connection failed"
✅ Check: `?sslmode=require` is in DATABASE_URL  
✅ Check: Azure PostgreSQL firewall allows container IPs  
✅ Check: Both API and Celery have identical DATABASE_URL

### "JWT token verification failed"
✅ Check: Both API and Celery have identical `SECRET_KEY` and `JWT_SECRET_KEY`

---

## 📚 References

- **Main Configuration:** `core_infra/config.py`
- **Celery Setup:** `core_infra/celery_tasks.py`
- **Redis Manager:** `core_infra/redis_manager.py`
- **Docker Compose:** `docker-compose.yml`
- **Example Environment:** `.env.example`

---

## Branch Information Answer

**Question:** *"Is the development branch the default one in the backend repo? Can I use for CI/CD work? Or is it still main?"*

**Answer:**
- ✅ **Default Branch:** `main` (confirmed)
- ✅ **Use for CI/CD:** `main` branch
- ✅ **Production Branch:** `main`
- ⚠️ **Development Branch:** `development` exists but is NOT the default
- 🔒 **Branch Protection:** `main` is protected, requires pull requests

**Recommendation:** Use `main` branch for all CI/CD workflows. It's the default, production-ready, and protected branch.

---

**Document Version:** 1.0  
**Last Updated:** October 17, 2025  
**Prepared By:** BabyShield Development Team

# ✅ Docker Deployment Verification for BabyShield

## Your Commands Are CORRECT! ✅

```bash
docker build --no-cache -f Dockerfile.backend -t babyshield-backend:api-v1 .
aws ecr get-login-password --region eu-north-1 | docker login --username AWS --password-stdin 180703226577.dkr.ecr.eu-north-1.amazonaws.com
docker tag babyshield-backend:api-v1 180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:api-v1
docker push 180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:api-v1
```

## ⚠️ BUT FIRST - Update Your Dockerfile!

Your current `Dockerfile.backend` needs system dependencies for psycopg2. Update it:

```dockerfile
# Use Python 3.11 slim as the base image
FROM python:3.11-slim

# Set working directory
WORKDIR /usr/src/app

# Environment settings
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies for psycopg2 and other packages
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    postgresql-client \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Create necessary directories
RUN mkdir -p /usr/src/app/logs \
    && mkdir -p /usr/src/app/static/admin \
    && mkdir -p /usr/src/app/static/legal

# Run database migrations (optional - can be done separately)
# RUN alembic upgrade head

# Expose port for health checks (FastAPI or other HTTP server)
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/api/v1/healthz || exit 1

# Start FastAPI with Uvicorn
CMD ["uvicorn", "api.main_babyshield:app", "--host", "0.0.0.0", "--port", "8001"]
```

## 📋 Pre-Deployment Checklist

### 1. Files to Verify Are Included
```bash
# Check these critical files exist
ls -la services/search_service.py
ls -la api/models/search_validation.py
ls -la api/middleware/correlation.py
ls -la api/routes/system.py
ls -la core_infra/upsert_handler.py
```

### 2. Test Build Locally First
```bash
# Build locally to catch errors
docker build --no-cache -f Dockerfile.backend -t babyshield-backend:test .

# Run locally to test
docker run -p 8001:8001 \
  -e DATABASE_URL="your-db-url" \
  -e REDIS_URL="your-redis-url" \
  -e SECRET_KEY="your-secret" \
  babyshield-backend:test
```

### 3. Environment Variables for ECS/Fargate
Make sure your ECS task definition has:
```json
{
  "environment": [
    {"name": "DATABASE_URL", "value": "postgresql://..."},
    {"name": "REDIS_URL", "value": "redis://..."},
    {"name": "SECRET_KEY", "value": "..."},
    {"name": "ADMIN_API_KEY", "value": "..."},
    {"name": "AWS_REGION", "value": "eu-north-1"},
    {"name": "CORS_ALLOWED_ORIGINS", "value": "https://babyshield.cureviax.ai,https://app.babyshield.app"}
  ]
}
```

## 🚀 Complete Deployment Process

### Step 1: Update Dockerfile (if needed)
```bash
# Copy the updated Dockerfile content above
```

### Step 2: Build & Push (Your Commands)
```bash
# 1. Build with no cache
docker build --no-cache -f Dockerfile.backend -t babyshield-backend:api-v1 .

# 2. Login to ECR
aws ecr get-login-password --region eu-north-1 | docker login --username AWS --password-stdin 180703226577.dkr.ecr.eu-north-1.amazonaws.com

# 3. Tag for ECR
docker tag babyshield-backend:api-v1 180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:api-v1

# 4. Push to ECR
docker push 180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:api-v1
```

### Step 3: Update ECS Service
```bash
# Force new deployment
aws ecs update-service \
  --cluster your-cluster-name \
  --service your-service-name \
  --force-new-deployment \
  --region eu-north-1
```

### Step 4: Run Database Migrations
```bash
# Option A: Run in ECS task
aws ecs run-task \
  --cluster your-cluster-name \
  --task-definition your-task-def \
  --overrides '{"containerOverrides":[{"name":"babyshield-backend","command":["alembic","upgrade","head"]}]}' \
  --region eu-north-1

# Option B: Connect to RDS and run manually
docker run --rm \
  -e DATABASE_URL="your-rds-url" \
  180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:api-v1 \
  alembic upgrade head
```

### Step 5: Verify Deployment
```bash
# Check service status
aws ecs describe-services \
  --cluster your-cluster-name \
  --services your-service-name \
  --region eu-north-1

# Test endpoints
curl https://babyshield.cureviax.ai/api/v1/healthz
curl -X POST https://babyshield.cureviax.ai/api/v1/search/advanced \
  -H "Content-Type: application/json" \
  -d '{"product": "pacifier", "limit": 5}'
```

## 🔍 Troubleshooting

### If endpoints still return 404:
1. **Check CloudWatch logs**:
```bash
aws logs tail /ecs/your-service --follow --region eu-north-1
```

2. **Verify task is running latest image**:
```bash
aws ecs describe-tasks \
  --cluster your-cluster \
  --tasks $(aws ecs list-tasks --cluster your-cluster --service your-service --query 'taskArns[0]' --output text) \
  --region eu-north-1 \
  --query 'tasks[0].containers[0].image'
```

3. **Check ALB target health**:
```bash
aws elbv2 describe-target-health \
  --target-group-arn your-target-group-arn \
  --region eu-north-1
```

## ✅ Expected Results After Deployment

1. **Health Check**: 
   ```json
   {"status":"healthy","database":"connected","redis":"connected","version":"1.0.0"}
   ```

2. **Search Endpoint**:
   ```json
   {
     "ok": true,
     "data": {
       "query": {"product": "pacifier", "limit": 5},
       "results": [...],
       "total": 45,
       "page": 1
     },
     "traceId": "trace_abc123"
   }
   ```

## 🎯 Summary

Your Docker commands are **PERFECT**! Just:
1. ✅ Update Dockerfile to include system dependencies
2. ✅ Build and push (your commands)
3. ✅ Update ECS service
4. ✅ Run database migrations
5. ✅ Test the endpoints

The deployment will be successful! 🚀

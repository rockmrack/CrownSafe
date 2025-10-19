# AWS Deployment Guide - BabyShield Backend

**Date:** October 17, 2025  
**Target:** AWS ECS with ECR Registry  
**Region:** eu-north-1 (Stockholm)  

---

## 🚀 Current AWS Deployment Process

### Overview

BabyShield Backend is deployed to **AWS ECS (Elastic Container Service)** using Docker images stored in **AWS ECR (Elastic Container Registry)**.

**AWS Infrastructure:**
- **ECR Registry:** `180703226577.dkr.ecr.eu-north-1.amazonaws.com`
- **ECR Repository:** `babyshield-backend`
- **ECS Cluster:** `babyshield-cluster`
- **ECS Service:** `babyshield-backend-task-service-0l41s2a9`
- **Task Definition:** `babyshield-backend-task`
- **Region:** `eu-north-1` (Stockholm, Sweden)

---

## 📋 Manual Deployment Steps (Your Current Process)

### Step 1: Build Docker Image

```powershell
# Build the production-ready Docker image
docker build -f Dockerfile.final -t babyshield-backend:fixed-v3 .
```

**Important Notes:**
- Uses `Dockerfile.final` (not `Dockerfile`)
- `Dockerfile.final` is optimized for production (smaller, no dev dependencies)
- Build on `linux/amd64` platform (ECS requirement)

### Step 2: Login to AWS ECR

```powershell
# Authenticate Docker to AWS ECR
aws ecr get-login-password --region eu-north-1 | docker login --username AWS --password-stdin 180703226577.dkr.ecr.eu-north-1.amazonaws.com
```

**What this does:**
- Gets temporary ECR login credentials from AWS
- Authenticates Docker CLI to push images to your ECR registry
- Credentials expire after 12 hours

### Step 3: Tag Docker Image for ECR

```powershell
# Tag the local image for ECR repository
docker tag babyshield-backend:fixed-v3 180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:production-fixed-20250901
```

**Tag Format:**
```
<registry>/<repository>:<tag>
180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:production-fixed-20250901
```

### Step 4: Push Image to ECR

```powershell
# Upload the image to AWS ECR
docker push 180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:production-fixed-20250901
```

**What happens:**
- Docker uploads the image layers to AWS ECR
- Image becomes available for ECS deployment
- ECS can now pull this image to run containers

### Step 5: Update ECS Service (Manual)

After pushing to ECR, you need to update the ECS service to use the new image:

```powershell
# Force new deployment with latest image
aws ecs update-service `
    --cluster babyshield-cluster `
    --service babyshield-backend-task-service-0l41s2a9 `
    --force-new-deployment `
    --region eu-north-1
```

**Or** update the task definition to use the specific image tag (more controlled):

```powershell
# Get current task definition
aws ecs describe-task-definition `
    --task-definition babyshield-backend-task `
    --region eu-north-1 > current-task-def.json

# Edit the image in containerDefinitions[0].image to:
# 180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:production-fixed-20250901

# Register new task definition (after editing JSON)
aws ecs register-task-definition --cli-input-json file://updated-task-def.json --region eu-north-1

# Update service to use new task definition
aws ecs update-service `
    --cluster babyshield-cluster `
    --service babyshield-backend-task-service-0l41s2a9 `
    --task-definition babyshield-backend-task:NEW_REVISION `
    --region eu-north-1
```

---

## 🔧 Automated Deployment Script (Your Production Script)

You have an existing production deployment script: `deploy_production_hotfix.ps1`

**What it does:**
1. ✅ Builds Docker image with timestamp tag
2. ✅ Tags for ECR (both specific version and `latest`)
3. ✅ Logs in to ECR
4. ✅ Pushes images to ECR
5. ✅ Gets image digest
6. ✅ Forces new ECS deployment

**Usage:**
```powershell
.\deploy_production_hotfix.ps1
```

**Key variables in script:**
- `$ECR_REGISTRY` = `180703226577.dkr.ecr.eu-north-1.amazonaws.com`
- `$ECR_REPO` = `babyshield-backend`
- `$AWS_REGION` = `eu-north-1`
- `$ECS_CLUSTER` = `babyshield-cluster`
- `$ECS_SERVICE` = `babyshield-backend-task-service-0l41s2a9`

---

## ⚙️ Environment Variables in AWS ECS

### How Environment Variables Are Configured

Environment variables are **NOT** in a `.env` file in production. They are configured in the **ECS Task Definition**.

**To view current production environment variables:**
```powershell
aws ecs describe-task-definition `
    --task-definition babyshield-backend-task `
    --region eu-north-1 `
    --query 'taskDefinition.containerDefinitions[0].environment' `
    --output table
```

**To add/update environment variables:**

You have a script: `enable_chat_production.ps1` that shows the pattern:

1. Get current task definition
2. Modify the `environment` array in `containerDefinitions[0]`
3. Remove non-registerable fields
4. Register new task definition revision
5. Update ECS service to use new revision

---

## 📊 Current Production Environment Variables (Based on Your Scripts)

Your production environment variables are configured in the ECS Task Definition. Based on your deployment scripts, these are the key ones:

### Core Application
```
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
```

### Database (RDS PostgreSQL)
```
DATABASE_URL=postgresql://username:password@babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com:5432/babyshield_db
DB_NAME=babyshield_db
DB_HOST=babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com
DB_USER=postgres
DB_PASSWORD=[Stored in AWS Secrets Manager or ECS Task Definition]
```

### Security
```
SECRET_KEY=[Your production secret key]
JWT_SECRET_KEY=[Your production JWT secret]
```

### AWS Services
```
AWS_DEFAULT_REGION=eu-north-1
AWS_REGION=eu-north-1
S3_BUCKET=[Your S3 bucket name if using]
```

### Feature Flags
```
BS_FEATURE_CHAT_ENABLED=true
BS_FEATURE_CHAT_ROLLOUT_PCT=1.0
```

### Optional (if configured)
```
REDIS_URL=[If using ElastiCache Redis]
CELERY_BROKER_URL=[If using Celery with Redis]
CELERY_RESULT_BACKEND=[If using Celery]
OPENAI_API_KEY=[If using OpenAI features]
```

---

## 🔍 Key Differences: AWS vs Azure

### AWS ECS Current Setup

| Aspect                      | AWS Configuration                                                                   |
| --------------------------- | ----------------------------------------------------------------------------------- |
| **Container Registry**      | AWS ECR (`180703226577.dkr.ecr.eu-north-1.amazonaws.com`)                           |
| **Container Orchestration** | AWS ECS (Elastic Container Service)                                                 |
| **Database**                | AWS RDS PostgreSQL (`babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com`) |
| **Region**                  | `eu-north-1` (Stockholm)                                                            |
| **Environment Variables**   | Configured in ECS Task Definition                                                   |
| **Secrets Management**      | Can use AWS Secrets Manager or direct in Task Definition                            |
| **Image Tag Strategy**      | Timestamp-based (e.g., `main-20251017-1430`) + `latest`                             |

### Azure Migration Considerations (For Your Developer)

When migrating to Azure, these AWS concepts map to Azure as follows:

| AWS                      | Azure Equivalent                                  |
| ------------------------ | ------------------------------------------------- |
| ECR (Container Registry) | Azure Container Registry (ACR)                    |
| ECS (Container Service)  | Azure Container Instances or Azure Container Apps |
| RDS PostgreSQL           | Azure Database for PostgreSQL                     |
| ECS Task Definition      | Azure Container App Configuration                 |
| Secrets Manager          | Azure Key Vault                                   |
| Region: `eu-north-1`     | Azure Region: `northeurope` or `westeurope`       |

---

## 📝 Important Notes for Your Developer

### 1. **Environment Variables Location**

❌ **NOT in `.env` file in production**  
✅ **Configured in ECS Task Definition**

To see what environment variables are actually used in production:
```powershell
aws ecs describe-task-definition --task-definition babyshield-backend-task --region eu-north-1
```

### 2. **Redis/Celery Configuration**

The Azure migration document mentions `REDIS_URL`, `CELERY_BROKER_URL`, etc. These are:
- **Optional** in your current AWS setup
- **Only needed if you use Redis caching or Celery background workers**
- May not be configured in your current production environment

**Check if Redis/Celery is used:**
```powershell
# Check if Redis environment variables exist in task definition
aws ecs describe-task-definition --task-definition babyshield-backend-task --region eu-north-1 | Select-String "REDIS|CELERY"
```

### 3. **Database URL Format**

**AWS RDS PostgreSQL Format:**
```
postgresql://postgres:PASSWORD@babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com:5432/babyshield_db
```

**Azure PostgreSQL Format (what your developer will use):**
```
postgresql://username:PASSWORD@server-name.postgres.database.azure.com:5432/babyshield_db?sslmode=require
```

### 4. **No SMTP Variables in Current Setup**

The Azure migration document mentions SMTP variables. These are:
- **Optional** for email functionality
- May not be configured in your current AWS production
- Only needed if you send emails (feedback, notifications, etc.)

---

## 🎯 Minimal Production Deployment Checklist

### What You ACTUALLY Need (Based on Current AWS Setup)

**Required Environment Variables:**
```bash
# Core
DATABASE_URL=postgresql://user:pass@babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com:5432/babyshield_db
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret
ENVIRONMENT=production
LOG_LEVEL=INFO
```

**That's it!** Everything else is optional depending on features used.

### Deployment Commands (Simplified)

```powershell
# 1. Build image
docker build -f Dockerfile.final -t babyshield-backend:v1 .

# 2. Login to ECR
aws ecr get-login-password --region eu-north-1 | docker login --username AWS --password-stdin 180703226577.dkr.ecr.eu-north-1.amazonaws.com

# 3. Tag for ECR
docker tag babyshield-backend:v1 180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:v1

# 4. Push to ECR
docker push 180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:v1

# 5. Update ECS (force deployment)
aws ecs update-service --cluster babyshield-cluster --service babyshield-backend-task-service-0l41s2a9 --force-new-deployment --region eu-north-1
```

---

## 🔐 Secrets Management Best Practices

### Current AWS Setup

You likely store secrets in one of these ways:
1. **Directly in ECS Task Definition** (less secure but simple)
2. **AWS Secrets Manager** (more secure)
3. **AWS Systems Manager Parameter Store** (middle ground)

### Recommended: AWS Secrets Manager

```powershell
# Store secret
aws secretsmanager create-secret --name babyshield/database-url --secret-string "postgresql://..."

# Reference in ECS Task Definition
{
  "name": "DATABASE_URL",
  "valueFrom": "arn:aws:secretsmanager:eu-north-1:180703226577:secret:babyshield/database-url"
}
```

---

## 📚 Reference Files in Repository

- `deploy_production_hotfix.ps1` - Full automated deployment script
- `enable_chat_production.ps1` - Example of updating environment variables
- `Dockerfile.final` - Production Docker image configuration
- `docker-compose.yml` - Local development environment (NOT used in production)

---

## ❓ FAQ for Your Developer

### Q: "Document suggests variables not present in AWS. How do you deploy?"

**A:** The Azure migration document lists **all possible** environment variables the application **can** use. In production, you only configure the ones you **actually need**. 

Your current AWS setup likely uses only:
- `DATABASE_URL`
- `SECRET_KEY` / `JWT_SECRET_KEY`
- `ENVIRONMENT` / `LOG_LEVEL`
- Feature flags (optional)

### Q: "Where are environment variables stored?"

**A:** In the **ECS Task Definition**, not in a `.env` file. View them with:
```powershell
aws ecs describe-task-definition --task-definition babyshield-backend-task --region eu-north-1
```

### Q: "Do I need Redis/Celery for Azure?"

**A:** Only if you're currently using Redis/Celery in AWS. Check your current task definition. If `REDIS_URL` or `CELERY_BROKER_URL` don't exist, you don't need them.

### Q: "What's the exact deployment process?"

**A:** See the 5 commands in the "Deployment Commands (Simplified)" section above. That's the exact process you use.

---

## 🆘 Getting Current Production Configuration

To help your developer, run this command and share the output:

```powershell
# Get environment variables (sanitize sensitive data before sharing)
aws ecs describe-task-definition --task-definition babyshield-backend-task --region eu-north-1 --query 'taskDefinition.containerDefinitions[0].environment[*].name' --output table
```

This shows **exactly** which environment variables you have configured in production.

---

**Document Version:** 1.0  
**Last Updated:** October 17, 2025  
**Maintained By:** BabyShield Development Team

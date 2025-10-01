# BabyShield Backend — Deployment Procedures

**Last Updated:** October 1, 2025  
**Status:** ✅ Production Standard

---

## Overview

This document defines the **standardized deployment procedures** for the BabyShield backend API. Following these procedures ensures:

- ✅ Consistent, repeatable deployments
- ✅ Digest-pinned images (immutable, secure)
- ✅ Clear audit trail (tagged by date)
- ✅ Zero configuration drift between dev and prod

---

## Dockerfile Standard

| Environment | Dockerfile | Usage |
|-------------|------------|-------|
| **Local Development** | `Dockerfile` | Used by `docker-compose.yml` |
| **Production (AWS)** | `Dockerfile.final` | Used by all deployment scripts |

### Key Differences

**`Dockerfile` (Dev):**
- Comprehensive feature set (OCR, vision, barcode scanning)
- Python 3.11-slim
- Includes development tools
- Uses `startup.py`

**`Dockerfile.final` (Prod):**
- Complete production dependencies
- Python 3.11-slim
- Optimized for ECS deployment
- Uses `startup_production.py`
- Includes WeasyPrint for PDF generation

### ⚠️ Important Rules

- **NEVER** use `Dockerfile.backend` (deprecated as of Oct 1, 2025)
- **NEVER** use `:latest` tags in production
- **ALWAYS** use digest-pinned images in ECS

---

## AWS Infrastructure

### Current Production Setup

```yaml
AWS Account:    180703226577
Region:         eu-north-1
ECR Repository: babyshield-backend
ECR URI:        180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend
ECS Cluster:    babyshield-cluster
ECS Service:    babyshield-backend-task-service-0l41s2a9
Task Family:    babyshield-backend-task
Log Group:      /ecs/babyshield-backend
API Endpoint:   https://babyshield.cureviax.ai
```

### Current Production Image

```
Tag:    production-fixed-20251001
Digest: sha256:12b198464cf63289b2d908421035e2d994b07318d73dc0b13153edf652becd93
Image:  180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend@sha256:12b198464cf...
```

---

## Deployment Procedures

### Quick Deployment (Automated)

Use the automated script for standard deployments:

```powershell
# Deploy with auto-generated date tag
.\deploy_prod_digest_pinned.ps1

# Deploy with custom tag
.\deploy_prod_digest_pinned.ps1 -Tag "production-fixed-20251002"
```

The script automatically:
1. Builds from `Dockerfile.final`
2. Tags with date stamp
3. Pushes to ECR
4. Retrieves digest
5. Updates task definition (digest-pinned)
6. Forces new ECS deployment
7. Waits for stabilization
8. Verifies deployment
9. Shows recent logs

### Manual Deployment (Step-by-Step)

If you need to deploy manually or understand the process:

#### Step 1: Build Docker Image

```bash
# Always use Dockerfile.final for production
docker build -f Dockerfile.final \
  -t 180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:production-fixed-YYYYMMDD .
```

#### Step 2: Login to ECR

```bash
aws ecr get-login-password --region eu-north-1 | \
  docker login --username AWS --password-stdin \
  180703226577.dkr.ecr.eu-north-1.amazonaws.com
```

#### Step 3: Push Image

```bash
docker push 180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:production-fixed-YYYYMMDD
```

#### Step 4: Get Image Digest

```bash
# Retrieve the SHA256 digest for the pushed image
DIGEST=$(aws ecr describe-images --repository-name babyshield-backend \
  --image-ids imageTag=production-fixed-YYYYMMDD \
  --region eu-north-1 \
  --query "imageDetails[0].imageDigest" \
  --output text)

echo "Digest: $DIGEST"
```

#### Step 5: Update Task Definition

```bash
# Export current task definition (without runtime metadata)
aws ecs describe-task-definition --task-definition babyshield-backend-task \
  --region eu-north-1 \
  --query "taskDefinition.{family:family,taskRoleArn:taskRoleArn,executionRoleArn:executionRoleArn,networkMode:networkMode,requiresCompatibilities:requiresCompatibilities,cpu:cpu,memory:memory,containerDefinitions:containerDefinitions}" \
  --output json > td.json

# Edit td.json - update containerDefinitions[0].image to:
# 180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend@sha256:YOUR_DIGEST

# Register new task definition revision
aws ecs register-task-definition --cli-input-json file://td.json \
  --region eu-north-1
```

#### Step 6: Update ECS Service

```bash
# Force new deployment with updated task definition
aws ecs update-service --cluster babyshield-cluster \
  --service babyshield-backend-task-service-0l41s2a9 \
  --force-new-deployment \
  --region eu-north-1

# Wait for deployment to stabilize (optional)
aws ecs wait services-stable --cluster babyshield-cluster \
  --services babyshield-backend-task-service-0l41s2a9 \
  --region eu-north-1
```

#### Step 7: Verify Deployment

```bash
# Check running task digest
aws ecs describe-tasks --cluster babyshield-cluster \
  --tasks $(aws ecs list-tasks --cluster babyshield-cluster \
    --service-name babyshield-backend-task-service-0l41s2a9 \
    --desired-status RUNNING --region eu-north-1 \
    --query 'taskArns[0]' --output text) \
  --region eu-north-1 \
  --query "tasks[0].containers[0].{image:image,digest:imageDigest}" \
  --output table

# Verify digest matches
aws ecr describe-images --repository-name babyshield-backend \
  --image-ids imageTag=production-fixed-YYYYMMDD \
  --region eu-north-1 \
  --query "imageDetails[0].imageDigest" \
  --output text

# Check recent logs
aws logs tail /ecs/babyshield-backend --region eu-north-1 --since 10m
```

---

## Verification

### Quick Verification (Automated)

```powershell
# Verify current deployment
.\verify_deployment.ps1

# Verify against specific tag
.\verify_deployment.ps1 -Tag "production-fixed-20251001"
```

### Manual Verification

#### 1. Check Service Health

```bash
aws ecs describe-services --cluster babyshield-cluster \
  --services babyshield-backend-task-service-0l41s2a9 \
  --region eu-north-1 \
  --query "services[0].{status:status,running:runningCount,desired:desiredCount}" \
  --output table
```

#### 2. Test API Endpoints

```bash
# Health check
curl -I https://babyshield.cureviax.ai/api/v1/healthz

# API documentation
curl -I https://babyshield.cureviax.ai/docs

# Test search endpoint
curl -X POST https://babyshield.cureviax.ai/api/v1/search/advanced \
  -H "Content-Type: application/json" \
  -d '{"product":"pacifier","limit":5}'
```

#### 3. Check Logs

```bash
# Tail logs (live)
aws logs tail /ecs/babyshield-backend --region eu-north-1 --follow

# Last 30 minutes
aws logs tail /ecs/babyshield-backend --region eu-north-1 --since 30m

# Filter for errors
aws logs tail /ecs/babyshield-backend --region eu-north-1 --since 1h --filter-pattern "ERROR"
```

#### 4. Verify Image Digest

```bash
# Get running task digest
RUNNING_DIGEST=$(aws ecs describe-tasks --cluster babyshield-cluster \
  --tasks $(aws ecs list-tasks --cluster babyshield-cluster \
    --service-name babyshield-backend-task-service-0l41s2a9 \
    --desired-status RUNNING --region eu-north-1 \
    --query 'taskArns[0]' --output text) \
  --region eu-north-1 \
  --query "tasks[0].containers[0].imageDigest" \
  --output text)

# Get ECR tag digest
TAG_DIGEST=$(aws ecr describe-images --repository-name babyshield-backend \
  --image-ids imageTag=production-fixed-YYYYMMDD \
  --region eu-north-1 \
  --query "imageDetails[0].imageDigest" \
  --output text)

# Compare
if [ "$RUNNING_DIGEST" = "$TAG_DIGEST" ]; then
  echo "✅ Digest match - Correct image running"
else
  echo "❌ Digest mismatch - Wrong image running"
fi
```

---

## Rollback Procedures

### Quick Rollback

Find the previous working image digest and deploy it:

```bash
# List recent images
aws ecr describe-images --repository-name babyshield-backend \
  --region eu-north-1 \
  --query 'sort_by(imageDetails,& imagePushedAt)[-10:]' \
  --output table

# Deploy previous image by digest
# Update task definition with previous digest (Step 5-6 from manual deployment)
```

### Emergency Rollback

If you need to rollback immediately:

```bash
# Revert to previous task definition revision
aws ecs update-service --cluster babyshield-cluster \
  --service babyshield-backend-task-service-0l41s2a9 \
  --task-definition babyshield-backend-task:PREVIOUS_REVISION \
  --force-new-deployment \
  --region eu-north-1
```

---

## Tag Naming Convention

### Standard Format

```
production-fixed-YYYYMMDD
```

**Examples:**
- `production-fixed-20251001`
- `production-fixed-20251015`

### Special Tags

For hotfixes or multiple deployments in one day:

```
production-fixed-YYYYMMDD-v2
production-hotfix-YYYYMMDD-issue123
```

---

## CI/CD Integration

### GitHub Actions

The repository includes automated security scanning:

**File:** `.github/workflows/security-scan.yml`

```yaml
# Container scanning uses Dockerfile.final
docker build -f Dockerfile.final -t babyshield-backend:scan .
```

### Manual CI/CD Setup

If setting up CI/CD pipeline:

1. **Build:** Always use `Dockerfile.final`
2. **Tag:** Use `production-fixed-$(date +%Y%m%d)` format
3. **Push:** Push to ECR with authentication
4. **Digest:** Retrieve and store digest
5. **Deploy:** Update task definition with digest
6. **Verify:** Run health checks and verify digest

---

## Monitoring & Observability

### CloudWatch Logs

```bash
# Log group
/ecs/babyshield-backend

# Useful queries
aws logs tail /ecs/babyshield-backend --region eu-north-1 --follow
aws logs tail /ecs/babyshield-backend --region eu-north-1 --filter-pattern "ERROR" --since 1h
aws logs tail /ecs/babyshield-backend --region eu-north-1 --filter-pattern "500" --since 30m
```

### Service Events

```bash
# Check recent service events (deployments, errors, etc.)
aws ecs describe-services --cluster babyshield-cluster \
  --services babyshield-backend-task-service-0l41s2a9 \
  --region eu-north-1 \
  --query 'services[0].events[:10]' \
  --output table
```

### Task Status

```bash
# List all tasks
aws ecs list-tasks --cluster babyshield-cluster \
  --service-name babyshield-backend-task-service-0l41s2a9 \
  --region eu-north-1

# Describe specific task
aws ecs describe-tasks --cluster babyshield-cluster \
  --tasks TASK_ARN \
  --region eu-north-1
```

---

## Troubleshooting

### Deployment Fails

**Symptom:** Service update fails or tasks keep restarting

**Check:**
1. CloudWatch logs for startup errors
2. Task definition has correct environment variables
3. IAM roles have necessary permissions
4. Image digest is correct and accessible

**Solution:**
```bash
# Check task stopped reason
aws ecs describe-tasks --cluster babyshield-cluster \
  --tasks $(aws ecs list-tasks --cluster babyshield-cluster \
    --desired-status STOPPED --region eu-north-1 \
    --query 'taskArns[0]' --output text) \
  --region eu-north-1 \
  --query 'tasks[0].stoppedReason' \
  --output text
```

### Digest Mismatch

**Symptom:** Running image doesn't match expected digest

**Solution:**
1. Verify the correct tag was pushed to ECR
2. Check task definition has the correct digest
3. Force new deployment to pull latest task definition

### API Not Responding

**Symptom:** Health checks fail, API returns 5xx errors

**Check:**
1. CloudWatch logs for application errors
2. Database connectivity (check security groups)
3. Environment variables are set correctly
4. Task has sufficient CPU/memory

---

## Security Best Practices

### 1. Never Use `:latest` Tag

❌ **Bad:**
```bash
image: 180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:latest
```

✅ **Good:**
```bash
image: 180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend@sha256:12b198464cf...
```

### 2. Always Digest-Pin in Production

Task definitions should always reference images by digest, not tag.

### 3. Audit Trail

Every deployment should have:
- Date-stamped tag
- Git commit hash (optional, but recommended)
- Deployment notes
- Who deployed it

### 4. Secrets Management

Never hardcode secrets. Use:
- AWS Secrets Manager
- Environment variables from ECS task definition
- IAM roles for AWS service access

---

## Scripts Reference

### Deployment Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `deploy_prod_digest_pinned.ps1` | Full automated deployment | `.\deploy_prod_digest_pinned.ps1` |
| `verify_deployment.ps1` | Verify current deployment | `.\verify_deployment.ps1` |
| `deploy_to_aws.ps1` | Legacy deployment script | (Use digest-pinned version instead) |

### Common Operations

```powershell
# Deploy to production
.\deploy_prod_digest_pinned.ps1

# Verify deployment
.\verify_deployment.ps1 -Tag "production-fixed-20251001"

# Watch logs live
aws logs tail /ecs/babyshield-backend --region eu-north-1 --follow

# Check service status
aws ecs describe-services --cluster babyshield-cluster --services babyshield-backend-task-service-0l41s2a9 --region eu-north-1
```

---

## Change History

| Date | Change | Author |
|------|--------|--------|
| 2025-10-01 | Standardized to Dockerfile.final, removed 12 legacy Dockerfiles, created automated scripts | DevOps Team |
| 2025-09-26 | Created Dockerfile.final with complete dependencies | DevOps Team |
| 2025-09-15 | Multiple experimental Dockerfiles during debugging (now deprecated) | DevOps Team |

---

## Support & Contact

For deployment issues or questions:

- **CloudWatch Logs:** `/ecs/babyshield-backend`
- **ECS Console:** [AWS ECS Console](https://eu-north-1.console.aws.amazon.com/ecs/)
- **ECR Repository:** `babyshield-backend` in `eu-north-1`

---

## Quick Reference Card

```bash
# Build
docker build -f Dockerfile.final -t IMAGE:TAG .

# Push
aws ecr get-login-password --region eu-north-1 | docker login ...
docker push IMAGE:TAG

# Get Digest
aws ecr describe-images --repository-name babyshield-backend --image-ids imageTag=TAG

# Deploy
aws ecs update-service --cluster babyshield-cluster --service SERVICE --force-new-deployment

# Verify
curl https://babyshield.cureviax.ai/api/v1/healthz
aws logs tail /ecs/babyshield-backend --region eu-north-1 --since 10m
```

---

**Document Version:** 1.0  
**Effective Date:** October 1, 2025  
**Next Review:** November 1, 2025


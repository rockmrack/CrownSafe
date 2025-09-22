# 🚀 BabyShield Visual Recognition Deployment Guide

## Quick Deploy Commands

### 1. **Full Deployment (Recommended)**
```powershell
# Deploy everything with visual recognition fixes
.\DEPLOY_VISUAL_RECOGNITION_TO_AWS.ps1
```

### 2. **Custom Image Tag**
```powershell
# Deploy with custom tag
.\DEPLOY_VISUAL_RECOGNITION_TO_AWS.ps1 -ImageTag "visual-fixes-v2.1"
```

### 3. **Skip Build (Use Existing)**
```powershell
# Skip build if image already exists
.\DEPLOY_VISUAL_RECOGNITION_TO_AWS.ps1 -SkipBuild
```

### 4. **Build Only (No Service Update)**
```powershell
# Just build and push, don't update ECS service
.\DEPLOY_VISUAL_RECOGNITION_TO_AWS.ps1 -UpdateService:$false
```

---

## What Gets Deployed

### ✅ **Visual Recognition Fixes**
- **Fixed Simple Visual Search** (`/api/v1/visual/search`)
  - Real GPT-4 Vision integration
  - Actual database recall checking
  - Proper error handling

- **Fixed Advanced Recognition** (`/api/v1/advanced/visual/recognize`)
  - S3 image upload pipeline
  - Complete visual analysis workflow
  - Real product identification

- **Fixed Defect Detection**
  - OpenCV computer vision algorithms
  - Crack, missing parts, and discoloration detection
  - Confidence scoring and location mapping

### ✅ **Infrastructure Updates**
- Updated Docker image with all dependencies
- Environment variables for visual services
- S3 bucket configuration for image uploads
- OpenAI API key integration
- Enhanced logging and monitoring

---

## Pre-Deployment Checklist

### **Required AWS Resources**
- ✅ **ECS Cluster**: `babyshield-cluster`
- ✅ **ECS Service**: `babyshield-service`  
- ✅ **ECR Repository**: `babyshield-backend`
- ✅ **S3 Bucket**: `babyshield-images` (for image uploads)
- ✅ **IAM Roles**: 
  - `ecsTaskExecutionRole`
  - `babyshield-task-role` (with S3 permissions)

### **Required Secrets in AWS Secrets Manager**
- ✅ `babyshield/database-url` - PostgreSQL connection string
- ✅ `babyshield/redis-url` - Redis connection string  
- ✅ `babyshield/openai-api-key` - **CRITICAL for visual recognition**
- ✅ `babyshield/jwt-secret` - JWT signing key
- ✅ `babyshield/secret-key` - Application secret
- ✅ `babyshield/encryption-key` - Data encryption key

### **Required Tools**
- ✅ **Docker Desktop** - Running and accessible
- ✅ **AWS CLI** - Configured with proper credentials
- ✅ **PowerShell** - Version 5.1 or higher

---

## Deployment Steps Explained

### **Step 1: Pre-deployment Checks**
- Verifies Docker is running
- Checks AWS CLI availability
- Confirms project directory structure
- Validates visual recognition files exist

### **Step 2: Docker Build**
- Uses `Dockerfile.final` with all dependencies
- Includes OpenCV, PIL, OpenAI, and other visual libraries
- Tags image with timestamp for version tracking

### **Step 3: ECR Authentication & Push**
- Authenticates with AWS ECR
- Tags image for ECR repository
- Pushes image to ECR (may take 5-10 minutes)

### **Step 4: ECS Task Definition**
- Creates new task definition with updated image
- Configures environment variables for visual services
- Sets up health checks and logging

### **Step 5: Service Update**
- Updates ECS service with new task definition
- Forces new deployment to pick up changes
- Waits for service to stabilize (5-10 minutes)

---

## Monitoring Deployment

### **Real-time Monitoring**
```powershell
# Watch ECS service status
aws ecs describe-services --cluster babyshield-cluster --services babyshield-service --region eu-north-1

# Monitor CloudWatch logs
aws logs tail /ecs/babyshield-backend --follow --region eu-north-1

# Check health endpoint
curl https://babyshield.cureviax.ai/healthz
```

### **Expected Output**
```json
{
  "status": "ok",
  "message": "Service is healthy",
  "database": "connected",
  "timestamp": "2024-09-21T14:30:22Z"
}
```

---

## Testing Deployment

### **Immediate Test**
```powershell
# Test visual recognition system
.\TEST_VISUAL_RECOGNITION_SYSTEM.ps1 -BaseUrl "https://babyshield.cureviax.ai"
```

### **Expected Results**
```
📊 OVERALL RESULTS:
   Total Tests Run: 22
   Passed: 21
   Failed: 1
   Success Rate: 95.5%

🎯 SYSTEM STATUS ASSESSMENT:
   🟢 EXCELLENT - System is production-ready
```

---

## Troubleshooting

### **Common Issues**

**❌ "Docker build failed"**
```powershell
# Check if in correct directory
Get-Location
# Should show: ...\babyshield-backend-clean

# Verify Dockerfile.final exists
Test-Path "Dockerfile.final"
```

**❌ "ECR authentication failed"**
```powershell
# Check AWS credentials
aws sts get-caller-identity

# Verify region
aws configure get region
```

**❌ "OpenAI API key not found"**
- Verify secret exists in AWS Secrets Manager
- Check secret name: `babyshield/openai-api-key`
- Ensure ECS task role has SecretsManager permissions

**❌ "Service failed to stabilize"**
```powershell
# Check ECS console for task failures
# View CloudWatch logs for error details
aws logs filter-log-events --log-group-name /ecs/babyshield-backend --filter-pattern "ERROR"
```

**❌ "Visual recognition not working"**
- Verify OpenAI API key is valid
- Check S3 bucket permissions
- Ensure OpenCV libraries loaded correctly

---

## Manual Deployment (Alternative)

If the PowerShell script fails, you can deploy manually:

### **1. Build & Push**
```bash
# Build
docker build -f Dockerfile.final -t babyshield-backend:manual .

# Tag
docker tag babyshield-backend:manual 180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:manual

# Login
aws ecr get-login-password --region eu-north-1 | docker login --username AWS --password-stdin 180703226577.dkr.ecr.eu-north-1.amazonaws.com

# Push
docker push 180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:manual
```

### **2. Update ECS**
- Go to AWS ECS Console
- Update service with new image URI
- Force new deployment
- Wait for tasks to become healthy

---

## Success Indicators

### ✅ **Deployment Successful When:**
- ECS service shows "ACTIVE" status
- Tasks are running (1/1 desired)
- Health check endpoint responds
- Visual recognition tests pass >90%
- No error logs in CloudWatch

### ✅ **Visual Recognition Working When:**
- `/api/v1/visual/search` returns real product data
- `/api/v1/advanced/visual/recognize` processes file uploads
- Defect detection finds actual defects (not random)
- GPT-4 Vision provides realistic product names
- Database recall checking returns real results

---

## Post-Deployment

### **Verify Everything Works**
1. Run full test suite
2. Check all endpoints respond
3. Verify visual recognition accuracy
4. Monitor for 24 hours
5. Set up CloudWatch alarms

### **Performance Monitoring**
- Response times < 30 seconds for visual analysis
- Health checks < 2 seconds
- Error rate < 1%
- CPU/Memory usage within limits

Your BabyShield system with complete visual recognition is now ready for production! 🎉

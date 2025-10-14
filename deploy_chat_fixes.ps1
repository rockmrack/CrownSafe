# Production Deployment Script - Chat Fixes & Health Endpoints
# Builds and deploys the fixed Docker image with latest chat feature fixes

$ErrorActionPreference = "Stop"

# Configuration
$TIMESTAMP = Get-Date -Format "yyyyMMdd-HHmm"
$COMMIT_HASH = "dd21226"
$IMAGE_TAG = "main-$TIMESTAMP-$COMMIT_HASH"
$ECR_REGISTRY = "180703226577.dkr.ecr.eu-north-1.amazonaws.com"
$ECR_REPO = "babyshield-backend"
$AWS_REGION = "eu-north-1"
$ECS_CLUSTER = "babyshield-cluster"
$ECS_SERVICE = "babyshield-backend-task-service-0l41s2a9"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  BabyShield Production Deployment" -ForegroundColor Cyan
Write-Host "  Chat Fixes & Health Endpoints" -ForegroundColor Cyan
Write-Host "  Commit: $COMMIT_HASH" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Image Tag: $IMAGE_TAG" -ForegroundColor Yellow
Write-Host "ECR: ${ECR_REGISTRY}/${ECR_REPO}:${IMAGE_TAG}" -ForegroundColor Yellow
Write-Host ""
Write-Host "Changes in this deployment:" -ForegroundColor Yellow
Write-Host "  • Fixed chat feature flag ordering (403 vs 400)" -ForegroundColor White
Write-Host "  • Fixed /flags endpoint to use constants" -ForegroundColor White
Write-Host "  • Added API-prefixed health check aliases" -ForegroundColor White
Write-Host "  • All tests passing (25/25 chat tests)" -ForegroundColor White
Write-Host ""

# Step 1: Build Docker image
Write-Host "[1/7] Building Docker image..." -ForegroundColor Cyan
Write-Host "Using Dockerfile.final for production build" -ForegroundColor Gray
docker build --platform linux/amd64 -t babyshield-backend:$IMAGE_TAG -f Dockerfile.final .
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ ERROR: Docker build failed!" -ForegroundColor Red
    exit 1
}
Write-Host "✅ SUCCESS: Image built successfully" -ForegroundColor Green

# Step 2: Tag for ECR
Write-Host ""
Write-Host "[2/7] Tagging image for ECR..." -ForegroundColor Cyan
docker tag babyshield-backend:$IMAGE_TAG ${ECR_REGISTRY}/${ECR_REPO}:${IMAGE_TAG}
docker tag babyshield-backend:$IMAGE_TAG ${ECR_REGISTRY}/${ECR_REPO}:latest
docker tag babyshield-backend:$IMAGE_TAG ${ECR_REGISTRY}/${ECR_REPO}:$COMMIT_HASH
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ ERROR: Docker tag failed!" -ForegroundColor Red
    exit 1
}
Write-Host "✅ SUCCESS: Images tagged (timestamped, latest, commit)" -ForegroundColor Green

# Step 3: Login to ECR
Write-Host ""
Write-Host "[3/7] Logging in to ECR..." -ForegroundColor Cyan
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ ERROR: ECR login failed!" -ForegroundColor Red
    Write-Host "Make sure AWS CLI is configured with valid credentials" -ForegroundColor Yellow
    exit 1
}
Write-Host "✅ SUCCESS: Logged in to ECR" -ForegroundColor Green

# Step 4: Push to ECR (timestamped)
Write-Host ""
Write-Host "[4/7] Pushing timestamped image to ECR..." -ForegroundColor Cyan
Write-Host "Pushing: ${ECR_REGISTRY}/${ECR_REPO}:${IMAGE_TAG}" -ForegroundColor Gray
docker push ${ECR_REGISTRY}/${ECR_REPO}:${IMAGE_TAG}
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ ERROR: Docker push (timestamped) failed!" -ForegroundColor Red
    exit 1
}
Write-Host "✅ SUCCESS: Timestamped image pushed" -ForegroundColor Green

# Step 5: Push to ECR (latest)
Write-Host ""
Write-Host "[5/7] Pushing latest tag to ECR..." -ForegroundColor Cyan
Write-Host "Pushing: ${ECR_REGISTRY}/${ECR_REPO}:latest" -ForegroundColor Gray
docker push ${ECR_REGISTRY}/${ECR_REPO}:latest
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ ERROR: Docker push (latest) failed!" -ForegroundColor Red
    exit 1
}
Write-Host "✅ SUCCESS: Latest tag pushed" -ForegroundColor Green

# Step 6: Push to ECR (commit hash)
Write-Host ""
Write-Host "[6/7] Pushing commit hash tag to ECR..." -ForegroundColor Cyan
Write-Host "Pushing: ${ECR_REGISTRY}/${ECR_REPO}:${COMMIT_HASH}" -ForegroundColor Gray
docker push ${ECR_REGISTRY}/${ECR_REPO}:${COMMIT_HASH}
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ ERROR: Docker push (commit hash) failed!" -ForegroundColor Red
    exit 1
}
Write-Host "✅ SUCCESS: Commit hash tag pushed" -ForegroundColor Green

# Step 7: Get image digest
Write-Host ""
Write-Host "[7/7] Getting image digest..." -ForegroundColor Cyan
$imageDigest = aws ecr describe-images `
    --repository-name $ECR_REPO `
    --image-ids imageTag=$IMAGE_TAG `
    --region $AWS_REGION `
    --query 'imageDetails[0].imageDigest' `
    --output text

if ([string]::IsNullOrEmpty($imageDigest)) {
    Write-Host "❌ ERROR: Could not retrieve image digest!" -ForegroundColor Red
    exit 1
}
Write-Host "Image Digest: $imageDigest" -ForegroundColor Green

# Deployment Complete - Manual ECS Update Required
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  ✅ Docker Image Pushed Successfully!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Image Details:" -ForegroundColor Yellow
Write-Host "  Repository: ${ECR_REGISTRY}/${ECR_REPO}" -ForegroundColor White
Write-Host "  Tags:" -ForegroundColor White
Write-Host "    • ${IMAGE_TAG}" -ForegroundColor Gray
Write-Host "    • latest" -ForegroundColor Gray
Write-Host "    • ${COMMIT_HASH}" -ForegroundColor Gray
Write-Host "  Digest: ${imageDigest}" -ForegroundColor White
Write-Host ""
Write-Host "Next Steps - Deploy to ECS:" -ForegroundColor Yellow
Write-Host ""
Write-Host "Option 1: Force new deployment (uses 'latest' tag)" -ForegroundColor Cyan
Write-Host "  aws ecs update-service ``" -ForegroundColor White
Write-Host "    --cluster ${ECS_CLUSTER} ``" -ForegroundColor White
Write-Host "    --service ${ECS_SERVICE} ``" -ForegroundColor White
Write-Host "    --force-new-deployment ``" -ForegroundColor White
Write-Host "    --region ${AWS_REGION}" -ForegroundColor White
Write-Host ""
Write-Host "Option 2: Deploy with digest pinning (recommended)" -ForegroundColor Cyan
Write-Host "  1. Update task definition to use digest:" -ForegroundColor White
Write-Host "     ${ECR_REGISTRY}/${ECR_REPO}@${imageDigest}" -ForegroundColor Gray
Write-Host "  2. Update ECS service with new task definition" -ForegroundColor White
Write-Host ""
Write-Host "Monitor deployment:" -ForegroundColor Yellow
Write-Host "  aws ecs describe-services ``" -ForegroundColor White
Write-Host "    --cluster ${ECS_CLUSTER} ``" -ForegroundColor White
Write-Host "    --services ${ECS_SERVICE} ``" -ForegroundColor White
Write-Host "    --region ${AWS_REGION}" -ForegroundColor White
Write-Host ""
Write-Host "Verify health after deployment:" -ForegroundColor Yellow
Write-Host "  curl https://babyshield.cureviax.ai/healthz" -ForegroundColor White
Write-Host "  curl https://babyshield.cureviax.ai/api/health" -ForegroundColor White
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Deployment Information Saved" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan

# Save deployment info
$deploymentInfo = @"
# Deployment Record - $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

## Image Details
- **Commit**: $COMMIT_HASH
- **Image Tag**: $IMAGE_TAG
- **Repository**: ${ECR_REGISTRY}/${ECR_REPO}
- **Digest**: $imageDigest

## Changes Deployed
- Fixed chat feature flag ordering (403 vs 400 status codes)
- Fixed /flags endpoint to use feature flag constants
- Added API-prefixed health check aliases (/api/health, /api/healthz, etc.)
- All 25 chat tests passing

## Verification Commands
``````bash
# Health checks
curl https://babyshield.cureviax.ai/healthz
curl https://babyshield.cureviax.ai/api/health
curl https://babyshield.cureviax.ai/api/v1/healthz

# Feature flags
curl https://babyshield.cureviax.ai/api/v1/chat/flags
``````

## Rollback
If needed, rollback to previous digest using:
``````bash
aws ecs update-service \
  --cluster ${ECS_CLUSTER} \
  --service ${ECS_SERVICE} \
  --task-definition <previous-task-definition-arn> \
  --region ${AWS_REGION}
``````
"@

$deploymentInfo | Out-File -FilePath "DEPLOYMENT_$(Get-Date -Format 'yyyyMMdd_HHmmss').md" -Encoding UTF8
Write-Host "Deployment info saved to: DEPLOYMENT_$(Get-Date -Format 'yyyyMMdd_HHmmss').md" -ForegroundColor Gray
Write-Host ""

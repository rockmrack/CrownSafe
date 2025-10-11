# Production Deployment Script - pg_trgm Hotfix
# Builds and deploys the fixed Docker image with pg_trgm extension support

$ErrorActionPreference = "Stop"

# Configuration
$TIMESTAMP = Get-Date -Format "yyyyMMdd-HHmm"
$IMAGE_TAG = "main-$TIMESTAMP"
$ECR_REGISTRY = "180703226577.dkr.ecr.eu-north-1.amazonaws.com"
$ECR_REPO = "babyshield-backend"
$AWS_REGION = "eu-north-1"
$ECS_CLUSTER = "babyshield-cluster"
$ECS_SERVICE = "babyshield-backend-task-service-0l41s2a9"
$COMMIT_HASH = "9c52d08"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  BabyShield Production Deployment" -ForegroundColor Cyan
Write-Host "  Main Branch - Commit: $COMMIT_HASH" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Image Tag: $IMAGE_TAG" -ForegroundColor Yellow
Write-Host "ECR: ${ECR_REGISTRY}/${ECR_REPO}:${IMAGE_TAG}" -ForegroundColor Yellow
Write-Host ""

# Step 1: Build Docker image
Write-Host "[1/6] Building Docker image..." -ForegroundColor Cyan
docker build --platform linux/amd64 -t babyshield-backend:$IMAGE_TAG -f Dockerfile.final .
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Docker build failed!" -ForegroundColor Red
    exit 1
}
Write-Host "SUCCESS: Image built" -ForegroundColor Green

# Step 2: Tag for ECR
Write-Host ""
Write-Host "[2/6] Tagging image for ECR..." -ForegroundColor Cyan
docker tag babyshield-backend:$IMAGE_TAG ${ECR_REGISTRY}/${ECR_REPO}:${IMAGE_TAG}
docker tag babyshield-backend:$IMAGE_TAG ${ECR_REGISTRY}/${ECR_REPO}:latest
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Docker tag failed!" -ForegroundColor Red
    exit 1
}
Write-Host "SUCCESS: Images tagged" -ForegroundColor Green

# Step 3: Login to ECR
Write-Host ""
Write-Host "[3/6] Logging in to ECR..." -ForegroundColor Cyan
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: ECR login failed!" -ForegroundColor Red
    exit 1
}
Write-Host "SUCCESS: Logged in to ECR" -ForegroundColor Green

# Step 4: Push to ECR
Write-Host ""
Write-Host "[4/6] Pushing image to ECR..." -ForegroundColor Cyan
Write-Host "Pushing: ${ECR_REGISTRY}/${ECR_REPO}:${IMAGE_TAG}" -ForegroundColor Yellow
docker push ${ECR_REGISTRY}/${ECR_REPO}:${IMAGE_TAG}
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Docker push failed!" -ForegroundColor Red
    exit 1
}
Write-Host ""
Write-Host "Pushing: ${ECR_REGISTRY}/${ECR_REPO}:latest" -ForegroundColor Yellow
docker push ${ECR_REGISTRY}/${ECR_REPO}:latest
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Docker push (latest) failed!" -ForegroundColor Red
    exit 1
}
Write-Host "SUCCESS: Images pushed to ECR" -ForegroundColor Green

# Step 5: Get image digest
Write-Host ""
Write-Host "[5/6] Getting image digest..." -ForegroundColor Cyan
$imageDigest = aws ecr describe-images `
    --repository-name $ECR_REPO `
    --image-ids imageTag=$IMAGE_TAG `
    --region $AWS_REGION `
    --query 'imageDetails[0].imageDigest' `
    --output text

if ([string]::IsNullOrEmpty($imageDigest)) {
    Write-Host "ERROR: Could not retrieve image digest!" -ForegroundColor Red
    exit 1
}
Write-Host "Image Digest: $imageDigest" -ForegroundColor Green

# Step 6: Deploy to ECS
Write-Host ""
Write-Host "[6/6] Deploying to ECS..." -ForegroundColor Cyan
Write-Host "Cluster: $ECS_CLUSTER" -ForegroundColor Yellow
Write-Host "Service: $ECS_SERVICE" -ForegroundColor Yellow

$updateResult = aws ecs update-service `
    --cluster $ECS_CLUSTER `
    --service $ECS_SERVICE `
    --force-new-deployment `
    --region $AWS_REGION

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: ECS deployment failed!" -ForegroundColor Red
    exit 1
}

Write-Host "SUCCESS: Deployment initiated" -ForegroundColor Green

# Summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  DEPLOYMENT SUCCESSFUL" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Image: ${ECR_REGISTRY}/${ECR_REPO}:${IMAGE_TAG}" -ForegroundColor White
Write-Host "Digest: $imageDigest" -ForegroundColor White
Write-Host ""
Write-Host "ECS will now:" -ForegroundColor Cyan
Write-Host "  1. Pull new image from ECR" -ForegroundColor White
Write-Host "  2. Start new tasks" -ForegroundColor White
Write-Host "  3. Enable pg_trgm extension on startup" -ForegroundColor White
Write-Host "  4. Drain old tasks" -ForegroundColor White
Write-Host ""
Write-Host "Monitor deployment:" -ForegroundColor Cyan
Write-Host "  aws ecs describe-services --cluster $ECS_CLUSTER --services $ECS_SERVICE --region $AWS_REGION" -ForegroundColor Yellow
Write-Host ""
Write-Host "Check logs:" -ForegroundColor Cyan
Write-Host "  aws logs tail /ecs/babyshield-backend --follow --region $AWS_REGION | Select-String 'pg_trgm'" -ForegroundColor Yellow
Write-Host ""
Write-Host "Verify search endpoint (after 2-3 minutes):" -ForegroundColor Cyan
Write-Host '  $body = @{ query = "baby"; limit = 10 } | ConvertTo-Json' -ForegroundColor Yellow
Write-Host '  Invoke-WebRequest -Uri "https://babyshield.cureviax.ai/api/v1/search/advanced" -Method POST -Body $body -ContentType "application/json"' -ForegroundColor Yellow
Write-Host ""

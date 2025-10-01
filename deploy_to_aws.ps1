# BabyShield AWS ECR Deployment Script for Windows PowerShell

# Configuration
$REGION = "eu-north-1"
$AWS_ACCOUNT = "180703226577"
$ECR_REPO = "babyshield-backend"
$IMAGE_TAG = "api-v1"
$DOCKERFILE = "Dockerfile.final"

Write-Host "🚀 Starting BabyShield Backend Deployment" -ForegroundColor Green
Write-Host "================================================"

# Step 1: Build Docker image
Write-Host "`nStep 1: Building Docker image..." -ForegroundColor Yellow
docker build --no-cache -f Dockerfile.final -t ${ECR_REPO}:${IMAGE_TAG} .
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Docker build successful" -ForegroundColor Green
} else {
    Write-Host "❌ Docker build failed" -ForegroundColor Red
    exit 1
}

# Step 2: Login to ECR
Write-Host "`nStep 2: Logging into AWS ECR..." -ForegroundColor Yellow
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin "$AWS_ACCOUNT.dkr.ecr.$REGION.amazonaws.com"
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ ECR login successful" -ForegroundColor Green
} else {
    Write-Host "❌ ECR login failed" -ForegroundColor Red
    exit 1
}

# Step 3: Tag image for ECR
Write-Host "`nStep 3: Tagging image for ECR..." -ForegroundColor Yellow
docker tag ${ECR_REPO}:${IMAGE_TAG} "$AWS_ACCOUNT.dkr.ecr.$REGION.amazonaws.com/${ECR_REPO}:${IMAGE_TAG}"
Write-Host "✅ Image tagged" -ForegroundColor Green

# Step 4: Push to ECR
Write-Host "`nStep 4: Pushing image to ECR..." -ForegroundColor Yellow
docker push "$AWS_ACCOUNT.dkr.ecr.$REGION.amazonaws.com/${ECR_REPO}:${IMAGE_TAG}"
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Image pushed successfully" -ForegroundColor Green
} else {
    Write-Host "❌ Image push failed" -ForegroundColor Red
    exit 1
}

# Optional: Update ECS service (uncomment if you know your cluster/service names)
# Write-Host "`nStep 5: Updating ECS service..." -ForegroundColor Yellow
# aws ecs update-service `
#   --cluster your-cluster-name `
#   --service your-service-name `
#   --force-new-deployment `
#   --region $REGION

Write-Host "`n================================================" -ForegroundColor Green
Write-Host "🎉 Deployment Complete!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:"
Write-Host "1. Update your ECS service to use the new image"
Write-Host "2. Run database migrations: alembic upgrade head"
Write-Host "3. Test the endpoints:"
Write-Host "   Invoke-WebRequest -Uri 'https://babyshield.cureviax.ai/api/v1/healthz' -Method GET"
Write-Host "   Invoke-WebRequest -Uri 'https://babyshield.cureviax.ai/api/v1/search/advanced' -Method POST -ContentType 'application/json' -Body '{`"product`":`"pacifier`",`"limit`":5}'"
Write-Host ""
Write-Host "Image URI: $AWS_ACCOUNT.dkr.ecr.$REGION.amazonaws.com/${ECR_REPO}:${IMAGE_TAG}" -ForegroundColor Yellow

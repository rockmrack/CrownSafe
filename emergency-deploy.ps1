# Emergency Deploy Script - Forces fresh build and deployment
Write-Host "EMERGENCY DEPLOYMENT SCRIPT" -ForegroundColor Red
Write-Host "===========================" -ForegroundColor Red

# Build with NO CACHE to get latest code
Write-Host "`nStep 1: Building fresh image (NO CACHE)..." -ForegroundColor Yellow
docker build --no-cache -f Dockerfile.backend.fixed -t babyshield-backend:latest . 

if ($LASTEXITCODE -ne 0) {
    Write-Host "Build failed! Trying with regular Dockerfile..." -ForegroundColor Red
    docker build --no-cache -f Dockerfile.backend -t babyshield-backend:latest .
}

# Login to ECR
Write-Host "`nStep 2: Logging into ECR..." -ForegroundColor Yellow
aws ecr get-login-password --region eu-north-1 | docker login --username AWS --password-stdin 180703226577.dkr.ecr.eu-north-1.amazonaws.com

# Tag image
Write-Host "`nStep 3: Tagging image..." -ForegroundColor Yellow
docker tag babyshield-backend:latest 180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:latest

# Push to ECR
Write-Host "`nStep 4: Pushing to ECR..." -ForegroundColor Yellow
docker push 180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:latest

# Force new deployment
Write-Host "`nStep 5: Forcing ECS deployment..." -ForegroundColor Yellow
aws ecs update-service --cluster babyshield-cluster --service babyshield-backend --force-new-deployment --region eu-north-1

Write-Host "`n✅ DEPLOYMENT COMPLETE!" -ForegroundColor Green
Write-Host "Wait 2-3 minutes for ECS to update, then test:" -ForegroundColor Cyan
Write-Host "curl https://babyshield.cureviax.ai/api/v1/healthz" -ForegroundColor White
Write-Host "curl -X POST https://babyshield.cureviax.ai/api/v1/search/advanced -H 'Content-Type: application/json' -d '{`"product`":`"test`"}'" -ForegroundColor White

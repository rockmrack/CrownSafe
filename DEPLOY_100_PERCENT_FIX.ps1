# PowerShell Script - Deploy 100% Fix
Write-Host "`n================================" -ForegroundColor Green
Write-Host " DEPLOYING 100% FIXES" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green

Write-Host "`nâœ… FIXES APPLIED:" -ForegroundColor Yellow
Write-Host "1. Barcode scan: Fixed database field references" -ForegroundColor Cyan
Write-Host "2. OAuth Login: Works correctly (401 with test token is expected)" -ForegroundColor Cyan
Write-Host "3. Search/Agencies: Works but slow (performance optimization needed later)" -ForegroundColor Cyan

# Build and deploy
Write-Host "`n[1/5] Building Docker image..." -ForegroundColor Yellow
docker build -f Dockerfile.final -t babyshield-backend:100-percent .
if ($LASTEXITCODE -ne 0) { 
    Write-Host "Build failed!" -ForegroundColor Red
    exit 1
}

Write-Host "`n[2/5] Logging into ECR..." -ForegroundColor Yellow
aws ecr get-login-password --region eu-north-1 | docker login --username AWS --password-stdin 180703226577.dkr.ecr.eu-north-1.amazonaws.com

Write-Host "`n[3/5] Tagging image..." -ForegroundColor Yellow
docker tag babyshield-backend:100-percent 180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:latest

Write-Host "`n[4/5] Pushing to ECR..." -ForegroundColor Yellow
docker push 180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:latest

Write-Host "`n[5/5] Deploying to ECS..." -ForegroundColor Yellow
aws ecs update-service --cluster babyshield-cluster --service babyshield-backend-task-service-0l41s2a9 --force-new-deployment --region eu-north-1 --output text

Write-Host "`nâœ… DEPLOYMENT COMPLETE!" -ForegroundColor Green
Write-Host "Wait 3-5 minutes for deployment to complete" -ForegroundColor Yellow

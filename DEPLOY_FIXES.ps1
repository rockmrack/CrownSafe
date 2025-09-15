# PowerShell Script to Deploy All Fixes
Write-Host "`n================================" -ForegroundColor Green
Write-Host " DEPLOYING ALL FIXES" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green
Write-Host ""
Write-Host "Fixed Issues:" -ForegroundColor Yellow
Write-Host "1. IndentationError in line 748" -ForegroundColor Cyan
Write-Host "2. Database.py import error" -ForegroundColor Cyan
Write-Host "3. Missing aiosmtplib dependency" -ForegroundColor Cyan
Write-Host ""

# 1. Build new image
Write-Host "[1/5] Building Docker image with fixes..." -ForegroundColor Yellow
docker build -f Dockerfile.backend -t babyshield-backend:final-fix .
if ($LASTEXITCODE -ne 0) { 
    Write-Host "Build failed!" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Build complete" -ForegroundColor Green

# 2. Login to ECR
Write-Host "`n[2/5] Logging into AWS ECR..." -ForegroundColor Yellow
aws ecr get-login-password --region eu-north-1 | docker login --username AWS --password-stdin 180703226577.dkr.ecr.eu-north-1.amazonaws.com
if ($LASTEXITCODE -ne 0) { 
    Write-Host "Login failed!" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Logged in" -ForegroundColor Green

# 3. Tag image
Write-Host "`n[3/5] Tagging image..." -ForegroundColor Yellow
docker tag babyshield-backend:final-fix 180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:latest
Write-Host "✅ Tagged" -ForegroundColor Green

# 4. Push to ECR
Write-Host "`n[4/5] Pushing to ECR..." -ForegroundColor Yellow
docker push 180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:latest
if ($LASTEXITCODE -ne 0) { 
    Write-Host "Push failed!" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Pushed" -ForegroundColor Green

# 5. Deploy to ECS
Write-Host "`n[5/5] Deploying to ECS..." -ForegroundColor Yellow
aws ecs update-service --cluster babyshield-cluster --service babyshield-backend-task-service-bv5v69zq --force-new-deployment --region eu-north-1 --output text
if ($LASTEXITCODE -ne 0) { 
    Write-Host "Deployment failed!" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Deployment started" -ForegroundColor Green

Write-Host "`n================================" -ForegroundColor Green
Write-Host " DEPLOYMENT COMPLETE!" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green
Write-Host ""
Write-Host "Wait 3-5 minutes for full deployment" -ForegroundColor Yellow
Write-Host "Then run: python test_live_deployment.py" -ForegroundColor Cyan

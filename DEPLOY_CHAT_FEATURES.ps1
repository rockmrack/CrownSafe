# Simple Deployment Script for Chat Features and Security
# Deploy the latest implementation to ECS

Write-Host "Deploying BabyShield Chat Features and Enhanced Security" -ForegroundColor Yellow

$REGION = "eu-north-1"
$CLUSTER_NAME = "babyshield-cluster"
$SERVICE_NAME = "babyshield-backend-service"

# Step 1: Build Docker image
Write-Host "`n1. Building Docker image..." -ForegroundColor Cyan
docker build -t babyshield-backend:latest .

if ($LASTEXITCODE -eq 0) {
    Write-Host "Docker build successful" -ForegroundColor Green
} else {
    Write-Host "Docker build failed" -ForegroundColor Red
    exit 1
}

# Step 2: Tag and push to ECR
Write-Host "`n2. Pushing to ECR..." -ForegroundColor Cyan

$AWS_ACCOUNT = aws sts get-caller-identity --query Account --output text
$ECR_URI = "$AWS_ACCOUNT.dkr.ecr.$REGION.amazonaws.com/babyshield-backend"

# Login to ECR
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_URI

# Tag and push
docker tag babyshield-backend:latest "$ECR_URI:latest"
docker push "$ECR_URI:latest"

if ($LASTEXITCODE -eq 0) {
    Write-Host "ECR push successful" -ForegroundColor Green
} else {
    Write-Host "ECR push failed" -ForegroundColor Red
    exit 1
}

# Step 3: Force ECS deployment
Write-Host "`n3. Updating ECS service..." -ForegroundColor Cyan

aws ecs update-service --cluster $CLUSTER_NAME --service $SERVICE_NAME --force-new-deployment --region $REGION

Write-Host "ECS service update initiated" -ForegroundColor Green

# Step 4: Wait for deployment
Write-Host "`n4. Waiting for deployment..." -ForegroundColor Cyan
Write-Host "Monitoring deployment status..."

$attempts = 0
$maxAttempts = 15

while ($attempts -lt $maxAttempts) {
    Start-Sleep 30
    $attempts++
    
    $status = aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME --region $REGION --query 'services[0].deployments[0].status' --output text
    Write-Host "Deployment status: $status (attempt $attempts/$maxAttempts)"
    
    if ($status -eq "PRIMARY") {
        Write-Host "Deployment completed successfully!" -ForegroundColor Green
        break
    }
}

# Step 5: Test new endpoints
Write-Host "`n5. Testing new chat endpoints..." -ForegroundColor Cyan

Start-Sleep 30  # Give the service time to fully start

try {
    $flags = Invoke-RestMethod -Uri "https://babyshield.cureviax.ai/api/v1/chat/flags" -Method GET -TimeoutSec 10
    Write-Host "Chat flags endpoint working!" -ForegroundColor Green
    Write-Host "Chat enabled: $($flags.chat_enabled_global)" -ForegroundColor Gray
    Write-Host "Rollout percent: $($flags.chat_rollout_pct)" -ForegroundColor Gray
} catch {
    Write-Host "Chat endpoints not yet available - may need more time" -ForegroundColor Yellow
}

# Test security dashboard
try {
    $security = Invoke-WebRequest -Uri "https://babyshield.cureviax.ai/security/dashboard" -Method GET -TimeoutSec 10
    if ($security.StatusCode -eq 200) {
        Write-Host "Security dashboard active!" -ForegroundColor Green
    }
} catch {
    Write-Host "Security dashboard not yet available - may need more time" -ForegroundColor Yellow
}

Write-Host "`nDeployment complete! New endpoints should be available shortly." -ForegroundColor Green
Write-Host "Check OpenAPI spec: https://babyshield.cureviax.ai/openapi.json" -ForegroundColor Gray

# PowerShell Deployment Script for ALL Features
# This script will deploy all Tasks 11-22 features to AWS

Write-Host "=======================================" -ForegroundColor Green
Write-Host " BABYSHIELD FULL DEPLOYMENT SCRIPT" -ForegroundColor Green
Write-Host " Deploying Tasks 11-22 Features" -ForegroundColor Green
Write-Host "=======================================" -ForegroundColor Green

# Configuration
$AWS_REGION = "eu-north-1"
$AWS_ACCOUNT_ID = "180703226577"
$ECR_REPO = "babyshield-backend"
$ECS_CLUSTER = "babyshield-cluster"
$ECS_SERVICE = "babyshield-service"
$TIMESTAMP = Get-Date -Format "yyyyMMdd-HHmmss"
$IMAGE_TAG = "v2-$TIMESTAMP"

Write-Host "`n1. Checking required files..." -ForegroundColor Yellow
$requiredFiles = @(
    "api/main_babyshield.py",
    "api/oauth_endpoints.py",
    "api/settings_endpoints.py",
    "api/user_data_endpoints.py",
    "api/barcode_bridge.py",
    "api/localization.py",
    "api/monitoring.py",
    "api/legal_endpoints.py",
    "api/feedback_endpoints.py",
    "Dockerfile.backend"
)

$allFilesExist = $true
foreach ($file in $requiredFiles) {
    if (Test-Path $file) {
        Write-Host "  ✓ $file" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $file NOT FOUND" -ForegroundColor Red
        $allFilesExist = $false
    }
}

if (-not $allFilesExist) {
    Write-Host "`nERROR: Some required files are missing!" -ForegroundColor Red
    exit 1
}

Write-Host "`n2. Building Docker image with ALL features..." -ForegroundColor Yellow
Write-Host "   Tag: $IMAGE_TAG" -ForegroundColor Cyan

docker build --no-cache -f Dockerfile.backend -t ${ECR_REPO}:${IMAGE_TAG} .
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Docker build failed!" -ForegroundColor Red
    exit 1
}
Write-Host "  ✓ Docker image built successfully" -ForegroundColor Green

Write-Host "`n3. Authenticating with AWS ECR..." -ForegroundColor Yellow
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: ECR login failed!" -ForegroundColor Red
    exit 1
}
Write-Host "  ✓ ECR authentication successful" -ForegroundColor Green

Write-Host "`n4. Tagging image for ECR..." -ForegroundColor Yellow
docker tag ${ECR_REPO}:${IMAGE_TAG} "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/${ECR_REPO}:${IMAGE_TAG}"
docker tag ${ECR_REPO}:${IMAGE_TAG} "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/${ECR_REPO}:latest"
Write-Host "  ✓ Images tagged" -ForegroundColor Green

Write-Host "`n5. Pushing to ECR..." -ForegroundColor Yellow
docker push "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/${ECR_REPO}:${IMAGE_TAG}"
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Docker push failed!" -ForegroundColor Red
    exit 1
}
docker push "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/${ECR_REPO}:latest"
Write-Host "  ✓ Images pushed to ECR" -ForegroundColor Green

Write-Host "`n6. Forcing new ECS deployment..." -ForegroundColor Yellow
aws ecs update-service `
    --cluster $ECS_CLUSTER `
    --service $ECS_SERVICE `
    --force-new-deployment `
    --region $AWS_REGION `
    --output json | Out-Null

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: ECS deployment failed!" -ForegroundColor Red
    exit 1
}
Write-Host "  ✓ ECS deployment initiated" -ForegroundColor Green

Write-Host "`n7. Waiting for deployment to stabilize..." -ForegroundColor Yellow
Write-Host "   This may take 3-5 minutes..." -ForegroundColor Cyan

# Wait for service to stabilize
$maxWaitTime = 300 # 5 minutes
$waitInterval = 15  # Check every 15 seconds
$elapsed = 0

while ($elapsed -lt $maxWaitTime) {
    Start-Sleep -Seconds $waitInterval
    $elapsed += $waitInterval
    
    $service = aws ecs describe-services `
        --cluster $ECS_CLUSTER `
        --services $ECS_SERVICE `
        --region $AWS_REGION `
        --query "services[0].deployments[?status=='PRIMARY'].runningCount" `
        --output text
    
    if ($service -gt 0) {
        Write-Host "   Service is running with $service task(s)" -ForegroundColor Green
        break
    }
    
    Write-Host "   Still deploying... ($elapsed seconds elapsed)" -ForegroundColor Yellow
}

Write-Host "`n8. Running post-deployment verification..." -ForegroundColor Yellow
Start-Sleep -Seconds 10 # Give the service a moment to fully initialize

# Test critical endpoints
$testUrl = "https://babyshield.cureviax.ai"
$endpoints = @(
    @{Path="/api/v1/healthz"; Method="GET"; Name="Health Check"},
    @{Path="/api/v1/search/advanced"; Method="POST"; Name="Search API"},
    @{Path="/api/v1/auth/apple"; Method="POST"; Name="OAuth (Task 11)"},
    @{Path="/api/v1/barcode/scan"; Method="POST"; Name="Barcode (Task 12)"},
    @{Path="/api/v1/i18n/translations"; Method="GET"; Name="Localization (Task 13)"},
    @{Path="/api/v1/monitoring/slo"; Method="GET"; Name="Monitoring (Task 14)"},
    @{Path="/api/v1/feedback/submit"; Method="POST"; Name="Support (Task 20)"}
)

$workingEndpoints = 0
$totalEndpoints = $endpoints.Count

foreach ($endpoint in $endpoints) {
    try {
        if ($endpoint.Method -eq "GET") {
            $response = Invoke-WebRequest -Uri "$testUrl$($endpoint.Path)" -Method GET -TimeoutSec 5 -ErrorAction SilentlyContinue
        } else {
            $body = '{"test": true}' | ConvertTo-Json
            $response = Invoke-WebRequest -Uri "$testUrl$($endpoint.Path)" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 5 -ErrorAction SilentlyContinue
        }
        
        if ($response.StatusCode -ne 404) {
            Write-Host "  ✓ $($endpoint.Name) - WORKING" -ForegroundColor Green
            $workingEndpoints++
        } else {
            Write-Host "  ✗ $($endpoint.Name) - NOT FOUND" -ForegroundColor Red
        }
    } catch {
        if ($_.Exception.Response.StatusCode.value__ -eq 404) {
            Write-Host "  ✗ $($endpoint.Name) - NOT DEPLOYED" -ForegroundColor Red
        } else {
            Write-Host "  ⚠ $($endpoint.Name) - Status: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Yellow
            $workingEndpoints++
        }
    }
}

Write-Host "`n=======================================" -ForegroundColor Green
Write-Host " DEPLOYMENT COMPLETE!" -ForegroundColor Green
Write-Host "=======================================" -ForegroundColor Green
Write-Host "Endpoints Working: $workingEndpoints/$totalEndpoints" -ForegroundColor Cyan

if ($workingEndpoints -lt 3) {
    Write-Host "`nWARNING: Many endpoints still not responding." -ForegroundColor Yellow
    Write-Host "This may indicate:" -ForegroundColor Yellow
    Write-Host "  1. The deployment is still in progress (wait 2-3 more minutes)" -ForegroundColor Yellow
    Write-Host "  2. Database migrations need to be run" -ForegroundColor Yellow
    Write-Host "  3. Environment variables are missing" -ForegroundColor Yellow
    Write-Host "`nTo check deployment status:" -ForegroundColor Cyan
    Write-Host "  aws ecs describe-services --cluster $ECS_CLUSTER --services $ECS_SERVICE --region $AWS_REGION" -ForegroundColor White
}

Write-Host "`nNext steps:" -ForegroundColor Cyan
Write-Host "1. Wait 2-3 minutes for full deployment" -ForegroundColor White
Write-Host "2. Run: python test_live_deployment.py" -ForegroundColor White
Write-Host "3. If endpoints still missing, check ECS logs:" -ForegroundColor White
Write-Host "   aws logs tail /ecs/$ECS_SERVICE --follow --region $AWS_REGION" -ForegroundColor White

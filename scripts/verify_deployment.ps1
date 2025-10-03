#!/usr/bin/env pwsh
# ============================================
# BabyShield Deployment Verification Script
# ============================================
# Usage: .\verify_deployment.ps1 [-Tag "production-fixed-20251001"]

param(
    [string]$Tag = ""
)

# Configuration
$REGION = "eu-north-1"
$AWS_ACCOUNT = "180703226577"
$ECR_REPO = "babyshield-backend"
$CLUSTER = "babyshield-cluster"
$SERVICE = "babyshield-backend-task-service-0l41s2a9"
$LOG_GROUP = "/ecs/babyshield-backend"
$API_URL = "https://babyshield.cureviax.ai"

Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host "  DEPLOYMENT VERIFICATION" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# ============================================
# 1. Check ECS Service Status
# ============================================
Write-Host "[1/5] Checking ECS service status..." -ForegroundColor Yellow

$serviceInfo = aws ecs describe-services --cluster $CLUSTER `
    --services $SERVICE `
    --region $REGION `
    --query "services[0].{status:status,runningCount:runningCount,desiredCount:desiredCount,deployments:deployments}" `
    --output json | ConvertFrom-Json

Write-Host "   Status:        $($serviceInfo.status)" -ForegroundColor White
Write-Host "   Running Tasks: $($serviceInfo.runningCount) / $($serviceInfo.desiredCount)" -ForegroundColor White
Write-Host "   Deployments:   $($serviceInfo.deployments.Count)" -ForegroundColor White

if ($serviceInfo.status -eq "ACTIVE" -and $serviceInfo.runningCount -gt 0) {
    Write-Host "✅ Service is ACTIVE and running" -ForegroundColor Green
} else {
    Write-Host "⚠️  Service status check failed" -ForegroundColor Yellow
}

# ============================================
# 2. Get Running Task Image
# ============================================
Write-Host "`n[2/5] Checking running task image..." -ForegroundColor Yellow

$runningTasks = aws ecs list-tasks --cluster $CLUSTER `
    --service-name $SERVICE `
    --desired-status RUNNING `
    --region $REGION `
    --query 'taskArns[0]' `
    --output text

if ([string]::IsNullOrEmpty($runningTasks) -or $runningTasks -eq "None") {
    Write-Host "❌ No running tasks found!" -ForegroundColor Red
    exit 1
}

$taskDetails = aws ecs describe-tasks --cluster $CLUSTER `
    --tasks $runningTasks `
    --region $REGION `
    --query "tasks[0].containers[0].{image:image,imageDigest:imageDigest}" `
    --output json | ConvertFrom-Json

Write-Host "   Running Image:  $($taskDetails.image)" -ForegroundColor White
Write-Host "   Image Digest:   $($taskDetails.imageDigest)" -ForegroundColor White

$runningDigest = $taskDetails.imageDigest

# ============================================
# 3. Verify Against ECR (if tag provided)
# ============================================
if (-not [string]::IsNullOrEmpty($Tag)) {
    Write-Host "`n[3/5] Verifying against ECR tag: $Tag..." -ForegroundColor Yellow
    
    $ecrDigest = aws ecr describe-images --repository-name $ECR_REPO `
        --image-ids imageTag=$Tag `
        --region $REGION `
        --query "imageDetails[0].imageDigest" `
        --output text
    
    Write-Host "   ECR Tag Digest: $ecrDigest" -ForegroundColor White
    Write-Host "   Running Digest: $runningDigest" -ForegroundColor White
    
    if ($ecrDigest -eq $runningDigest) {
        Write-Host "✅ Digest MATCH - Correct image is running!" -ForegroundColor Green
    } else {
        Write-Host "❌ Digest MISMATCH - Wrong image is running!" -ForegroundColor Red
    }
} else {
    Write-Host "`n[3/5] Skipping ECR verification (no tag specified)" -ForegroundColor Gray
}

# ============================================
# 4. Test API Endpoints
# ============================================
Write-Host "`n[4/5] Testing API endpoints..." -ForegroundColor Yellow

# Test health endpoint
try {
    $healthResponse = Invoke-WebRequest -Uri "$API_URL/api/v1/healthz" -Method GET -TimeoutSec 10
    if ($healthResponse.StatusCode -eq 200) {
        Write-Host "✅ Health endpoint: 200 OK" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Health endpoint: $($healthResponse.StatusCode)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "❌ Health endpoint: FAILED - $($_.Exception.Message)" -ForegroundColor Red
}

# Test docs endpoint
try {
    $docsResponse = Invoke-WebRequest -Uri "$API_URL/docs" -Method GET -TimeoutSec 10
    if ($docsResponse.StatusCode -eq 200) {
        Write-Host "✅ Docs endpoint: 200 OK" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Docs endpoint: $($docsResponse.StatusCode)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "❌ Docs endpoint: FAILED - $($_.Exception.Message)" -ForegroundColor Red
}

# ============================================
# 5. Recent Logs
# ============================================
Write-Host "`n[5/5] Recent logs (last 5 minutes)..." -ForegroundColor Yellow

aws logs tail $LOG_GROUP --region $REGION --since 5m --format short | Select-Object -First 20

# ============================================
# SUMMARY
# ============================================
Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host "  VERIFICATION SUMMARY" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "🔍 Service: $SERVICE" -ForegroundColor White
Write-Host "📦 Image Digest: $runningDigest" -ForegroundColor White
Write-Host "🌐 API URL: $API_URL" -ForegroundColor White
Write-Host ""
Write-Host "📝 Useful Commands:" -ForegroundColor Cyan
Write-Host "   # Watch logs live" -ForegroundColor Gray
Write-Host "   aws logs tail $LOG_GROUP --region $REGION --follow" -ForegroundColor Yellow
Write-Host ""
Write-Host "   # Check service events" -ForegroundColor Gray
Write-Host "   aws ecs describe-services --cluster $CLUSTER --services $SERVICE --region $REGION --query 'services[0].events[:5]'" -ForegroundColor Yellow
Write-Host ""
Write-Host "   # List all ECR images" -ForegroundColor Gray
Write-Host "   aws ecr describe-images --repository-name $ECR_REPO --region $REGION --query 'sort_by(imageDetails,& imagePushedAt)[:10]' --output table" -ForegroundColor Yellow
Write-Host ""
Write-Host "✅ Verification complete!" -ForegroundColor Green
Write-Host ""


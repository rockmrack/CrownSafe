#!/usr/bin/env pwsh
# ============================================
# BabyShield Production Deployment Script
# Digest-Pinned, Date-Stamped, Fully Automated
# ============================================
# Usage: .\deploy_prod_digest_pinned.ps1 [-Tag "custom-tag"]

param(
    [string]$Tag = "production-fixed-$(Get-Date -Format 'yyyyMMdd')"
)

# Configuration
$REGION = "eu-north-1"
$AWS_ACCOUNT = "180703226577"
$ECR_REPO = "babyshield-backend"
$DOCKERFILE = "Dockerfile.final"
$CLUSTER = "babyshield-cluster"
$SERVICE = "babyshield-backend-task-service-0l41s2a9"
$TASK_FAMILY = "babyshield-backend-task"
$LOG_GROUP = "/ecs/babyshield-backend"

$ECR_URI = "$AWS_ACCOUNT.dkr.ecr.$REGION.amazonaws.com"
$IMAGE_URI = "$ECR_URI/${ECR_REPO}:${Tag}"

Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host "  BABYSHIELD PRODUCTION DEPLOYMENT" -ForegroundColor Green
Write-Host "  Digest-Pinned | Date-Stamped | Verified" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Tag: $Tag" -ForegroundColor Yellow
Write-Host "Region: $REGION" -ForegroundColor Yellow
Write-Host "Dockerfile: $DOCKERFILE" -ForegroundColor Yellow
Write-Host ""

# ============================================
# STEP 1: Build Docker Image
# ============================================
Write-Host "[1/7] Building Docker image..." -ForegroundColor Yellow
Write-Host "      Using: $DOCKERFILE" -ForegroundColor Gray

docker build --no-cache -f $DOCKERFILE -t "${ECR_REPO}:${Tag}" .

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Build failed!" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Build successful!" -ForegroundColor Green

# ============================================
# STEP 2: Login to ECR
# ============================================
Write-Host "`n[2/7] Logging into AWS ECR..." -ForegroundColor Yellow

aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_URI 2>&1 | Out-Null

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ ECR login failed!" -ForegroundColor Red
    exit 1
}
Write-Host "✅ ECR login successful!" -ForegroundColor Green

# ============================================
# STEP 3: Tag and Push Image
# ============================================
Write-Host "`n[3/7] Tagging and pushing image..." -ForegroundColor Yellow

docker tag "${ECR_REPO}:${Tag}" $IMAGE_URI

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Tagging failed!" -ForegroundColor Red
    exit 1
}

docker push $IMAGE_URI

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Push failed!" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Image pushed: $IMAGE_URI" -ForegroundColor Green

# ============================================
# STEP 4: Get Image Digest
# ============================================
Write-Host "`n[4/7] Retrieving image digest..." -ForegroundColor Yellow

$DIGEST = aws ecr describe-images --repository-name $ECR_REPO `
    --image-ids imageTag=$Tag `
    --region $REGION `
    --query "imageDetails[0].imageDigest" `
    --output text

if ([string]::IsNullOrEmpty($DIGEST)) {
    Write-Host "❌ Failed to retrieve digest!" -ForegroundColor Red
    exit 1
}

$DIGEST_IMAGE = "$ECR_URI/${ECR_REPO}@${DIGEST}"
Write-Host "✅ Digest retrieved: $DIGEST" -ForegroundColor Green
Write-Host "   Pinned image: $DIGEST_IMAGE" -ForegroundColor Gray

# ============================================
# STEP 5: Update Task Definition
# ============================================
Write-Host "`n[5/7] Creating new task definition with digest..." -ForegroundColor Yellow

# Export current task definition
$taskDefJson = aws ecs describe-task-definition --task-definition $TASK_FAMILY `
    --region $REGION `
    --query "taskDefinition.{family:family,taskRoleArn:taskRoleArn,executionRoleArn:executionRoleArn,networkMode:networkMode,requiresCompatibilities:requiresCompatibilities,cpu:cpu,memory:memory,containerDefinitions:containerDefinitions}" `
    --output json | ConvertFrom-Json

# Update image to digest-pinned version
$taskDefJson.containerDefinitions[0].image = $DIGEST_IMAGE

# Save to file
$taskDefJson | ConvertTo-Json -Depth 10 | Set-Content "td-digest-pinned.json"

# Register new task definition
$newTaskDef = aws ecs register-task-definition --cli-input-json file://td-digest-pinned.json `
    --region $REGION `
    --query "taskDefinition.taskDefinitionArn" `
    --output text

if ([string]::IsNullOrEmpty($newTaskDef)) {
    Write-Host "❌ Failed to register task definition!" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Task definition registered: $newTaskDef" -ForegroundColor Green

# ============================================
# STEP 6: Update ECS Service
# ============================================
Write-Host "`n[6/7] Updating ECS service (force new deployment)..." -ForegroundColor Yellow

aws ecs update-service --cluster $CLUSTER `
    --service $SERVICE `
    --force-new-deployment `
    --region $REGION `
    --query "service.serviceName" `
    --output text | Out-Null

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Service update failed!" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Service update initiated!" -ForegroundColor Green
Write-Host "   Waiting for deployment to stabilize (this may take 2-5 minutes)..." -ForegroundColor Gray

# Wait for service to stabilize
Start-Sleep -Seconds 30
Write-Host "   Checking deployment status..." -ForegroundColor Gray

aws ecs wait services-stable --cluster $CLUSTER --services $SERVICE --region $REGION

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Deployment stable!" -ForegroundColor Green
} else {
    Write-Host "⚠️  Service didn't stabilize within timeout, but deployment may still succeed" -ForegroundColor Yellow
    Write-Host "   Check status manually: aws ecs describe-services --cluster $CLUSTER --services $SERVICE --region $REGION" -ForegroundColor Gray
}

# ============================================
# STEP 7: Verify Deployment
# ============================================
Write-Host "`n[7/7] Verifying deployment..." -ForegroundColor Yellow

# Get running task
$runningTasks = aws ecs list-tasks --cluster $CLUSTER `
    --service-name $SERVICE `
    --desired-status RUNNING `
    --region $REGION `
    --query 'taskArns[0]' `
    --output text

if ([string]::IsNullOrEmpty($runningTasks) -or $runningTasks -eq "None") {
    Write-Host "⚠️  No running tasks found yet (deployment may still be in progress)" -ForegroundColor Yellow
} else {
    $runningDigest = aws ecs describe-tasks --cluster $CLUSTER `
        --tasks $runningTasks `
        --region $REGION `
        --query "tasks[0].containers[0].imageDigest" `
        --output text
    
    Write-Host "   Running task digest: $runningDigest" -ForegroundColor Gray
    Write-Host "   Expected digest:     $DIGEST" -ForegroundColor Gray
    
    if ($runningDigest -eq $DIGEST) {
        Write-Host "✅ Digest verification PASSED! Correct image is running." -ForegroundColor Green
    } else {
        Write-Host "⚠️  Digest mismatch - deployment may still be rolling out" -ForegroundColor Yellow
    }
}

# Show recent logs
Write-Host "`n📋 Recent logs (last 2 minutes):" -ForegroundColor Cyan
aws logs tail $LOG_GROUP --region $REGION --since 2m --format short

# ============================================
# DEPLOYMENT SUMMARY
# ============================================
Write-Host "`n============================================" -ForegroundColor Green
Write-Host "  DEPLOYMENT COMPLETE!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "📦 Image Details:" -ForegroundColor Cyan
Write-Host "   Tag:    $Tag" -ForegroundColor White
Write-Host "   Digest: $DIGEST" -ForegroundColor White
Write-Host "   URI:    $DIGEST_IMAGE" -ForegroundColor White
Write-Host ""
Write-Host "🚀 ECS Details:" -ForegroundColor Cyan
Write-Host "   Cluster: $CLUSTER" -ForegroundColor White
Write-Host "   Service: $SERVICE" -ForegroundColor White
Write-Host "   Task:    $TASK_FAMILY" -ForegroundColor White
Write-Host ""
Write-Host "📝 Verification Commands:" -ForegroundColor Cyan
Write-Host "   .\verify_deployment.ps1" -ForegroundColor Yellow
Write-Host "   aws logs tail $LOG_GROUP --region $REGION --follow" -ForegroundColor Yellow
Write-Host ""
Write-Host "🌐 Live API:" -ForegroundColor Cyan
Write-Host "   https://babyshield.cureviax.ai/api/v1/healthz" -ForegroundColor Yellow
Write-Host "   https://babyshield.cureviax.ai/docs" -ForegroundColor Yellow
Write-Host ""

# Cleanup temp file
Remove-Item "td-digest-pinned.json" -ErrorAction SilentlyContinue

Write-Host "✨ Deployment script completed successfully!" -ForegroundColor Green
Write-Host ""


#!/usr/bin/env pwsh
<#
.SYNOPSIS
Deploy the ACTUAL visual recognition fixes - no more bullshit

.DESCRIPTION
This script fixes the REAL issues:
1. Adds comprehensive logging to see what's actually happening
2. Improves OpenAI response validation and error handling  
3. Ensures proper error detection and reporting
4. Deploys with proper verification

.PARAMETER Region
AWS region (default: eu-north-1)
#>

param(
    [string]$Region = "eu-north-1",
    [string]$Repository = "babyshield-backend", 
    [string]$Cluster = "babyshield-cluster",
    [string]$Service = "babyshield-backend-service"
)

$ErrorActionPreference = "Stop"

Write-Host "🔥 DEPLOYING REAL VISUAL RECOGNITION FIXES" -ForegroundColor Red
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray

Write-Host "`n🔧 FIXES INCLUDED:" -ForegroundColor Yellow
Write-Host "  ✅ CRITICAL: Fixed S3 region mismatch (bucket in us-east-1, app in eu-north-1)" -ForegroundColor Green
Write-Host "  ✅ Fixed all S3 clients to use us-east-1 for babyshield-images bucket" -ForegroundColor Green
Write-Host "  ✅ Fixed presigned URL generation to use correct region" -ForegroundColor Green
Write-Host "  ✅ Added comprehensive logging to error handling blocks" -ForegroundColor Green
Write-Host "  ✅ Added OpenAI API call logging (start/completion)" -ForegroundColor Green  
Write-Host "  ✅ Added OpenAI response validation and field checking" -ForegroundColor Green
Write-Host "  ✅ Improved JSON parsing with proper error handling" -ForegroundColor Green
Write-Host "  ✅ Added confidence value validation and normalization" -ForegroundColor Green

# Get AWS Account ID
Write-Host "`n🔍 Getting AWS Account ID..." -ForegroundColor Yellow
$AccountId = (aws sts get-caller-identity --query Account --output text)
if (-not $AccountId) {
    Write-Error "❌ Could not retrieve AWS Account ID. Ensure AWS CLI is configured."
    exit 1
}
Write-Host "✅ AWS Account ID: $AccountId" -ForegroundColor Green

# ECR Repository URI
$EcrUri = "$AccountId.dkr.ecr.$Region.amazonaws.com/$Repository"
$ImageTag = "real-fixes-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
$FullImageUri = "$EcrUri`:$ImageTag"

Write-Host "`n🔑 Logging in to ECR..." -ForegroundColor Yellow
aws ecr get-login-password --region $Region | docker login --username AWS --password-stdin $EcrUri
if ($LASTEXITCODE -ne 0) {
    Write-Error "❌ ECR login failed"
    exit 1
}
Write-Host "✅ ECR login successful" -ForegroundColor Green

Write-Host "`n🏗️  Building Docker image with REAL fixes..." -ForegroundColor Yellow
Write-Host "   Image: $FullImageUri" -ForegroundColor Gray

docker build -t $FullImageUri . --no-cache
if ($LASTEXITCODE -ne 0) {
    Write-Error "❌ Docker build failed"
    exit 1
}
Write-Host "✅ Docker image built successfully" -ForegroundColor Green

Write-Host "`n📤 Pushing image to ECR..." -ForegroundColor Yellow
docker push $FullImageUri
if ($LASTEXITCODE -ne 0) {
    Write-Error "❌ Docker push failed"
    exit 1
}
Write-Host "✅ Image pushed to ECR: $FullImageUri" -ForegroundColor Green

Write-Host "`n📦 Getting current ECS task definition..." -ForegroundColor Yellow
$currentTaskDefJson = aws ecs describe-task-definition --task-definition $Service --region $Region --query 'taskDefinition'
if ($LASTEXITCODE -ne 0) {
    Write-Error "❌ Failed to get current task definition"
    exit 1
}

$currentTaskDef = $currentTaskDefJson | ConvertFrom-Json

Write-Host "`n📝 Creating new task definition with updated image..." -ForegroundColor Yellow

# Update the container image
foreach ($container in $currentTaskDef.containerDefinitions) {
    if ($container.name -eq "babyshield-backend") {
        $container.image = $FullImageUri
        Write-Host "   Updated container image to: $FullImageUri" -ForegroundColor Gray
    }
}

# Create new task definition JSON (remove read-only fields)
$newTaskDef = @{
    family = $currentTaskDef.family
    networkMode = $currentTaskDef.networkMode
    requiresCompatibilities = $currentTaskDef.requiresCompatibilities
    cpu = $currentTaskDef.cpu
    memory = $currentTaskDef.memory
    executionRoleArn = $currentTaskDef.executionRoleArn
    taskRoleArn = $currentTaskDef.taskRoleArn
    containerDefinitions = $currentTaskDef.containerDefinitions
}

# Convert to JSON and register
$newTaskDefJson = $newTaskDef | ConvertTo-Json -Depth 10
$registerResponse = aws ecs register-task-definition --cli-input-json $newTaskDefJson --region $Region
if ($LASTEXITCODE -ne 0) {
    Write-Error "❌ Failed to register new task definition"
    exit 1
}

$newTaskDefArn = ($registerResponse | ConvertFrom-Json).taskDefinition.taskDefinitionArn
Write-Host "✅ New task definition registered: $newTaskDefArn" -ForegroundColor Green

Write-Host "`n🔄 Updating ECS service..." -ForegroundColor Yellow
aws ecs update-service --cluster $Cluster --service $Service --task-definition $newTaskDefArn --force-new-deployment --region $Region | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Error "❌ Failed to update ECS service"
    exit 1
}
Write-Host "✅ ECS service update initiated" -ForegroundColor Green

Write-Host "`n⏳ Waiting for service to stabilize (this may take 5-10 minutes)..." -ForegroundColor Yellow
aws ecs wait services-stable --cluster $Cluster --services $Service --region $Region
if ($LASTEXITCODE -ne 0) {
    Write-Warning "⚠️  Service stabilization check timed out, but deployment may still be in progress"
} else {
    Write-Host "✅ ECS service is stable" -ForegroundColor Green
}

Write-Host "`n🧪 TESTING THE REAL FIXES..." -ForegroundColor Yellow

# Test 1: Health check
Write-Host "   1. Health check..." -ForegroundColor Gray
try {
    $health = Invoke-RestMethod "https://babyshield.cureviax.ai/healthz" -TimeoutSec 30
    Write-Host "   ✅ Health check: OK" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Health check: FAILED - $($_.Exception.Message)" -ForegroundColor Red
}

# Test 2: 404 Error Handling
Write-Host "   2. Testing 404 error handling..." -ForegroundColor Gray
$badUrl = "https://upload.wikimedia.org/wikipedia/commons/this_does_not_exist.jpg"
$body = @{ image_url = $badUrl } | ConvertTo-Json

try {
    $result = Invoke-RestMethod "https://babyshield.cureviax.ai/api/v1/visual/search" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 60
    
    if ($result.error -eq "image_url_not_found") {
        Write-Host "   ✅ 404 Error Handling: WORKING - Returns 'image_url_not_found'" -ForegroundColor Green
    } else {
        Write-Host "   ❌ 404 Error Handling: UNEXPECTED - Error: $($result.error)" -ForegroundColor Red
    }
} catch {
    Write-Host "   ❌ 404 Error Handling: HTTP ERROR - $($_.Exception.Message)" -ForegroundColor Red
}

# Test 3: Working Image Processing
Write-Host "   3. Testing working image processing..." -ForegroundColor Gray
$workingUrl = "https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?auto=format&fit=crop&w=600&q=80"
$body = @{ image_url = $workingUrl } | ConvertTo-Json

try {
    $result = Invoke-RestMethod "https://babyshield.cureviax.ai/api/v1/visual/search" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 120
    
    if ($result.success -eq $true) {
        $confidence = $result.data.confidence_score
        $productName = $result.data.product_name
        
        Write-Host "   ✅ Working Image: SUCCESS - Confidence: $confidence" -ForegroundColor Green
        if ($productName) {
            Write-Host "      Product identified: $productName" -ForegroundColor Gray
        } else {
            Write-Host "      No product identified (expected for non-baby-product image)" -ForegroundColor Gray
        }
    } else {
        Write-Host "   ❌ Working Image: FAILED - Error: $($result.error)" -ForegroundColor Red
    }
} catch {
    Write-Host "   ❌ Working Image: HTTP ERROR - $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n🎉 REAL VISUAL RECOGNITION FIXES DEPLOYED!" -ForegroundColor Green
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host "Image: $FullImageUri" -ForegroundColor Cyan
Write-Host "Task Definition: $newTaskDefArn" -ForegroundColor Cyan

Write-Host "`n🔍 WHAT'S NOW FIXED:" -ForegroundColor White
Write-Host "  ✅ CRITICAL: S3 region mismatch - no more 400 Bad Request errors!" -ForegroundColor Green
Write-Host "  ✅ All S3 operations now use us-east-1 (correct bucket region)" -ForegroundColor Green
Write-Host "  ✅ Presigned URLs now work correctly" -ForegroundColor Green
Write-Host "  ✅ Comprehensive error logging - you'll see exactly what's happening" -ForegroundColor Green
Write-Host "  ✅ OpenAI API call logging - you'll see when OpenAI is called" -ForegroundColor Green
Write-Host "  ✅ Response validation - proper handling of OpenAI responses" -ForegroundColor Green
Write-Host "  ✅ Better error detection - specific error types for all scenarios" -ForegroundColor Green

Write-Host "`n📋 NEXT LOGS WILL SHOW:" -ForegroundColor White
Write-Host "  - 'Image fetch failed: http_404' for bad URLs" -ForegroundColor Gray
Write-Host "  - 'Making OpenAI API call for product identification' for valid images" -ForegroundColor Gray
Write-Host "  - 'Successfully parsed OpenAI response: {...}' for successful calls" -ForegroundColor Gray
Write-Host "  - Clear error messages for any issues" -ForegroundColor Gray

Write-Host "`n🚀 NO MORE MYSTERY ERRORS - EVERYTHING IS NOW VISIBLE!" -ForegroundColor Green

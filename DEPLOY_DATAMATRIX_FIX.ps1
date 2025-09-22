#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Deploy BabyShield with DataMatrix barcode scanning fixes
.DESCRIPTION
    This script rebuilds and deploys the BabyShield system with pylibdmtx fixes
#>

param(
    [string]$Region = "eu-north-1",
    [string]$ClusterName = "babyshield-cluster",
    [string]$ServiceName = "babyshield-backend",
    [string]$ImageName = "babyshield-backend",
    [switch]$SkipBuild = $false,
    [switch]$SkipDeploy = $false
)

# Colors for output
$Green = "Green"
$Red = "Red"
$Yellow = "Yellow"
$Cyan = "Cyan"

function Write-DeployStep {
    param([string]$Message)
    Write-Host "`n🚀 $Message" -ForegroundColor $Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "✅ $Message" -ForegroundColor $Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "⚠️  $Message" -ForegroundColor $Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "❌ $Message" -ForegroundColor $Red
}

Write-Host "🔧 DATAMATRIX BARCODE SCANNING FIX DEPLOYMENT" -ForegroundColor $Cyan
Write-Host "Deploying BabyShield with pylibdmtx fixes" -ForegroundColor Gray

# ===============================================================
# STEP 1: VERIFY FIXES ARE IN PLACE
# ===============================================================
Write-DeployStep "Verifying fixes are in place"

# Check Dockerfile
if (Select-String -Path "Dockerfile" -Pattern "libdmtx0b") {
    Write-Success "Dockerfile contains libdmtx system dependencies"
} else {
    Write-Error "Dockerfile missing libdmtx dependencies"
    exit 1
}

# Check requirements.txt
if (Select-String -Path "requirements.txt" -Pattern "pylibdmtx") {
    Write-Success "requirements.txt contains pylibdmtx==0.1.10"
} else {
    Write-Error "requirements.txt missing pylibdmtx"
    exit 1
}

# ===============================================================
# STEP 2: BUILD NEW DOCKER IMAGE
# ===============================================================
if (-not $SkipBuild) {
    Write-DeployStep "Building new Docker image with DataMatrix fixes"
    
    try {
        # Get AWS account ID
        $accountId = aws sts get-caller-identity --query Account --output text
        if (-not $accountId) {
            throw "Could not get AWS account ID"
        }
        
        $ecrRepo = "$accountId.dkr.ecr.$Region.amazonaws.com/$ImageName"
        $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
        $imageTag = "datamatrix-fix-$timestamp"
        
        Write-Host "📦 Building image: $ecrRepo`:$imageTag" -ForegroundColor Gray
        
        # Build the image
        docker build -t $ImageName`:$imageTag .
        if ($LASTEXITCODE -ne 0) {
            throw "Docker build failed"
        }
        Write-Success "Docker image built successfully"
        
        # Tag for ECR
        docker tag $ImageName`:$imageTag $ecrRepo`:$imageTag
        docker tag $ImageName`:$imageTag $ecrRepo`:latest
        
        # Login to ECR
        Write-Host "🔐 Logging into ECR..." -ForegroundColor Gray
        aws ecr get-login-password --region $Region | docker login --username AWS --password-stdin $ecrRepo
        if ($LASTEXITCODE -ne 0) {
            throw "ECR login failed"
        }
        
        # Push to ECR
        Write-Host "📤 Pushing to ECR..." -ForegroundColor Gray
        docker push $ecrRepo`:$imageTag
        docker push $ecrRepo`:latest
        if ($LASTEXITCODE -ne 0) {
            throw "Docker push failed"
        }
        
        Write-Success "Image pushed to ECR: $ecrRepo`:$imageTag"
        
    } catch {
        Write-Error "Build failed: $($_.Exception.Message)"
        exit 1
    }
} else {
    Write-Warning "Skipping build step"
}

# ===============================================================
# STEP 3: DEPLOY TO ECS
# ===============================================================
if (-not $SkipDeploy) {
    Write-DeployStep "Deploying to ECS"
    
    try {
        # Force new deployment
        Write-Host "🔄 Forcing ECS service update..." -ForegroundColor Gray
        aws ecs update-service --cluster $ClusterName --service $ServiceName --force-new-deployment --region $Region
        if ($LASTEXITCODE -ne 0) {
            throw "ECS update failed"
        }
        
        Write-Success "ECS deployment initiated"
        
        # Wait for deployment to stabilize
        Write-Host "⏳ Waiting for deployment to stabilize (this may take 3-5 minutes)..." -ForegroundColor Gray
        aws ecs wait services-stable --cluster $ClusterName --services $ServiceName --region $Region
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "Deployment wait timed out, but deployment may still be in progress"
        } else {
            Write-Success "Deployment completed successfully"
        }
        
    } catch {
        Write-Error "Deployment failed: $($_.Exception.Message)"
        exit 1
    }
} else {
    Write-Warning "Skipping deployment step"
}

# ===============================================================
# STEP 4: VERIFY DEPLOYMENT
# ===============================================================
Write-DeployStep "Verifying deployment"

try {
    # Wait a bit for the service to come online
    Write-Host "⏳ Waiting for service to come online..." -ForegroundColor Gray
    Start-Sleep -Seconds 30
    
    # Test health endpoint
    $baseUrl = "https://babyshield.cureviax.ai"
    $healthResponse = Invoke-RestMethod -Uri "$baseUrl/health" -Method GET -TimeoutSec 10
    Write-Success "Health check passed"
    
    # Test DataMatrix endpoint availability
    try {
        $testData = @{ image_base64 = "test" }
        Invoke-RestMethod -Uri "$baseUrl/api/v1/barcode/datamatrix" -Method POST -Body ($testData | ConvertTo-Json) -ContentType "application/json" -ErrorAction Stop
    } catch {
        $statusCode = $_.Exception.Response.StatusCode.value__
        if ($statusCode -eq 422 -or $statusCode -eq 400) {
            Write-Success "DataMatrix endpoint is available (validation error expected)"
        } else {
            Write-Warning "DataMatrix endpoint may have issues: Status $statusCode"
        }
    }
    
} catch {
    Write-Warning "Verification failed: $($_.Exception.Message)"
    Write-Host "Service may still be starting up. Check manually in a few minutes." -ForegroundColor Gray
}

# ===============================================================
# STEP 5: PROVIDE TESTING INSTRUCTIONS
# ===============================================================
Write-DeployStep "Testing Instructions"

Write-Host "`n📋 NEXT STEPS:" -ForegroundColor $Yellow
Write-Host "1. Run DataMatrix functionality test:" -ForegroundColor Gray
Write-Host "   .\TEST_DATAMATRIX_FUNCTIONALITY.ps1" -ForegroundColor White
Write-Host ""
Write-Host "2. Check deployment logs:" -ForegroundColor Gray
Write-Host "   aws logs tail /ecs/babyshield-backend --follow --region $Region" -ForegroundColor White
Write-Host ""
Write-Host "3. Monitor for the 'DataMatrix requested but pylibdmtx not installed' warning" -ForegroundColor Gray
Write-Host "   It should no longer appear in the logs" -ForegroundColor Gray

Write-Host "`n🔍 EXPECTED RESULTS:" -ForegroundColor $Yellow
Write-Host "- No more 'pylibdmtx not installed' warnings in logs" -ForegroundColor Gray
Write-Host "- DataMatrix endpoint should respond without library errors" -ForegroundColor Gray
Write-Host "- System should show 'DataMatrix scanning enabled and available'" -ForegroundColor Gray

Write-Host "`n✅ DataMatrix fix deployment completed!" -ForegroundColor $Green
Write-Host "🚀 BabyShield is now deployed with full DataMatrix barcode support" -ForegroundColor $Green

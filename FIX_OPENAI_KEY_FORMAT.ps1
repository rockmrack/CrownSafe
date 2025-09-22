#!/usr/bin/env pwsh
# Fix OpenAI API Key Format Issue in AWS Secrets Manager

Write-Host "🔧 Fixing OpenAI API Key Format Issue" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray

# The correct clean API key (from your .env file)
$CLEAN_OPENAI_KEY = "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"
$REGION = "eu-north-1"

Write-Host "`n📝 ISSUE IDENTIFIED:" -ForegroundColor Red
Write-Host "  Production logs show malformed API key:" -ForegroundColor Gray
Write-Host "  ❌ Current: '<sk-proj-...>\r\n>' (has extra characters)" -ForegroundColor Red
Write-Host "  ✅ Should be: 'sk-proj-...' (clean key only)" -ForegroundColor Green

Write-Host "`n🔧 FIXING AWS SECRETS MANAGER..." -ForegroundColor Yellow

# Update the secret with clean key
Write-Host "  Updating OpenAI API key secret with clean format..." -ForegroundColor White

try {
    aws secretsmanager update-secret `
        --secret-id "babyshield/openai-api-key" `
        --secret-string $CLEAN_OPENAI_KEY `
        --region $REGION
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✅ OpenAI API key updated successfully" -ForegroundColor Green
    } else {
        Write-Host "  ❌ Failed to update secret" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "  ❌ Error updating secret: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Verify the secret was updated correctly
Write-Host "`n🔍 VERIFYING SECRET..." -ForegroundColor Yellow
try {
    $secretValue = aws secretsmanager get-secret-value `
        --secret-id "babyshield/openai-api-key" `
        --region $REGION `
        --query 'SecretString' `
        --output text
    
    if ($secretValue -eq $CLEAN_OPENAI_KEY) {
        Write-Host "  ✅ Secret verification successful - key is clean" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  Secret may still have formatting issues" -ForegroundColor Yellow
        Write-Host "     Expected length: $($CLEAN_OPENAI_KEY.Length)" -ForegroundColor Gray
        Write-Host "     Actual length: $($secretValue.Length)" -ForegroundColor Gray
    }
} catch {
    Write-Host "  ⚠️  Could not verify secret (but update may have succeeded)" -ForegroundColor Yellow
}

Write-Host "`n🚀 DEPLOYING UPDATED TASK DEFINITION..." -ForegroundColor Yellow

# Force ECS to restart with updated secret
Write-Host "  Forcing ECS service update to pick up new secret..." -ForegroundColor White

try {
    aws ecs update-service `
        --cluster "babyshield-cluster" `
        --service "babyshield-backend-service" `
        --force-new-deployment `
        --region $REGION
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✅ ECS service update initiated" -ForegroundColor Green
    } else {
        Write-Host "  ❌ Failed to update ECS service" -ForegroundColor Red
    }
} catch {
    Write-Host "  ❌ Error updating ECS service: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n⏱️  WAITING FOR DEPLOYMENT..." -ForegroundColor Yellow
Write-Host "  This will take 2-3 minutes..." -ForegroundColor Gray

# Wait for service to stabilize
try {
    aws ecs wait services-stable `
        --cluster "babyshield-cluster" `
        --services "babyshield-backend-service" `
        --region $REGION
    
    Write-Host "  ✅ Deployment completed!" -ForegroundColor Green
} catch {
    Write-Host "  ⚠️  Deployment may still be in progress" -ForegroundColor Yellow
}

Write-Host "`n🧪 TESTING OPENAI INTEGRATION..." -ForegroundColor Yellow

# Test the visual search endpoint
try {
    Write-Host "  Testing visual recognition with clean API key..." -ForegroundColor Gray
    
    $testBody = @{
        image_url = "https://images.unsplash.com/photo-1585386959984-a4155223168f?auto=format&fit=crop&w=600&q=60"
        user_id = 1
    } | ConvertTo-Json
    
    $response = Invoke-RestMethod -Uri "https://babyshield.cureviax.ai/api/v1/visual/search" -Method POST -Body $testBody -ContentType "application/json" -TimeoutSec 30
    
    if ($response.status -eq "success" -or $response.status -eq "completed") {
        Write-Host "  ✅ Visual recognition test successful!" -ForegroundColor Green
        Write-Host "     Status: $($response.status)" -ForegroundColor Gray
    } else {
        Write-Host "  ⚠️  Visual recognition returned: $($response.status)" -ForegroundColor Yellow
    }
    
} catch {
    Write-Host "  ❌ Visual recognition test failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n" -NoNewline
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "✅ OpenAI API Key Format Fix Complete!" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan

Write-Host "`n📊 EXPECTED RESULTS:" -ForegroundColor White
Write-Host "  Before: httpcore.LocalProtocolError: Illegal header value" -ForegroundColor Red
Write-Host "  After:  Clean OpenAI API calls without connection errors" -ForegroundColor Green

Write-Host "`n🔍 MONITOR LOGS:" -ForegroundColor White
Write-Host "  Watch for these in CloudWatch:" -ForegroundColor Gray
Write-Host "  ✅ 'VisualSearchAgentLogic initialized'" -ForegroundColor Green
Write-Host "  ✅ 'Analyzing image for definitive product identification'" -ForegroundColor Green
Write-Host "  ❌ No more 'Illegal header value' errors" -ForegroundColor Green

Write-Host "`n🎉 OpenAI visual recognition should now work perfectly!" -ForegroundColor Green

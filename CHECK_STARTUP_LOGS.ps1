#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Check startup logs for the latest BabyShield deployment
.DESCRIPTION
    Retrieves and analyzes the startup logs to identify any remaining issues
#>

param(
    [string]$Region = "eu-north-1",
    [string]$LogGroup = "/ecs/babyshield-backend"
)

Write-Host "🔍 CHECKING LATEST STARTUP LOGS" -ForegroundColor Cyan
Write-Host "Looking for container: b1b04a32afad4c2bbffa09f76004b529" -ForegroundColor Gray

# Get logs from the last 30 minutes
$startTime = (Get-Date).AddMinutes(-30).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')

Write-Host "`n📋 Fetching startup logs..." -ForegroundColor Yellow

try {
    # Get recent logs
    $logEvents = aws logs filter-log-events --log-group-name $LogGroup --start-time $startTime --filter-pattern '"b1b04a32afad4c2bbffa09f76004b529"' --region $Region --max-items 100 --query 'events[*].[timestamp,message]' --output text
    
    if ($logEvents) {
        Write-Host "`n🔍 ANALYZING STARTUP MESSAGES:" -ForegroundColor Cyan
        
        # Check for key startup indicators
        $lines = $logEvents -split "`n"
        $dataMatrixFound = $false
        $pyZbarFound = $false
        $openAIKeyFound = $false
        $startupComplete = $false
        
        foreach ($line in $lines) {
            if ($line -like "*DataMatrix*") {
                $dataMatrixFound = $true
                if ($line -like "*not installed*") {
                    Write-Host "❌ DataMatrix Issue: $line" -ForegroundColor Red
                } elseif ($line -like "*enabled and available*") {
                    Write-Host "✅ DataMatrix Success: $line" -ForegroundColor Green
                } else {
                    Write-Host "ℹ️  DataMatrix Info: $line" -ForegroundColor Yellow
                }
            }
            
            if ($line -like "*PyZbar*") {
                $pyZbarFound = $true
                Write-Host "✅ PyZbar: $line" -ForegroundColor Green
            }
            
            if ($line -like "*OpenAI API key*") {
                $openAIKeyFound = $true
                Write-Host "✅ OpenAI Handling: $line" -ForegroundColor Green
            }
            
            if ($line -like "*Application startup complete*") {
                $startupComplete = $true
                Write-Host "✅ Startup Complete: $line" -ForegroundColor Green
            }
            
            if ($line -like "*ERROR*" -or $line -like "*CRITICAL*") {
                Write-Host "❌ Error Found: $line" -ForegroundColor Red
            }
        }
        
        Write-Host "`n📊 STARTUP ANALYSIS SUMMARY:" -ForegroundColor Cyan
        Write-Host "  DataMatrix Messages Found: $dataMatrixFound" -ForegroundColor $(if ($dataMatrixFound) { "Green" } else { "Red" })
        Write-Host "  PyZbar Messages Found: $pyZbarFound" -ForegroundColor $(if ($pyZbarFound) { "Green" } else { "Red" })
        Write-Host "  OpenAI Handling Found: $openAIKeyFound" -ForegroundColor $(if ($openAIKeyFound) { "Green" } else { "Red" })
        Write-Host "  Startup Completed: $startupComplete" -ForegroundColor $(if ($startupComplete) { "Green" } else { "Yellow" })
        
    } else {
        Write-Host "❌ No logs found for container b1b04a32afad4c2bbffa09f76004b529" -ForegroundColor Red
        Write-Host "This could mean:" -ForegroundColor Yellow
        Write-Host "  - Container is still starting up" -ForegroundColor Gray
        Write-Host "  - Different container ID is active" -ForegroundColor Gray
        Write-Host "  - Logs haven't been indexed yet" -ForegroundColor Gray
    }
    
} catch {
    Write-Host "❌ Error retrieving logs: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Try running: aws logs describe-log-groups --region $Region" -ForegroundColor Yellow
}

Write-Host "`n🔧 NEXT STEPS:" -ForegroundColor Cyan
Write-Host "1. Run: .\TEST_ALL_FIXES.ps1 - to test all functionality" -ForegroundColor Gray
Write-Host "2. Check specific issues found above" -ForegroundColor Gray
Write-Host "3. Redeploy if critical issues remain" -ForegroundColor Gray

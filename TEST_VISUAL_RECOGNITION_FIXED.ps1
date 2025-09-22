#!/usr/bin/env pwsh
# Test Visual Recognition After OpenAI Fix

param(
    [string]$BaseUrl = "https://babyshield.cureviax.ai"
)

Write-Host "🔍 Testing BabyShield Visual Recognition" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray

# Test image URL
$TestImageUrl = "https://images.unsplash.com/photo-1585386959984-a4155223168f?auto=format&fit=crop&w=1000&q=80"

# Download test image
$testImagePath = "$env:TEMP\baby_product_test.jpg"
Write-Host "`n📥 Downloading test image..." -ForegroundColor Yellow
try {
    Invoke-WebRequest -Uri $TestImageUrl -OutFile $testImagePath -UseBasicParsing
    Write-Host "✅ Test image downloaded: $testImagePath" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to download test image: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Test 1: Simple Visual Search (should work even without OpenAI)
Write-Host "`n🔍 Test 1: Basic Visual Search..." -ForegroundColor Yellow
try {
    $response1 = Invoke-RestMethod -Uri "$BaseUrl/api/v1/visual/search" -Method POST -Body @{
        image_url = $TestImageUrl
        user_id = 1
    } -ContentType "application/json"
    
    Write-Host "✅ Basic visual search: SUCCESS" -ForegroundColor Green
    Write-Host "   Status: $($response1.status)" -ForegroundColor Gray
} catch {
    Write-Host "❌ Basic visual search failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 2: Advanced Visual Recognition (requires OpenAI)
Write-Host "`n🔍 Test 2: Advanced Visual Recognition..." -ForegroundColor Yellow
try {
    # Create multipart form data
    Add-Type -AssemblyName System.Net.Http
    $httpClient = [System.Net.Http.HttpClient]::new()
    $multipartContent = [System.Net.Http.MultipartFormDataContent]::new()
    
    # Add image file
    $fileStream = [System.IO.File]::OpenRead($testImagePath)
    $streamContent = [System.Net.Http.StreamContent]::new($fileStream)
    $streamContent.Headers.ContentType = [System.Net.Http.Headers.MediaTypeHeaderValue]::Parse("image/jpeg")
    $multipartContent.Add($streamContent, "image", "test.jpg")
    
    # Make request
    $uri = "$BaseUrl/api/v1/advanced/visual/recognize?user_id=1&check_for_defects=true&confidence_threshold=0.5"
    $response2 = $httpClient.PostAsync($uri, $multipartContent).Result
    $responseContent = $response2.Content.ReadAsStringAsync().Result
    
    $fileStream.Dispose()
    $httpClient.Dispose()
    
    $statusCode = [int]$response2.StatusCode
    Write-Host "   HTTP Status: $statusCode" -ForegroundColor $(if ($statusCode -eq 200) { "Green" } else { "Red" })
    
    if ($statusCode -eq 200) {
        $jsonResponse = $responseContent | ConvertFrom-Json
        Write-Host "✅ Advanced visual recognition: SUCCESS" -ForegroundColor Green
        Write-Host "   Status: $($jsonResponse.status)" -ForegroundColor Gray
        
        if ($jsonResponse.products_identified) {
            Write-Host "   Products found: $($jsonResponse.products_identified.Count)" -ForegroundColor Gray
            foreach ($product in $jsonResponse.products_identified) {
                Write-Host "   📦 Product: $($product.product_name)" -ForegroundColor Gray
                Write-Host "   🎯 Confidence: $($product.confidence)" -ForegroundColor Gray
                Write-Host "   ⚠️  Recall Status: $($product.recall_status)" -ForegroundColor Gray
            }
        }
        
        if ($jsonResponse.defects_detected) {
            $defectCount = ($jsonResponse.defects_detected | Measure-Object).Count
            Write-Host "   🔍 Defects detected: $defectCount" -ForegroundColor Gray
        }
        
        Write-Host "`n🎉 VISUAL RECOGNITION IS FULLY WORKING!" -ForegroundColor Green
        
    } else {
        Write-Host "❌ Advanced visual recognition failed" -ForegroundColor Red
        Write-Host "   Response: $responseContent" -ForegroundColor Gray
        
        if ($responseContent -like "*OpenAI API key*") {
            Write-Host "`n⚠️  OpenAI API key still not configured properly!" -ForegroundColor Yellow
            Write-Host "   Run: .\FIX_OPENAI_VISUAL_RECOGNITION.ps1" -ForegroundColor White
        }
    }
    
} catch {
    Write-Host "❌ Advanced visual recognition failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 3: Check logs for OpenAI status
Write-Host "`n📋 Test 3: Checking deployment logs..." -ForegroundColor Yellow
try {
    # Get recent logs from AWS CloudWatch
    $logEvents = aws logs describe-log-streams `
        --log-group-name "/ecs/babyshield-backend" `
        --order-by LastEventTime `
        --descending `
        --max-items 1 `
        --region "eu-north-1" `
        --query 'logStreams[0].logStreamName' `
        --output text 2>$null
    
    if ($logEvents -and $logEvents -ne "None") {
        Write-Host "Recent OpenAI-related logs:" -ForegroundColor White
        $logs = aws logs get-log-events `
            --log-group-name "/ecs/babyshield-backend" `
            --log-stream-name $logEvents `
            --start-time $((Get-Date).AddMinutes(-10).ToUnixTimeMilliseconds()) `
            --region "eu-north-1" `
            --query 'events[?contains(message, `OpenAI`) || contains(message, `visual`)].message' `
            --output text 2>$null
        
        if ($logs) {
            $logs -split "`n" | ForEach-Object {
                if ($_ -like "*OpenAI API key not configured*") {
                    Write-Host "   ❌ $_" -ForegroundColor Red
                } elseif ($_ -like "*OpenAI*available*" -or $_ -like "*visual*available*") {
                    Write-Host "   ✅ $_" -ForegroundColor Green
                } else {
                    Write-Host "   ℹ️  $_" -ForegroundColor Gray
                }
            }
        } else {
            Write-Host "   No OpenAI-related logs found in recent messages" -ForegroundColor Gray
        }
    } else {
        Write-Host "   Unable to fetch logs (AWS CLI may not be configured)" -ForegroundColor Gray
    }
} catch {
    Write-Host "   Could not check logs: $($_.Exception.Message)" -ForegroundColor Gray
}

Write-Host "`n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host "🎯 Summary:" -ForegroundColor Cyan

if (Test-Path $testImagePath) {
    Remove-Item $testImagePath -Force
}

Write-Host "   Visual Recognition Test Complete!" -ForegroundColor White
Write-Host "   If advanced recognition failed, run the fix script:" -ForegroundColor Gray
Write-Host "   .\FIX_OPENAI_VISUAL_RECOGNITION.ps1" -ForegroundColor White

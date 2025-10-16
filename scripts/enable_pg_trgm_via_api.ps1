# Enable pg_trgm extension via admin API endpoint
# This is the cleanest way to enable the extension without needing ECS exec or direct DB access

Write-Host "`n[*] Enabling pg_trgm PostgreSQL Extension via Admin API`n" -ForegroundColor Cyan

# Production API URL
$API_URL = "https://babyshield.cureviax.ai"

Write-Host "Step 1: Authenticate as admin user..." -ForegroundColor Yellow
Write-Host "You need to manually get an admin access token first." -ForegroundColor Yellow
Write-Host ""
Write-Host "To get a token, run:" -ForegroundColor White
Write-Host '  $body = @{ username = "admin@example.com"; password = "your-password" } | ConvertTo-Json' -ForegroundColor Gray
Write-Host "  `$auth = Invoke-RestMethod -Uri `"$API_URL/api/v1/auth/login`" -Method POST -Body `$body -ContentType `"application/json`"" -ForegroundColor Gray
Write-Host '  $token = $auth.access_token' -ForegroundColor Gray
Write-Host ""

$token = Read-Host "Enter your admin access token (or press Ctrl+C to exit)"

if ([string]::IsNullOrWhiteSpace($token)) {
    Write-Host "[X] No token provided. Exiting." -ForegroundColor Red
    exit 1
}

Write-Host "`nStep 2: Calling pg_trgm enablement endpoint...`n" -ForegroundColor Yellow

try {
    $headers = @{
        "Authorization" = "Bearer $token"
        "Content-Type"  = "application/json"
    }
    
    $response = Invoke-RestMethod -Uri "$API_URL/api/v1/admin/database/enable-pg-trgm" -Method POST -Headers $headers -ErrorAction Stop
    
    Write-Host "[OK] Success! pg_trgm extension enabled`n" -ForegroundColor Green
    
    Write-Host "Results:" -ForegroundColor Cyan
    Write-Host "  Extension Status: $($response.data.extension_status)" -ForegroundColor White
    Write-Host "  Extension Version: $($response.data.extension_version)" -ForegroundColor White
    Write-Host "  Similarity Test: $($response.data.similarity_test)" -ForegroundColor White
    Write-Host "  Index Status: $($response.data.index_status)" -ForegroundColor White
    
    if ($response.data.existing_indexes -and $response.data.existing_indexes.Count -gt 0) {
        Write-Host "  Existing Indexes: $($response.data.existing_indexes -join ', ')" -ForegroundColor White
    }
    
    if ($response.data.indexes_created -and $response.data.indexes_created.Count -gt 0) {
        Write-Host "  Indexes Created: $($response.data.indexes_created -join ', ')" -ForegroundColor White
    }
    
    Write-Host "`n[OK] $($response.data.message)`n" -ForegroundColor Green
    
    Write-Host "Step 3: Test search endpoint..." -ForegroundColor Yellow
    Write-Host "Run this command to verify search is now working:" -ForegroundColor Cyan
    Write-Host '  $searchBody = @{ query = "baby"; limit = 10 } | ConvertTo-Json' -ForegroundColor Gray
    Write-Host "  Invoke-RestMethod -Uri `"$API_URL/api/v1/search/advanced`" -Method POST -Body `$searchBody -ContentType `"application/json`"" -ForegroundColor Gray
    Write-Host ""
}
catch {
    Write-Host "[ERROR] $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Common issues:" -ForegroundColor Yellow
    Write-Host "  1. Invalid or expired token" -ForegroundColor White
    Write-Host "  2. User doesn't have admin privileges" -ForegroundColor White
    Write-Host "  3. API endpoint not deployed yet" -ForegroundColor White
    Write-Host ""
    
    if ($_.Exception.Response) {
        $statusCode = $_.Exception.Response.StatusCode.value__
        Write-Host "HTTP Status Code: $statusCode" -ForegroundColor Red
        
        if ($statusCode -eq 403) {
            Write-Host "[X] Access denied. This endpoint requires admin privileges." -ForegroundColor Red
        }
        elseif ($statusCode -eq 401) {
            Write-Host "[X] Authentication failed. Token may be invalid or expired." -ForegroundColor Red
        }
    }
    
    exit 1
}

Write-Host "[DONE] Search functionality should now be restored." -ForegroundColor Green

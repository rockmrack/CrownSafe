# Quick Security Headers Test
# Tests the CORRECT endpoint that uses middleware

Write-Host "`n=== SECURITY HEADERS TEST ===" -ForegroundColor Cyan
Write-Host "Testing: http://localhost:8001/api/v1/health`n" -ForegroundColor Yellow

# Test with HEAD request
Write-Host "Testing with HEAD request..." -ForegroundColor Green
$response = Invoke-WebRequest -Uri "http://localhost:8001/api/v1/health" -Method HEAD

Write-Host "`nSecurity Headers Found:" -ForegroundColor Cyan
Write-Host "----------------------------------------" -ForegroundColor Gray

$securityHeaders = @(
    "X-Frame-Options",
    "X-Content-Type-Options",
    "X-XSS-Protection",
    "Referrer-Policy",
    "Content-Security-Policy",
    "Permissions-Policy",
    "X-RateLimit-Limit",
    "X-RateLimit-Remaining"
)

$found = 0
$total = $securityHeaders.Count

foreach ($header in $securityHeaders) {
    if ($response.Headers.ContainsKey($header)) {
        $value = $response.Headers[$header]
        if ($value.Length -gt 50) {
            $value = $value.Substring(0, 47) + "..."
        }
        Write-Host "[OK] $header`: $value" -ForegroundColor Green
        $found++
    } else {
        Write-Host "[FAIL] $header`: MISSING" -ForegroundColor Red
    }
}

Write-Host "`n========================================" -ForegroundColor Gray
Write-Host "Result: $found/$total security headers present" -ForegroundColor $(if ($found -eq $total) { "Green" } else { "Yellow" })

if ($found -eq $total) {
    Write-Host "`n✓ SUCCESS: All security headers are active!" -ForegroundColor Green
    Write-Host "Your API is protected with OWASP-compliant security headers.`n" -ForegroundColor Cyan
} elseif ($found -gt 0) {
    Write-Host "`n⚠ PARTIAL: Some headers present, some missing." -ForegroundColor Yellow
    Write-Host "This might be normal depending on your configuration.`n" -ForegroundColor Gray
} else {
    Write-Host "`n✗ FAILED: No security headers found." -ForegroundColor Red
    Write-Host "Check that the server is running and middleware is activated.`n" -ForegroundColor Yellow
}

Write-Host "========================================`n" -ForegroundColor Gray


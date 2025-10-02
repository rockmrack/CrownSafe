# scripts/create_smoke_test_user.ps1
# Creates or verifies the smoke test user exists

[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [string]$BASE,
  
  [Parameter(Mandatory = $true)]
  [string]$Email,
  
  [Parameter(Mandatory = $true)]
  [string]$Password
)

$ErrorActionPreference = 'Stop'

Write-Host "Creating smoke test user at: $BASE"
Write-Host "Email: $Email"

# Prepare registration payload
$payload = @{
  email = $Email
  password = $Password
  confirm_password = $Password
} | ConvertTo-Json

try {
  # Try to register the user
  Write-Host "`nAttempting to register user..."
  $response = Invoke-RestMethod -Uri "$BASE/api/v1/auth/register" `
    -Method Post `
    -ContentType 'application/json' `
    -Body $payload `
    -ErrorAction Stop
  
  Write-Host "User created successfully!" -ForegroundColor Green
  Write-Host "Response: $($response | ConvertTo-Json -Compress)"
} catch {
  $statusCode = $_.Exception.Response.StatusCode.value__
  $errorBody = $_.ErrorDetails.Message
  
  if ($statusCode -eq 400 -and $errorBody -like '*already registered*') {
    Write-Host "User already exists (that's OK)" -ForegroundColor Yellow
  } else {
    Write-Host "Registration failed: $errorBody" -ForegroundColor Red
    throw
  }
}

# Verify we can login
Write-Host "`nVerifying login..."
# Use hashtable for automatic URL encoding of special characters
$formData = @{
  username = $Email
  password = $Password
  grant_type = 'password'
}
try {
  $login = Invoke-RestMethod -Uri "$BASE/api/v1/auth/token" `
    -Method Post `
    -ContentType 'application/x-www-form-urlencoded' `
    -Body $formData `
    -ErrorAction Stop
  
  $token = $login.access_token
  if (-not $token) { $token = $login.token }
  if (-not $token -and $login.data) { $token = $login.data.access_token }
  
  if ($token) {
    Write-Host "Login successful!" -ForegroundColor Green
    $tokenPreview = $token.Substring(0, [Math]::Min(20, $token.Length))
    Write-Host "Token (first 20 chars): ${tokenPreview}..."
  } else {
    Write-Host "Login succeeded but no token found in response" -ForegroundColor Red
    Write-Host "Response: $($login | ConvertTo-Json)"
    exit 1
  }
} catch {
  Write-Host "Login failed: $($_.Exception.Message)" -ForegroundColor Red
  Write-Host "Error: $($_.ErrorDetails.Message)"
  exit 1
}

Write-Host "`n========================================"  -ForegroundColor Cyan
Write-Host "Smoke test user is ready!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "`nAdd these secrets to GitHub:"
Write-Host "Repository -> Settings -> Secrets and variables -> Actions -> New repository secret"
Write-Host ""
Write-Host "SMOKE_TEST_EMAIL     = $Email" -ForegroundColor Yellow
Write-Host "SMOKE_TEST_PASSWORD  = $Password" -ForegroundColor Yellow
Write-Host ""

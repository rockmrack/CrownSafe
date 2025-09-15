# Quick test to verify the fix works
Write-Host "`n🧪 QUICK LOCAL TEST" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Yellow

# Build the fixed image
Write-Host "`n1. Building fixed image..." -ForegroundColor Green
docker build -f Dockerfile.final -t babyshield-backend:test-local . 2>&1 | Out-Null

if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✅ Build successful!" -ForegroundColor Green
    
    # Run and capture output
    Write-Host "`n2. Testing for errors..." -ForegroundColor Green
    $output = docker run --rm babyshield-backend:test-local python -c @"
import sys
errors = []
try:
    import openai
    print('✅ openai')
except: errors.append('openai')
try:
    import qrcode
    print('✅ qrcode')
except: errors.append('qrcode')
try:
    import pyzbar
    print('✅ pyzbar')
except: errors.append('pyzbar')
try:
    import reportlab
    print('✅ reportlab')
except: errors.append('reportlab')
try:
    import jwt
    print('✅ jwt')
except: errors.append('jwt')
try:
    import prometheus_client
    print('✅ prometheus_client')
except: errors.append('prometheus_client')
try:
    import aiosmtplib
    print('✅ aiosmtplib')
except: errors.append('aiosmtplib')
try:
    import firebase_admin
    print('✅ firebase_admin')
except: errors.append('firebase_admin')

if errors:
    print(f'❌ Missing: {errors}')
    sys.exit(1)
else:
    print('✅ ALL MODULES PRESENT!')
"@ 2>&1

    Write-Host $output
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "`n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
        Write-Host "🎉 SUCCESS! ALL ERRORS FIXED!" -ForegroundColor Green -BackgroundColor Black
        Write-Host "Ready to deploy to AWS!" -ForegroundColor Green
        Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
    } else {
        Write-Host "`n❌ Some modules still missing" -ForegroundColor Red
    }
} else {
    Write-Host "   ❌ Build failed" -ForegroundColor Red
}

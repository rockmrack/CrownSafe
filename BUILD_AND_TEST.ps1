# PowerShell script to build and test the FIXED Docker image

Write-Host "`n====================================" -ForegroundColor Green
Write-Host "  BUILDING FIXED DOCKER IMAGE" -ForegroundColor Green
Write-Host "====================================" -ForegroundColor Green

# Step 1: Build the new image with all fixes
Write-Host "`n📦 Building new image with ALL dependencies..." -ForegroundColor Cyan
docker build -f Dockerfile.final -t babyshield-backend:complete .

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ Build successful!" -ForegroundColor Green
    
    # Step 2: Test the new image locally
    Write-Host "`n🧪 Testing the new image..." -ForegroundColor Cyan
    Write-Host "Starting container (press Ctrl+C to stop)..." -ForegroundColor Yellow
    
    docker run --rm `
        -p 8001:8001 `
        -e DATABASE_URL="sqlite:///./babyshield_test.db" `
        -e OPENAI_API_KEY="sk-test-key" `
        -e JWT_SECRET_KEY="test-jwt-key" `
        -e SECRET_KEY="test-secret-key" `
        -e ENCRYPTION_KEY="test-encryption-key" `
        babyshield-backend:complete
        
} else {
    Write-Host "`n❌ Build failed! Check the errors above." -ForegroundColor Red
    exit 1
}

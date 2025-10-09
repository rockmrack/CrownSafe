# Enable pg_trgm extension in production PostgreSQL database
# This fixes the "function similarity(text, unknown) does not exist" error

Write-Host "Enabling pg_trgm extension in production database..." -ForegroundColor Yellow

# Connection details
$DB_HOST = "babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com"
$DB_USER = "babyshield_user"
$DB_PASS = "MandarunLabadiena25!"
$DB_NAME = "postgres"
$DB_PORT = "5432"

Write-Host "Connection: $DB_HOST / $DB_NAME" -ForegroundColor Cyan

# SQL commands to execute
$sqlFile = "scripts\enable_pg_trgm_prod.sql"

try {
    if (Get-Command psql -ErrorAction SilentlyContinue) {
        Write-Host "Using psql command..." -ForegroundColor Cyan
        
        # Set password environment variable
        $env:PGPASSWORD = $DB_PASS
        
        # Execute SQL file
        psql -h $DB_HOST -U $DB_USER -d $DB_NAME -p $DB_PORT -f $sqlFile
        
        Write-Host "" 
        Write-Host "SUCCESS: pg_trgm extension enabled!" -ForegroundColor Green
    }
    else {
        Write-Host "ERROR: psql not found. Please install PostgreSQL client tools." -ForegroundColor Red
        Write-Host ""
        Write-Host "Or run the SQL file manually: scripts\enable_pg_trgm_prod.sql" -ForegroundColor Yellow
    }
}
catch {
    Write-Host "ERROR: $_" -ForegroundColor Red
}
finally {
    # Clean up password environment variable
    Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "Next: Test the search endpoint with:" -ForegroundColor Cyan
Write-Host '  $body = @{ query = "baby"; limit = 10 } | ConvertTo-Json' -ForegroundColor White
Write-Host '  Invoke-WebRequest -Uri "https://babyshield.cureviax.ai/api/v1/search/advanced" -Method POST -Body $body -ContentType "application/json"' -ForegroundColor White

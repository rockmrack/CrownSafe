# Enable pg_trgm extension in production PostgreSQL database
# This fixes the "function similarity(text, unknown) does not exist" error

Write-Host "Enabling pg_trgm extension in production database..." -ForegroundColor Yellow

# Connection details
$DB_HOST = "babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com"
$DB_USER = "babyshield_user"
$DB_PASS = "MandarunLabadiena25!"
$DB_NAME = "postgres"
$DB_PORT = "5432"

# Build connection string
$connectionString = "Host=$DB_HOST;Port=$DB_PORT;Database=$DB_NAME;Username=$DB_USER;Password=$DB_PASS;SSL Mode=Require;"

Write-Host "Connection: ${DB_HOST}:${DB_PORT}/${DB_NAME}" -ForegroundColor Cyan

# SQL commands to execute
$sqlCommands = @"
-- Enable pg_trgm extension
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Verify extension
SELECT extname, extversion FROM pg_extension WHERE extname = 'pg_trgm';

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_recalls_product_trgm 
ON recalls_enhanced USING gin (lower(product_name) gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_recalls_brand_trgm 
ON recalls_enhanced USING gin (lower(brand) gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_recalls_description_trgm 
ON recalls_enhanced USING gin (lower(description) gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_recalls_hazard_trgm 
ON recalls_enhanced USING gin (lower(hazard) gin_trgm_ops);

-- Test similarity function
SELECT similarity('baby', 'baby') as exact_match;
SELECT similarity('baby', 'babe') as similar;
"@

try {
    # Try using Npgsql if available, otherwise use psql
    if (Get-Command psql -ErrorAction SilentlyContinue) {
        Write-Host "Using psql command..." -ForegroundColor Cyan
        
        # Set password environment variable
        $env:PGPASSWORD = $DB_PASS
        
        # Execute SQL
        $sqlCommands | psql -h $DB_HOST -U $DB_USER -d $DB_NAME -p $DB_PORT
        
        Write-Host "`n✅ Successfully enabled pg_trgm extension!" -ForegroundColor Green
    }
    else {
        Write-Host "❌ psql not found. Please install PostgreSQL client tools." -ForegroundColor Red
        Write-Host "`nAlternatively, run this SQL manually in pgAdmin or another PostgreSQL client:" -ForegroundColor Yellow
        Write-Host $sqlCommands -ForegroundColor White
    }
}
catch {
    Write-Host "❌ Error: $_" -ForegroundColor Red
    Write-Host "`nIf this fails, you can run the SQL manually:" -ForegroundColor Yellow
    Write-Host $sqlCommands -ForegroundColor White
}
finally {
    # Clean up password environment variable
    Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
}

Write-Host "`n📝 After enabling the extension, test the search endpoint:" -ForegroundColor Cyan
$testCommand = 'Invoke-WebRequest -Uri "https://babyshield.cureviax.ai/api/v1/search/advanced" -Method POST -Body "{\"query\":\"baby\",\"limit\":10}" -ContentType "application/json"'
Write-Host $testCommand -ForegroundColor White

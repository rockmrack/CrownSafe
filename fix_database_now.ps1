# PowerShell script to fix the database schema issue
Write-Host "==================================" -ForegroundColor Cyan
Write-Host "DATABASE SCHEMA FIX" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan

# You need to set your DATABASE_URL first
$DATABASE_URL = Read-Host -Prompt "`nEnter your DATABASE_URL (postgresql://user:pass@host:port/dbname)"

if ($DATABASE_URL -eq "") {
    Write-Host "ERROR: Database URL required!" -ForegroundColor Red
    exit 1
}

# Set environment variable
$env:DATABASE_URL = $DATABASE_URL

# Create Python fix script
$pythonScript = @'
import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL")
print(f"Connecting to database...")

try:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        # Start transaction
        trans = conn.begin()
        
        try:
            # Add missing columns
            print("Adding missing columns...")
            
            # Check and add severity
            result = conn.execute(text("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'recalls_enhanced' AND column_name = 'severity'
            """)).fetchone()
            
            if not result:
                conn.execute(text("ALTER TABLE recalls_enhanced ADD COLUMN severity VARCHAR(50)"))
                print("✅ Added 'severity' column")
            else:
                print("✓ 'severity' column already exists")
            
            # Check and add risk_category
            result = conn.execute(text("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'recalls_enhanced' AND column_name = 'risk_category'
            """)).fetchone()
            
            if not result:
                conn.execute(text("ALTER TABLE recalls_enhanced ADD COLUMN risk_category VARCHAR(100)"))
                print("✅ Added 'risk_category' column")
            else:
                print("✓ 'risk_category' column already exists")
            
            # Set defaults
            conn.execute(text("UPDATE recalls_enhanced SET severity = 'medium' WHERE severity IS NULL"))
            conn.execute(text("UPDATE recalls_enhanced SET risk_category = 'general' WHERE risk_category IS NULL"))
            
            trans.commit()
            print("\n🎉 SUCCESS! Database schema fixed!")
            
        except Exception as e:
            trans.rollback()
            raise e
            
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)
'@

$pythonScript | Out-File -FilePath "emergency_db_fix.py" -Encoding UTF8

Write-Host "`nRunning database fix..." -ForegroundColor Yellow

# Install psycopg2 if needed
pip install psycopg2-binary sqlalchemy --quiet

# Run the fix
python emergency_db_fix.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ Database fixed!" -ForegroundColor Green
    Write-Host "Testing search endpoint..." -ForegroundColor Yellow
    
    # Test the endpoint
    $response = Invoke-RestMethod -Uri "https://babyshield.cureviax.ai/api/v1/search/advanced" `
        -Method POST `
        -ContentType "application/json" `
        -Body '{"product":"test","limit":1}' `
        -ErrorAction SilentlyContinue
    
    if ($response.ok -eq $true) {
        Write-Host "✅ Search API is now WORKING!" -ForegroundColor Green
    } else {
        Write-Host "⚠️ Search might need a moment to update" -ForegroundColor Yellow
    }
} else {
    Write-Host "❌ Fix failed. Try Option 2 or 3 below." -ForegroundColor Red
}

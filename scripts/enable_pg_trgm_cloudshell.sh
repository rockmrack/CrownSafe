# Enable pg_trgm Extension via AWS CloudShell
# This script runs directly in CloudShell which has access to RDS

# Database connection details
DB_HOST="babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com"
DB_NAME="postgres"
DB_USER="babyshield_user"
DB_PASS="MandarunLabadiena25!"

echo "=========================================="
echo "  Enabling pg_trgm Extension on RDS"
echo "=========================================="
echo ""

# Check if psql is installed
if ! command -v psql &> /dev/null; then
    echo "Installing PostgreSQL client..."
    sudo yum install -y postgresql15
fi

echo "Connecting to production database..."
echo "Host: $DB_HOST"
echo "Database: $DB_NAME"
echo ""

# Enable pg_trgm extension
echo "Step 1: Enabling pg_trgm extension..."
PGPASSWORD=$DB_PASS psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;" 2>&1

if [ $? -eq 0 ]; then
    echo "✓ pg_trgm extension enabled successfully"
else
    echo "✗ Failed to enable pg_trgm extension"
    exit 1
fi

echo ""
echo "Step 2: Verifying extension..."
PGPASSWORD=$DB_PASS psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'pg_trgm';"

echo ""
echo "Step 3: Testing similarity function..."
PGPASSWORD=$DB_PASS psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT similarity('baby', 'baby') as exact_match, similarity('baby', 'babe') as similar;"

echo ""
echo "Step 4: Creating GIN indexes for fast search..."
PGPASSWORD=$DB_PASS psql -h $DB_HOST -U $DB_USER -d $DB_NAME << 'EOF'
CREATE INDEX IF NOT EXISTS idx_recalls_product_trgm ON recalls_enhanced USING gin (lower(product_name) gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_recalls_brand_trgm ON recalls_enhanced USING gin (lower(brand) gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_recalls_description_trgm ON recalls_enhanced USING gin (lower(description) gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_recalls_hazard_trgm ON recalls_enhanced USING gin (lower(hazard) gin_trgm_ops);
EOF

if [ $? -eq 0 ]; then
    echo "✓ All GIN indexes created successfully"
else
    echo "✗ Some indexes may have failed"
fi

echo ""
echo "Step 5: Verifying indexes..."
PGPASSWORD=$DB_PASS psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT indexname FROM pg_indexes WHERE tablename = 'recalls_enhanced' AND indexname LIKE '%trgm%' ORDER BY indexname;"

echo ""
echo "=========================================="
echo "  ✓ pg_trgm Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Test search: https://babyshield.cureviax.ai/api/v1/search/advanced"
echo "  2. Check CloudWatch logs (pg_trgm warning should disappear)"
echo ""

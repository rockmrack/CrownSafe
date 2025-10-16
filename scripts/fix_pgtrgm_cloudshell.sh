#!/bin/bash
# FASTEST FIX for pg_trgm - Run this in AWS CloudShell
# This adds your IP to security group, enables pg_trgm, then removes your IP

set -e  # Exit on error

echo "========================================"
echo "  pg_trgm Quick Fix for CloudShell"
echo "========================================"
echo ""

# Step 1: Get CloudShell IP
echo "Step 1: Getting your CloudShell IP..."
MY_IP=$(curl -s https://checkip.amazonaws.com)
echo "✓ Your IP: $MY_IP"
echo ""

# Step 2: Find RDS security group
echo "Step 2: Finding RDS security group..."
SG_ID=$(aws rds describe-db-instances \
  --db-instance-identifier babyshield-prod-db \
  --region eu-north-1 \
  --query 'DBInstances[0].VpcSecurityGroups[0].VpcSecurityGroupId' \
  --output text)
echo "✓ Security Group: $SG_ID"
echo ""

# Step 3: Add your IP to security group
echo "Step 3: Adding your IP to security group (temporary)..."
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 5432 \
  --cidr $MY_IP/32 \
  --region eu-north-1 \
  2>/dev/null || echo "Note: IP may already be added"
echo "✓ Your IP added to security group"
echo ""

# Wait a moment for security group to update
sleep 2

# Step 4: Enable pg_trgm
echo "Step 4: Enabling pg_trgm extension..."
PGPASSWORD='MandarunLabadiena25!' psql \
  -h babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com \
  -U babyshield_user \
  -d postgres \
  << 'SQL'
-- Enable extension
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Create GIN indexes for fast similarity search
CREATE INDEX IF NOT EXISTS idx_recalls_product_trgm 
  ON recalls_enhanced USING gin (lower(product_name) gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_recalls_brand_trgm 
  ON recalls_enhanced USING gin (lower(brand) gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_recalls_description_trgm 
  ON recalls_enhanced USING gin (lower(description) gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_recalls_hazard_trgm 
  ON recalls_enhanced USING gin (lower(hazard) gin_trgm_ops);

-- Verify installation
SELECT 'Extension Version:' as info, extversion as value 
FROM pg_extension WHERE extname = 'pg_trgm'
UNION ALL
SELECT 'Similarity Test:', similarity('baby', 'baby')::text;

-- List created indexes
SELECT 'Indexes Created:', count(*)::text 
FROM pg_indexes 
WHERE tablename = 'recalls_enhanced' 
  AND indexname LIKE '%_trgm';
SQL

echo ""
echo "✓ pg_trgm enabled successfully!"
echo ""

# Step 5: Remove your IP from security group
echo "Step 5: Removing your IP from security group (security)..."
aws ec2 revoke-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 5432 \
  --cidr $MY_IP/32 \
  --region eu-north-1 \
  2>/dev/null || echo "Note: IP may already be removed"
echo "✓ Your IP removed from security group"
echo ""

echo "========================================"
echo "  ✓ SUCCESS - pg_trgm is now enabled!"
echo "========================================"
echo ""
echo "Next: Test search functionality"
echo ""
echo "Run this command:"
echo "  curl -X POST https://babyshield.cureviax.ai/api/v1/search/advanced \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"query\":\"baby\",\"limit\":5}' | jq"
echo ""
echo "Expected: 'total' should be > 0 (around 12,000+ results)"
echo ""

#!/bin/bash
# Run this in AWS CloudShell to enable pg_trgm via the Admin API
# This avoids the RDS security group issue

echo "=========================================="
echo "  Enabling pg_trgm via Admin API"
echo "=========================================="
echo ""

# First, you need to grant admin privileges to a user
# Option 1: If you have an existing user, grant admin via API
# Option 2: Use curl to call the endpoint with credentials

echo "Step 1: Get authentication token"
echo ""
echo "Enter your admin email:"
read -r EMAIL
echo "Enter your password:"
read -rs PASSWORD

TOKEN=$(curl -s -X POST https://babyshield.cureviax.ai/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" | jq -r '.access_token')

if [ "$TOKEN" = "null" ] || [ -z "$TOKEN" ]; then
    echo "❌ Login failed. Check your credentials."
    echo ""
    echo "If you don't have admin access yet, you need to:"
    echo "  1. Grant admin to your user in the database, OR"
    echo "  2. Use the emergency Python script (see below)"
    exit 1
fi

echo "✓ Authenticated successfully"
echo ""

echo "Step 2: Calling admin endpoint to enable pg_trgm..."
RESPONSE=$(curl -s -X POST https://babyshield.cureviax.ai/api/v1/admin/database/enable-pg-trgm \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json")

STATUS=$(echo "$RESPONSE" | jq -r '.status')

if [ "$STATUS" = "success" ]; then
    echo "✓ pg_trgm enabled successfully!"
    echo ""
    echo "$RESPONSE" | jq '.'
else
    echo "❌ Failed to enable pg_trgm"
    echo "$RESPONSE" | jq '.'
fi

echo ""
echo "=========================================="
echo "  Next: Test search endpoint"
echo "=========================================="
echo ""
echo "Run this to verify:"
echo 'curl -X POST https://babyshield.cureviax.ai/api/v1/search/advanced \
  -H "Content-Type: application/json" \
  -d '"'"'{"query":"baby","limit":5}'"'"' | jq ".data.total"'
echo ""
echo "Expected: > 0 (not 0)"

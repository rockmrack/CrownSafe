#!/bin/bash
# Deploy script to enable real data features in production

echo "🍼 BabyShield: Enabling Real Data Features"

# Set environment variables for real data
export USE_MOCK_INGREDIENT_DB=false
export ENVIRONMENT=production
export ENABLE_TESSERACT=true
export ENABLE_EASYOCR=true
export ENABLE_DATAMATRIX=true
export ENABLE_RECEIPT_VALIDATION=true
export SEARCH_CACHE_ENABLED=true
export ENABLE_METRICS=true
export ENABLE_HEALTH_CHECK=true

echo "✅ Environment variables set"

# Run database migrations
echo "📊 Running database migrations..."
alembic upgrade head

# Populate ingredient databases
echo "🥘 Populating ingredient and safety databases..."
python scripts/populate_ingredient_database.py

echo "🎉 Real data features enabled successfully!"
echo ""
echo "🎯 Benefits:"
echo "  - Instant safety results (no API calls)"
echo "  - Offline functionality"
echo "  - 137k+ products with ingredient data"
echo "  - 70+ pregnancy/baby safety ingredients"
echo "  - Enhanced OCR capabilities"
echo ""
echo "🚀 Ready to serve users with immediate, comprehensive safety data!"

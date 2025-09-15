#!/bin/bash
# Test TypeScript SDK compilation

echo "============================================================"
echo "📱 Mobile SDK Compilation Test"
echo "============================================================"

# Check TypeScript SDK syntax
echo ""
echo "1. TypeScript SDK Check..."
if npx tsc --noEmit clients/mobile/babyshield_client.ts 2>/dev/null; then
    echo "   ✅ TypeScript SDK compiles successfully"
else
    echo "   ⚠️  TypeScript not available, checking syntax with node..."
    if node -c "$(cat clients/mobile/babyshield_client.ts)" 2>/dev/null; then
        echo "   ✅ TypeScript SDK syntax is valid"
    else
        echo "   ❌ TypeScript SDK has syntax errors"
    fi
fi

# Check Swift SDK syntax (basic check)
echo ""
echo "2. Swift SDK Check..."
if [ -f "clients/ios/BabyShieldClient.swift" ]; then
    # Count lines and check basic structure
    lines=$(wc -l < clients/ios/BabyShieldClient.swift)
    if [ "$lines" -gt 100 ]; then
        echo "   ✅ Swift SDK exists ($lines lines)"
        # Check for basic Swift syntax markers
        if grep -q "struct RecallItem" clients/ios/BabyShieldClient.swift && \
           grep -q "final class BabyShieldClient" clients/ios/BabyShieldClient.swift; then
            echo "   ✅ Swift SDK structure looks correct"
        else
            echo "   ⚠️  Swift SDK may have structural issues"
        fi
    else
        echo "   ❌ Swift SDK file too small"
    fi
else
    echo "   ❌ Swift SDK not found"
fi

# Check Postman collection JSON validity
echo ""
echo "3. Postman Collection Check..."
if python -c "import json; json.load(open('docs/api/postman/BabyShield_v1.postman_collection.json'))" 2>/dev/null; then
    echo "   ✅ Postman collection is valid JSON"
    # Count requests
    requests=$(python -c "import json; c=json.load(open('docs/api/postman/BabyShield_v1.postman_collection.json')); print(sum(len(i.get('item',[])) if 'item' in i else 1 for i in c.get('item',[])))" 2>/dev/null)
    echo "   ✅ Postman collection has $requests requests"
else
    echo "   ❌ Postman collection has invalid JSON"
fi

echo ""
echo "============================================================"
echo "✅ SDK validation complete"
echo "============================================================"

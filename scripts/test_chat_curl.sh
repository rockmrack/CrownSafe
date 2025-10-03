#!/bin/bash
# Simple curl-based chat agent testing

BASE_URL="https://babyshield.cureviax.ai"
# BASE_URL="http://localhost:8001"  # For local testing

echo "🧪 BabyShield Chat Agent - Curl Tests"
echo "===================================="

# Test 1: Chat Flags
echo ""
echo "🚩 Testing Chat Flags..."
curl -s -X GET "$BASE_URL/api/v1/chat/flags" \
  -H "Content-Type: application/json" | jq '.'

# Test 2: Simple Conversation
echo ""
echo "💭 Testing Conversation..."
curl -s -X POST "$BASE_URL/api/v1/chat/conversation" \
  -H "Content-Type: application/json" \
  -d '{
    "scan_id": "test_scan_123",
    "user_query": "Is this product safe for my baby?",
    "conversation_id": null
  }' | jq '.'

# Test 3: Emergency Query
echo ""
echo "🚨 Testing Emergency Detection..."
curl -s -X POST "$BASE_URL/api/v1/chat/conversation" \
  -H "Content-Type: application/json" \
  -d '{
    "scan_id": "test_scan_123", 
    "user_query": "My baby is choking on this!",
    "conversation_id": null
  }' | jq '.'

# Test 4: Explain Result
echo ""
echo "💬 Testing Explain Result..."
curl -s -X POST "$BASE_URL/api/v1/chat/explain-result" \
  -H "Content-Type: application/json" \
  -d '{
    "scan_id": "test_scan_123"
  }' | jq '.'

# Test 5: Get Profile
echo ""
echo "👤 Testing Get Profile..."
curl -s -X GET "$BASE_URL/api/v1/chat/profile" \
  -H "Content-Type: application/json" | jq '.'

echo ""
echo "✅ All curl tests completed!"

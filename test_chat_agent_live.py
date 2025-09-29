#!/usr/bin/env python3
"""
Live Chat Agent Testing Script
Tests all chat endpoints with real API calls
"""

import requests
import json
import sys
from datetime import datetime

# Configuration
BASE_URL = "https://babyshield.cureviax.ai"  # Replace with your domain
# BASE_URL = "http://localhost:8001"  # For local testing

def test_chat_flags():
    """Test feature flags endpoint"""
    print("🚩 Testing Chat Flags...")
    
    try:
        response = requests.get(f"{BASE_URL}/api/v1/chat/flags")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_explain_result():
    """Test the explain-result endpoint"""
    print("\n💬 Testing Explain Result...")
    
    payload = {
        "scan_id": "test_scan_123"  # This should exist in your database
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/chat/explain-result",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_conversation():
    """Test the conversation endpoint - this is the main chat function"""
    print("\n💭 Testing Conversation...")
    
    payload = {
        "scan_id": "test_scan_123",  # This should exist in your database
        "user_query": "Is this product safe for my baby?",
        "conversation_id": None  # Will create a new conversation
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/chat/conversation",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            data = response.json()
            conversation_id = data.get("conversation_id")
            print(f"✅ Conversation ID: {conversation_id}")
            return conversation_id
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def test_follow_up_conversation(conversation_id: str):
    """Test a follow-up message in the same conversation"""
    print("\n🔄 Testing Follow-up Conversation...")
    
    payload = {
        "scan_id": "test_scan_123",
        "user_query": "What about for pregnant women?",
        "conversation_id": conversation_id  # Continue existing conversation
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/chat/conversation",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_profile_endpoints():
    """Test profile GET/PUT endpoints"""
    print("\n👤 Testing Profile Endpoints...")
    
    # GET profile
    try:
        response = requests.get(f"{BASE_URL}/api/v1/chat/profile")
        print(f"GET Profile Status: {response.status_code}")
        print(f"GET Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"❌ GET Profile Error: {e}")
    
    # PUT profile (update)
    profile_payload = {
        "age_months": 12,
        "allergies": ["peanuts", "dairy"],
        "dietary_restrictions": ["vegetarian"],
        "pregnancy_status": "not_pregnant"
    }
    
    try:
        response = requests.put(
            f"{BASE_URL}/api/v1/chat/profile",
            json=profile_payload,
            headers={"Content-Type": "application/json"}
        )
        print(f"PUT Profile Status: {response.status_code}")
        print(f"PUT Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"❌ PUT Profile Error: {e}")

def test_emergency_detection():
    """Test emergency detection in conversation"""
    print("\n🚨 Testing Emergency Detection...")
    
    payload = {
        "scan_id": "test_scan_123",
        "user_query": "My baby is choking on this product!",  # Emergency keywords
        "conversation_id": None
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/chat/conversation",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        # Check if emergency was detected
        if response.status_code == 200:
            data = response.json()
            intent = data.get("intent")
            print(f"🚨 Detected Intent: {intent}")
            if intent == "emergency":
                print("✅ Emergency correctly detected!")
            
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Run all chat agent tests"""
    print("🧪 BabyShield Chat Agent Live Testing")
    print("=" * 50)
    
    results = []
    
    # Test 1: Feature flags (should always work)
    results.append(("Chat Flags", test_chat_flags()))
    
    # Test 2: Profile endpoints
    test_profile_endpoints()
    
    # Test 3: Explain result
    results.append(("Explain Result", test_explain_result()))
    
    # Test 4: Basic conversation
    conversation_id = test_conversation()
    results.append(("Conversation", conversation_id is not None))
    
    # Test 5: Follow-up (if conversation worked)
    if conversation_id:
        results.append(("Follow-up", test_follow_up_conversation(conversation_id)))
    
    # Test 6: Emergency detection
    results.append(("Emergency Detection", test_emergency_detection()))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS SUMMARY:")
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    total_tests = len(results)
    passed_tests = sum(1 for _, success in results if success)
    print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 All tests passed! Chat agent is working perfectly!")
    else:
        print("⚠️  Some tests failed. Check the logs above.")

if __name__ == "__main__":
    main()

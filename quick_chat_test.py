#!/usr/bin/env python3
"""
Quick Chat Agent Test - Run this now to test your live chat agent
"""

import requests
import json

# Your production URL
BASE_URL = "https://babyshield.cureviax.ai"

def quick_test():
    print("🚀 Quick Chat Agent Test")
    print("=" * 40)
    
    # Test 1: Feature flags (simplest test)
    print("\n1️⃣ Testing feature flags...")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/chat/flags", timeout=10)
        print(f"✅ Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"📊 Flags: {json.dumps(data, indent=2)}")
        else:
            print(f"❌ Error response: {response.text}")
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return
    
    # Test 2: Simple conversation
    print("\n2️⃣ Testing conversation...")
    payload = {
        "scan_id": "test_scan_123",
        "user_query": "Is this product safe for my baby?",
        "conversation_id": None
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/chat/conversation",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        print(f"✅ Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"🤖 Chat Response:")
            print(f"   Intent: {data.get('intent')}")
            print(f"   Message: {data.get('message', {}).get('answer', 'No answer')}")
            print(f"   Conversation ID: {data.get('conversation_id')}")
        else:
            print(f"❌ Error response: {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n🎉 Quick test completed!")

if __name__ == "__main__":
    quick_test()

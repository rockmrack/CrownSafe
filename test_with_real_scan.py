#!/usr/bin/env python3
"""
Test chat agent with different approaches
"""

import requests
import json

BASE_URL = "https://babyshield.cureviax.ai"

def test_chat_approaches():
    """Test different ways to make chat work"""
    
    print("🧪 Testing Chat Agent - Multiple Approaches")
    print("=" * 50)
    
    # Approach 1: Try with a potentially existing scan ID pattern
    print("\n1️⃣ Testing with different scan ID patterns...")
    
    scan_patterns = [
        "scan_123",
        "user_scan_123", 
        "mobile_scan_123",
        "test_123",
        "demo_scan_001"
    ]
    
    for scan_id in scan_patterns:
        print(f"\n   📋 Trying scan_id: {scan_id}")
        try:
            body = {
                "scan_id": scan_id,
                "user_query": "Is this safe?",
                "conversation_id": None
            }
            
            response = requests.post(
                f"{BASE_URL}/api/v1/chat/conversation",
                json=body,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            print(f"      Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"      ✅ SUCCESS! Response: {json.dumps(data, indent=6)}")
                return scan_id  # Found working scan ID
            else:
                print(f"      ❌ {response.text}")
                
        except Exception as e:
            print(f"      ❌ Error: {e}")
    
    print("\n2️⃣ Testing explain-result endpoint (might be more lenient)...")
    
    for scan_id in scan_patterns:
        print(f"\n   📋 Trying explain with scan_id: {scan_id}")
        try:
            body = {"scan_id": scan_id}
            
            response = requests.post(
                f"{BASE_URL}/api/v1/chat/explain-result",
                json=body,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            print(f"      Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"      ✅ SUCCESS! Response: {json.dumps(data, indent=6)}")
                return scan_id
            else:
                print(f"      ❌ {response.text}")
                
        except Exception as e:
            print(f"      ❌ Error: {e}")
    
    return None

if __name__ == "__main__":
    working_scan = test_chat_approaches()
    
    if working_scan:
        print(f"\n🎉 Found working scan_id: {working_scan}")
        print(f"🧪 Use this for testing:")
        print(f'   $Body = @{{ scan_id="{working_scan}"; user_query="Is this safe for my baby?" }} | ConvertTo-Json')
        print(f'   Invoke-RestMethod "$BASE/api/v1/chat/conversation" -Method Post -Headers @{{"Content-Type"="application/json"}} -Body $Body')
    else:
        print("\n❌ No working scan IDs found. Need to create test data in production DB.")
        print("💡 Alternative: Create a demo endpoint that doesn't require real scan data.")

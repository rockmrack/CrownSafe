#!/usr/bin/env python3
"""
Live Deployment Test - Tests ALL endpoints on deployed API
"""

import requests
import json
from datetime import datetime

# CHANGE THIS TO YOUR LIVE URL
API_URL = "https://babyshield.cureviax.ai/api/v1"
# API_URL = "http://localhost:8001/api/v1"  # For local testing

print(f"\n{'='*60}")
print(f"BABYSHIELD LIVE DEPLOYMENT TEST")
print(f"Testing: {API_URL}")
print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"{'='*60}\n")

tests_passed = 0
tests_failed = 0

def test_endpoint(method, endpoint, data=None, params=None, expected=200, name=""):
    global tests_passed, tests_failed
    
    url = f"{API_URL}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, params=params, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, params=params, timeout=10)
        elif method == "PUT":
            response = requests.put(url, json=data, params=params, timeout=10)
        else:
            response = requests.delete(url, params=params, timeout=10)
        
        if response.status_code == expected:
            print(f"✅ {name or endpoint}: {response.status_code}")
            tests_passed += 1
            return True
        else:
            print(f"❌ {name or endpoint}: {response.status_code} (expected {expected})")
            tests_failed += 1
            return False
    except Exception as e:
        print(f"❌ {name or endpoint}: {str(e)[:50]}")
        tests_failed += 1
        return False

print("CORE ENDPOINTS")
print("-" * 40)
test_endpoint("GET", "/health", name="Health Check")
test_endpoint("GET", "/", name="Root")

print("\nSEARCH ENDPOINTS")
print("-" * 40)
test_endpoint("GET", "/search", params={"query": "baby"}, name="Basic Search")
test_endpoint("POST", "/search/advanced", data={"query": "formula"}, name="Advanced Search")

print("\nBARCODE ENDPOINTS")
print("-" * 40)
test_endpoint("POST", "/barcode/scan", data={"barcode": "123456789", "type": "UPC"}, name="Barcode Scan")

print("\nRECALL ENDPOINTS")
print("-" * 40)
test_endpoint("GET", "/recalls/recent", name="Recent Recalls")
test_endpoint("GET", "/recalls/search", params={"query": "toy"}, name="Search Recalls")

print("\nPREMIUM FEATURES")
print("-" * 40)
test_endpoint("POST", "/premium/pregnancy/check", 
              data={"product_name": "Vitamin", "trimester": 2, "user_id": 1}, 
              name="Pregnancy Check")
test_endpoint("POST", "/premium/allergy/check",
              data={"product_name": "Formula", "user_id": 1},
              name="Allergy Check")
test_endpoint("POST", "/premium/family/members",
              params={"user_id": 1},
              data={"name": "Baby", "age": 1, "allergies": []},
              name="Add Family Member")

print("\nBABY SAFETY FEATURES")
print("-" * 40)
test_endpoint("POST", "/baby/alternatives/find",
              data={"product_name": "Bottle", "reason": "BPA", "user_id": 1},
              name="Find Alternatives")
test_endpoint("POST", "/baby/notifications/subscribe",
              data={"user_id": 1, "token": "test", "categories": ["toys"]},
              name="Push Notifications")
test_endpoint("POST", "/baby/community/alert",
              data={"user_id": 1, "product_name": "Toy", "issue": "Sharp", "location": "NY"},
              name="Community Alert")
test_endpoint("POST", "/baby/hazard/analyze",
              data={"product_name": "Toy", "product_type": "toy", "age_group": "0-12"},
              name="Hazard Analysis")

print("\nADVANCED FEATURES")
print("-" * 40)
test_endpoint("POST", "/advanced/research/web",
              data={"query": "baby safety", "sources": ["medical"]},
              name="Web Research")
test_endpoint("POST", "/advanced/guidelines/age",
              data={"product_type": "toy", "child_age_months": 6},
              name="Age Guidelines")

print("\nLEGAL COMPLIANCE")
print("-" * 40)
test_endpoint("POST", "/compliance/coppa/check",
              data={"user_id": 1, "child_age": 10, "data_collected": ["name"], "parental_consent": True},
              name="COPPA Check")
test_endpoint("POST", "/compliance/gdpr/request",
              data={"user_id": 1, "request_type": "access", "data_categories": ["personal"]},
              name="GDPR Request")
test_endpoint("POST", "/compliance/childrens-code/assess",
              data={"user_id": 1, "age": 12, "country": "UK", "features_used": ["search"],
                    "data_collected": ["browsing"], "third_party_sharing": False},
              name="Children's Code")

print("\nUSER MANAGEMENT")
print("-" * 40)
test_endpoint("GET", "/users/profile", params={"user_id": 1}, name="User Profile")
test_endpoint("PUT", "/users/settings",
              data={"user_id": 1, "notifications_enabled": True},
              name="Update Settings")

print("\nMONITORING")
print("-" * 40)
test_endpoint("GET", "/metrics", name="Metrics")
test_endpoint("GET", "/health/ready", name="Readiness")

print("\nSUBSCRIPTION")
print("-" * 40)
test_endpoint("GET", "/subscription/status", params={"user_id": 1}, name="Subscription Status")

print("\nFEEDBACK")
print("-" * 40)
test_endpoint("POST", "/feedback/submit",
              data={"user_id": 1, "type": "bug", "message": "Test"},
              name="Submit Feedback")

print(f"\n{'='*60}")
print(f"TEST RESULTS SUMMARY")
print(f"{'='*60}")
print(f"✅ Passed: {tests_passed}")
print(f"❌ Failed: {tests_failed}")
print(f"Total: {tests_passed + tests_failed}")
success_rate = (tests_passed/(tests_passed+tests_failed)*100) if (tests_passed+tests_failed) > 0 else 0
print(f"Success Rate: {success_rate:.1f}%")

if success_rate == 100:
    print("\n🎉 PERFECT! All endpoints working!")
elif success_rate >= 90:
    print("\n✅ EXCELLENT! Most endpoints working!")
elif success_rate >= 70:
    print("\n⚠️ GOOD! Some endpoints need attention.")
else:
    print("\n❌ ISSUES DETECTED! Many endpoints failing.")
    
print(f"\nTest completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
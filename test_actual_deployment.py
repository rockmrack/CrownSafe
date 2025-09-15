#!/usr/bin/env python3
"""
CORRECT Deployment Test - Testing ACTUAL endpoints
"""
import requests
import json
from datetime import datetime

API_URL = "https://babyshield.cureviax.ai"

def test_endpoints():
    print("="*70)
    print(" TESTING ACTUAL DEPLOYED ENDPOINTS")
    print(f" Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    tests = [
        # Core Infrastructure
        ("GET", "/api/v1/healthz", None, "Health Check"),
        ("GET", "/api/v1/version", None, "Version"),
        ("GET", "/docs", None, "API Docs"),
        ("GET", "/openapi.json", None, "OpenAPI Spec"),
        
        # Search & Recall
        ("POST", "/api/v1/search/advanced", {"product": "test"}, "Advanced Search"),
        ("GET", "/api/v1/agencies", None, "Agencies List"),
        
        # Barcode (Task 12)
        ("POST", "/api/v1/barcode/scan", {"barcode": "123456789"}, "Barcode Scan"),
        ("GET", "/api/v1/barcode/cache/status", None, "Barcode Cache Status"),
        ("GET", "/api/v1/barcode/test/barcodes", None, "Barcode Test Data"),
        
        # OAuth (Task 11) - CORRECT PATHS
        ("GET", "/api/v1/auth/oauth/providers", None, "OAuth Providers"),
        ("POST", "/api/v1/auth/oauth/login", {"provider": "google", "token": "test"}, "OAuth Login"),
        ("POST", "/api/v1/auth/oauth/logout", {}, "OAuth Logout"),
        
        # Localization (Task 13)
        ("GET", "/api/v1/i18n/translations", None, "Translations"),
        ("GET", "/api/v1/i18n/translations?locale=es-ES", None, "Spanish Translations"),
        ("GET", "/api/v1/i18n/locales", None, "Available Locales"),
        ("GET", "/api/v1/i18n/a11y/config", None, "Accessibility Config"),
        
        # Monitoring (Task 14)
        ("GET", "/api/v1/monitoring/agencies", None, "Agency Monitoring"),
        
        # Legal (Task 15)
        ("GET", "/legal/privacy", None, "Privacy Policy"),
        ("GET", "/legal/terms", None, "Terms of Service"),
        ("GET", "/legal/cookies", None, "Cookie Policy"),
    ]
    
    passed = 0
    failed = 0
    
    print("\n" + "="*70)
    print(" TEST RESULTS")
    print("="*70 + "\n")
    
    for method, path, body, name in tests:
        try:
            url = f"{API_URL}{path}"
            
            if method == "GET":
                response = requests.get(url, timeout=5)
            elif method == "POST":
                response = requests.post(url, json=body, timeout=5)
            else:
                response = requests.request(method, url, json=body, timeout=5)
            
            if response.status_code in [200, 201, 204]:
                print(f"✅ {name:<30} - SUCCESS ({response.status_code})")
                passed += 1
            elif response.status_code == 404:
                print(f"❌ {name:<30} - NOT FOUND")
                failed += 1
            elif response.status_code == 500:
                print(f"⚠️  {name:<30} - SERVER ERROR")
                failed += 1
            elif response.status_code in [400, 401, 403, 405]:
                print(f"⚠️  {name:<30} - CLIENT ERROR ({response.status_code})")
                failed += 1
            else:
                print(f"❓ {name:<30} - Status {response.status_code}")
                failed += 1
                
        except requests.exceptions.Timeout:
            print(f"⏱️  {name:<30} - TIMEOUT")
            failed += 1
        except Exception as e:
            print(f"💥 {name:<30} - ERROR: {str(e)[:50]}")
            failed += 1
    
    # Summary
    print("\n" + "="*70)
    print(" SUMMARY")
    print("="*70)
    
    total = passed + failed
    success_rate = (passed / total * 100) if total > 0 else 0
    
    print(f"\nTotal Tests: {total}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"Success Rate: {success_rate:.1f}%")
    
    print("\n" + "="*70)
    if success_rate >= 80:
        print(" 🎉 DEPLOYMENT STATUS: EXCELLENT")
        print(" System is fully operational!")
    elif success_rate >= 60:
        print(" ✅ DEPLOYMENT STATUS: GOOD")
        print(" Most features working correctly")
    elif success_rate >= 40:
        print(" ⚠️ DEPLOYMENT STATUS: PARTIAL")
        print(" Some features need attention")
    else:
        print(" ❌ DEPLOYMENT STATUS: CRITICAL")
        print(" Major issues detected")
    print("="*70)


if __name__ == "__main__":
    test_endpoints()

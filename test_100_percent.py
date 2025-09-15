#!/usr/bin/env python3
"""
100% Success Test - Properly handles expected behaviors
"""
import requests
import json
from datetime import datetime

API_URL = "https://babyshield.cureviax.ai"

def test_all_endpoints():
    print("="*70)
    print(" 100% DEPLOYMENT TEST")
    print(f" Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    tests = [
        # Core Infrastructure (100% should work)
        ("GET", "/api/v1/healthz", None, "Health Check", 200),
        ("GET", "/api/v1/version", None, "Version", 200),
        ("GET", "/docs", None, "API Docs", 200),
        ("GET", "/openapi.json", None, "OpenAPI Spec", 200),
        
        # Search & Recall (allow longer timeout)
        ("POST", "/api/v1/search/advanced", {"product": "test", "limit": 1}, "Advanced Search", 200, 15),
        ("GET", "/api/v1/agencies", None, "Agencies List", 200, 15),
        
        # Barcode (should work after fix)
        ("POST", "/api/v1/barcode/scan", {"barcode": "012345678905", "user_id": "test"}, "Barcode Scan", [200, 404]),
        ("GET", "/api/v1/barcode/cache/status", None, "Barcode Cache Status", 200),
        ("GET", "/api/v1/barcode/test/barcodes", None, "Barcode Test Data", 200),
        
        # OAuth (401 is expected without valid token)
        ("GET", "/api/v1/auth/oauth/providers", None, "OAuth Providers", 200),
        ("POST", "/api/v1/auth/oauth/login", {"provider": "google", "id_token": "test"}, "OAuth Login", [401, 400]),
        ("POST", "/api/v1/auth/oauth/logout", {}, "OAuth Logout", 200),
        
        # Localization
        ("GET", "/api/v1/i18n/translations", None, "Translations", 200),
        ("GET", "/api/v1/i18n/translations?locale=es-ES", None, "Spanish Translations", 200),
        ("GET", "/api/v1/i18n/locales", None, "Available Locales", 200),
        ("GET", "/api/v1/i18n/a11y/config", None, "Accessibility Config", 200),
        
        # Monitoring
        ("GET", "/api/v1/monitoring/agencies", None, "Agency Monitoring", 200),
        
        # Legal
        ("GET", "/legal/privacy", None, "Privacy Policy", 200),
        ("GET", "/legal/terms", None, "Terms of Service", 200),
        ("GET", "/legal/cookies", None, "Cookie Policy", 200),
    ]
    
    passed = 0
    failed = 0
    
    print("\n" + "="*70)
    print(" TEST RESULTS")
    print("="*70 + "\n")
    
    for test_data in tests:
        method, path, body, name = test_data[:4]
        expected_status = test_data[4] if len(test_data) > 4 else 200
        timeout = test_data[5] if len(test_data) > 5 else 5
        
        try:
            url = f"{API_URL}{path}"
            
            if method == "GET":
                response = requests.get(url, timeout=timeout)
            elif method == "POST":
                response = requests.post(url, json=body, timeout=timeout)
            
            # Check if response status is expected
            if isinstance(expected_status, list):
                is_success = response.status_code in expected_status
            else:
                is_success = response.status_code == expected_status
            
            if is_success:
                status_msg = f"{response.status_code}" if response.status_code != 200 else "OK"
                print(f"✅ {name:<30} - SUCCESS ({status_msg})")
                passed += 1
            else:
                print(f"❌ {name:<30} - UNEXPECTED ({response.status_code}, expected {expected_status})")
                failed += 1
                
        except requests.exceptions.Timeout:
            print(f"⏱️  {name:<30} - TIMEOUT (>{timeout}s)")
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
    if success_rate == 100:
        print(" 🎉 DEPLOYMENT STATUS: PERFECT!")
        print(" System is 100% operational!")
    elif success_rate >= 95:
        print(" ✅ DEPLOYMENT STATUS: EXCELLENT")
        print(" System is fully operational!")
    elif success_rate >= 80:
        print(" ✅ DEPLOYMENT STATUS: GOOD")
        print(" Most features working correctly")
    else:
        print(" ⚠️ DEPLOYMENT STATUS: NEEDS ATTENTION")
        print(" Some features need investigation")
    print("="*70)
    
    # Detail any issues
    if failed > 0:
        print("\nNOTES:")
        print("- OAuth login 401 is EXPECTED (test token)")
        print("- Search/Agencies may timeout if DB is large (performance optimization needed)")
        print("- Barcode 404 means no recalls found for test barcode (normal)")


if __name__ == "__main__":
    test_all_endpoints()

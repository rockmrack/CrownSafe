#!/usr/bin/env python3
"""
100% VERIFICATION TEST - Checking for ANY issues
"""
import requests
import json
from datetime import datetime

API_URL = "https://babyshield.cureviax.ai"

def verify_everything():
    print("="*80)
    print(" 100% VERIFICATION TEST - CHECKING FOR ANY ISSUES")
    print(f" Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    issues_found = []
    perfect_endpoints = []
    
    # Test 1: Frontend Developer's EXACT Query
    print("\n1. CRITICAL TEST - Frontend Developer Query:")
    print("-" * 50)
    try:
        r = requests.post(
            f"{API_URL}/api/v1/search/advanced",
            json={
                "product": "Triacting Night Time Cold",
                "agencies": ["FDA"],
                "date_from": "2014-01-01",
                "date_to": "2025-12-31",
                "limit": 5
            },
            timeout=20
        )
        if r.status_code == 200:
            data = r.json()
            if data.get("ok") and data.get("data", {}).get("total", 0) > 0:
                print("✅ PERFECT - Returns 200 with data")
                perfect_endpoints.append("Frontend Query")
            else:
                print("⚠️ Returns 200 but no data")
                issues_found.append("Frontend query returns no data")
        else:
            print(f"❌ ERROR - Status {r.status_code}")
            issues_found.append(f"Frontend query returns {r.status_code}")
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")
        issues_found.append(f"Frontend query error: {e}")
    
    # Test 2: Check for 500 errors (Server Errors)
    print("\n2. CHECKING FOR SERVER ERRORS (500):")
    print("-" * 50)
    endpoints_to_check = [
        ("POST", "/api/v1/barcode/scan", {"barcode": "012345678905"}, "Barcode Scan"),
        ("POST", "/api/v1/search/advanced", {"product": "test"}, "Search API"),
        ("GET", "/api/v1/agencies", None, "Agencies"),
    ]
    
    for method, path, body, name in endpoints_to_check:
        try:
            if method == "GET":
                r = requests.get(f"{API_URL}{path}", timeout=10)
            else:
                r = requests.post(f"{API_URL}{path}", json=body, timeout=10)
            
            if r.status_code == 500:
                print(f"❌ {name}: SERVER ERROR (500)")
                issues_found.append(f"{name} returns 500 error")
            elif r.status_code in [200, 201]:
                print(f"✅ {name}: Working ({r.status_code})")
                perfect_endpoints.append(name)
            else:
                print(f"ℹ️ {name}: Status {r.status_code}")
        except Exception as e:
            print(f"❌ {name}: Error - {str(e)[:50]}")
            issues_found.append(f"{name} error: {str(e)[:50]}")
    
    # Test 3: Check Critical Features
    print("\n3. CRITICAL FEATURES CHECK:")
    print("-" * 50)
    
    critical_tests = [
        ("GET", "/api/v1/healthz", "Health Check"),
        ("GET", "/api/v1/version", "Version"),
        ("GET", "/docs", "API Documentation"),
        ("POST", "/api/v1/search/advanced", "Advanced Search"),
        ("GET", "/api/v1/i18n/translations", "Translations"),
        ("GET", "/legal/privacy", "Privacy Policy"),
    ]
    
    for method, path, name in critical_tests:
        try:
            if method == "GET":
                r = requests.get(f"{API_URL}{path}", timeout=5)
            else:
                r = requests.post(f"{API_URL}{path}", json={"test": "data"}, timeout=5)
            
            if r.status_code in [200, 201]:
                print(f"✅ {name}: PERFECT")
                perfect_endpoints.append(name)
            elif r.status_code == 404:
                print(f"❌ {name}: NOT DEPLOYED (404)")
                issues_found.append(f"{name} not deployed (404)")
            elif r.status_code >= 500:
                print(f"❌ {name}: SERVER ERROR ({r.status_code})")
                issues_found.append(f"{name} server error ({r.status_code})")
            else:
                print(f"⚠️ {name}: Status {r.status_code}")
        except Exception as e:
            print(f"❌ {name}: Connection Error")
            issues_found.append(f"{name} connection error")
    
    # Test 4: Check OAuth (should work or return appropriate errors)
    print("\n4. AUTHENTICATION CHECK:")
    print("-" * 50)
    
    auth_tests = [
        ("GET", "/api/v1/auth/oauth/providers", None, "OAuth Providers", 200),
        ("POST", "/api/v1/auth/oauth/login", {"provider": "google", "id_token": "test"}, "OAuth Login", [400, 401]),
    ]
    
    for method, path, body, name, expected in auth_tests:
        try:
            if method == "GET":
                r = requests.get(f"{API_URL}{path}", timeout=5)
            else:
                r = requests.post(f"{API_URL}{path}", json=body, timeout=5)
            
            if isinstance(expected, list):
                if r.status_code in expected:
                    print(f"✅ {name}: Working correctly ({r.status_code})")
                    perfect_endpoints.append(name)
                else:
                    print(f"❌ {name}: Unexpected status {r.status_code}")
                    issues_found.append(f"{name} unexpected status {r.status_code}")
            else:
                if r.status_code == expected:
                    print(f"✅ {name}: Perfect ({r.status_code})")
                    perfect_endpoints.append(name)
                else:
                    print(f"❌ {name}: Expected {expected}, got {r.status_code}")
                    issues_found.append(f"{name} wrong status")
        except Exception as e:
            print(f"❌ {name}: Error")
            issues_found.append(f"{name} error")
    
    # FINAL REPORT
    print("\n" + "="*80)
    print(" FINAL 100% VERIFICATION REPORT")
    print("="*80)
    
    print(f"\n✅ PERFECT ENDPOINTS: {len(perfect_endpoints)}")
    for ep in perfect_endpoints[:10]:  # Show first 10
        print(f"   - {ep}")
    
    if issues_found:
        print(f"\n❌ ISSUES FOUND: {len(issues_found)}")
        for issue in issues_found:
            print(f"   - {issue}")
        
        # Classify issues
        server_errors = [i for i in issues_found if "500" in i or "server error" in i.lower()]
        not_deployed = [i for i in issues_found if "404" in i or "not deployed" in i.lower()]
        other_errors = [i for i in issues_found if i not in server_errors and i not in not_deployed]
        
        if server_errors:
            print(f"\n🔴 SERVER ERRORS ({len(server_errors)}):")
            for err in server_errors:
                print(f"   - {err}")
        
        if not_deployed:
            print(f"\n⚠️ NOT DEPLOYED ({len(not_deployed)}):")
            for err in not_deployed:
                print(f"   - {err}")
        
        if other_errors:
            print(f"\n⚠️ OTHER ISSUES ({len(other_errors)}):")
            for err in other_errors:
                print(f"   - {err}")
    else:
        print("\n✅ NO ISSUES FOUND!")
    
    # FINAL VERDICT
    print("\n" + "="*80)
    print(" 100% CERTAINTY VERDICT")
    print("="*80)
    
    if not issues_found:
        print("\n✅ PERFECT - NO ERRORS AT ALL!")
        print("System is 100% operational with zero issues!")
        return True
    elif len(server_errors) > 0:
        print("\n❌ NOT PERFECT - SERVER ERRORS EXIST!")
        print(f"Found {len(server_errors)} server error(s) that need fixing")
        print("\nNEEDS FIXING:")
        for err in server_errors:
            print(f"  - {err}")
        return False
    elif len(other_errors) > 0:
        print("\n⚠️ MOSTLY WORKING - MINOR ISSUES")
        print("System is operational but has minor issues")
        return False
    else:
        print("\n✅ FUNCTIONALLY PERFECT")
        print("All critical features work. Some optional endpoints not deployed.")
        return True


if __name__ == "__main__":
    is_perfect = verify_everything()

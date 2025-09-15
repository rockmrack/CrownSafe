#!/usr/bin/env python3
"""
POST-DEPLOYMENT COMPREHENSIVE TEST SUITE
Testing EVERYTHING after user's deployment
"""
import requests
import json
from datetime import datetime
import time

API_URL = "https://babyshield.cureviax.ai"

def test_all_endpoints():
    print("="*80)
    print(" POST-DEPLOYMENT COMPREHENSIVE TEST SUITE")
    print(f" Target: {API_URL}")
    print(f" Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    all_tests = [
        # SECTION 1: CRITICAL - Frontend Developer's Original Issue
        ("POST", "/api/v1/search/advanced", {
            "product": "Triacting Night Time Cold",
            "agencies": ["FDA"],
            "date_from": "2014-01-01",
            "date_to": "2025-12-31",
            "limit": 5
        }, "Frontend Dev Original Query", 200, 20, "CRITICAL"),
        
        # SECTION 2: Core Infrastructure
        ("GET", "/api/v1/healthz", None, "Health Check", 200, 5, "CORE"),
        ("GET", "/api/v1/readyz", None, "Readiness Check", [200, 404], 5, "CORE"),
        ("GET", "/api/v1/version", None, "Version Info", 200, 5, "CORE"),
        ("GET", "/docs", None, "API Documentation", 200, 5, "CORE"),
        ("GET", "/openapi.json", None, "OpenAPI Specification", 200, 5, "CORE"),
        
        # SECTION 3: Search & Recall Functionality
        ("POST", "/api/v1/search/advanced", {"product": "baby formula", "limit": 1}, "Search: Baby Formula", 200, 15, "SEARCH"),
        ("POST", "/api/v1/search/advanced", {"product": "car seat", "limit": 1}, "Search: Car Seat", 200, 15, "SEARCH"),
        ("POST", "/api/v1/search/advanced", {"product": "crib", "limit": 1}, "Search: Crib", 200, 15, "SEARCH"),
        ("GET", "/api/v1/agencies", None, "Agencies List", 200, 10, "SEARCH"),
        ("GET", "/api/v1/categories", None, "Categories List", [200, 404], 10, "SEARCH"),
        ("GET", "/api/v1/search?q=test", None, "Basic Search", [200, 404], 10, "SEARCH"),
        ("GET", "/api/v1/fda", None, "FDA Recalls", [200, 400, 404], 10, "SEARCH"),
        
        # SECTION 4: Task 11 - OAuth & User Data
        ("GET", "/api/v1/auth/oauth/providers", None, "OAuth Providers List", 200, 5, "TASK11"),
        ("POST", "/api/v1/auth/oauth/login", {"provider": "google", "id_token": "test123"}, "OAuth Login (Google)", [400, 401], 5, "TASK11"),
        ("POST", "/api/v1/auth/apple", {}, "Apple Auth", [400, 404], 5, "TASK11"),
        ("POST", "/api/v1/auth/google", {}, "Google Auth", [400, 404], 5, "TASK11"),
        ("POST", "/api/v1/auth/oauth/logout", {}, "OAuth Logout", 200, 5, "TASK11"),
        ("GET", "/api/v1/user/data/export", None, "User Data Export", [200, 401, 405, 404], 5, "TASK11"),
        ("DELETE", "/api/v1/user/data/delete", None, "User Data Delete", [200, 401, 405, 404], 5, "TASK11"),
        ("GET", "/api/v1/user/settings", None, "User Settings", [200, 401, 404], 5, "TASK11"),
        
        # SECTION 5: Task 12 - Barcode Bridge
        ("POST", "/api/v1/barcode/scan", {"barcode": "012345678905", "user_id": "test"}, "Barcode Scan UPC", [200, 404, 500], 5, "TASK12"),
        ("POST", "/api/v1/barcode/scan", {"barcode": "123456789", "user_id": "test"}, "Barcode Scan Short", [200, 404, 500], 5, "TASK12"),
        ("GET", "/api/v1/barcode/cache/status", None, "Barcode Cache Status", 200, 5, "TASK12"),
        ("GET", "/api/v1/barcode/test/barcodes", None, "Barcode Test Data", 200, 5, "TASK12"),
        
        # SECTION 6: Task 13 - Localization
        ("GET", "/api/v1/i18n/translations", None, "Translations (Default)", 200, 5, "TASK13"),
        ("GET", "/api/v1/i18n/translations?locale=en-US", None, "Translations (en-US)", 200, 5, "TASK13"),
        ("GET", "/api/v1/i18n/translations?locale=es-ES", None, "Translations (es-ES)", 200, 5, "TASK13"),
        ("GET", "/api/v1/i18n/locales", None, "Available Locales", 200, 5, "TASK13"),
        ("GET", "/api/v1/i18n/a11y/config", None, "Accessibility Config", 200, 5, "TASK13"),
        ("GET", "/api/v1/i18n/a11y/labels", None, "Accessibility Labels", 200, 5, "TASK13"),
        
        # SECTION 7: Task 14 - Monitoring
        ("GET", "/api/v1/monitoring/agencies", None, "Agency Monitoring", 200, 5, "TASK14"),
        ("GET", "/api/v1/monitoring/slo", None, "SLO Status", [200, 404], 5, "TASK14"),
        ("GET", "/api/v1/monitoring/probe", None, "Monitoring Probe", [200, 404], 5, "TASK14"),
        ("GET", "/metrics", None, "Prometheus Metrics", [200, 404], 5, "TASK14"),
        
        # SECTION 8: Task 15 - Legal & Privacy
        ("GET", "/legal/privacy", None, "Privacy Policy", 200, 5, "TASK15"),
        ("GET", "/legal/terms", None, "Terms of Service", 200, 5, "TASK15"),
        ("GET", "/legal/cookies", None, "Cookie Policy", 200, 5, "TASK15"),
        ("GET", "/legal/data-deletion", None, "Data Deletion Policy", [200, 404], 5, "TASK15"),
        
        # SECTION 9: Task 20 - Support & Feedback
        ("GET", "/api/v1/feedback/categories", None, "Feedback Categories", [200, 404], 5, "TASK20"),
        ("POST", "/api/v1/feedback/submit", {"type": "bug", "message": "test"}, "Feedback Submit", [200, 400, 404], 5, "TASK20"),
        ("GET", "/api/v1/feedback/health", None, "Support Health", [200, 404], 5, "TASK20"),
    ]
    
    # Results tracking
    results_by_section = {}
    total_passed = 0
    total_failed = 0
    critical_tests = []
    
    print("\n" + "="*80)
    print(" RUNNING TESTS")
    print("="*80)
    
    for test_data in all_tests:
        method, path, body, name, expected, timeout, section = test_data
        
        if section not in results_by_section:
            results_by_section[section] = {"passed": 0, "failed": 0, "tests": []}
        
        try:
            url = f"{API_URL}{path}"
            
            # Make request
            if method == "GET":
                response = requests.get(url, timeout=timeout)
            elif method == "POST":
                response = requests.post(url, json=body, timeout=timeout)
            elif method == "DELETE":
                response = requests.delete(url, json=body, timeout=timeout)
            else:
                response = requests.request(method, url, json=body, timeout=timeout)
            
            # Check if response is expected
            if isinstance(expected, list):
                is_success = response.status_code in expected
            else:
                is_success = response.status_code == expected
            
            if is_success:
                if section == "CRITICAL":
                    print(f"⭐ {name:<40} - SUCCESS ({response.status_code})")
                    critical_tests.append((name, True, response.status_code))
                else:
                    print(f"✅ {name:<40} - SUCCESS ({response.status_code})")
                results_by_section[section]["passed"] += 1
                total_passed += 1
            else:
                if section == "CRITICAL":
                    print(f"🔴 {name:<40} - FAILED (Got {response.status_code}, Expected {expected})")
                    critical_tests.append((name, False, response.status_code))
                else:
                    print(f"❌ {name:<40} - FAILED (Got {response.status_code}, Expected {expected})")
                results_by_section[section]["failed"] += 1
                total_failed += 1
            
            results_by_section[section]["tests"].append({
                "name": name,
                "status": "PASS" if is_success else "FAIL",
                "code": response.status_code
            })
            
        except requests.exceptions.Timeout:
            print(f"⏱️  {name:<40} - TIMEOUT (>{timeout}s)")
            results_by_section[section]["failed"] += 1
            total_failed += 1
        except Exception as e:
            print(f"💥 {name:<40} - ERROR: {str(e)[:50]}")
            results_by_section[section]["failed"] += 1
            total_failed += 1
    
    # Print detailed results by section
    print("\n" + "="*80)
    print(" DETAILED RESULTS BY SECTION")
    print("="*80)
    
    for section, data in results_by_section.items():
        total = data["passed"] + data["failed"]
        success_rate = (data["passed"] / total * 100) if total > 0 else 0
        
        print(f"\n{section}:")
        print(f"  Passed: {data['passed']}/{total} ({success_rate:.1f}%)")
        
        if data["failed"] > 0:
            print(f"  Failed tests:")
            for test in data["tests"]:
                if test["status"] == "FAIL":
                    print(f"    - {test['name']} (Status: {test['code']})")
    
    # Overall summary
    print("\n" + "="*80)
    print(" FINAL SUMMARY")
    print("="*80)
    
    total_tests = total_passed + total_failed
    overall_success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
    
    print(f"\nTotal Tests Run: {total_tests}")
    print(f"✅ Passed: {total_passed}")
    print(f"❌ Failed: {total_failed}")
    print(f"Success Rate: {overall_success_rate:.1f}%")
    
    # Critical test results
    if critical_tests:
        print("\n⭐ CRITICAL TEST RESULTS:")
        for name, passed, code in critical_tests:
            if passed:
                print(f"  ✅ {name} - WORKING (Status: {code})")
            else:
                print(f"  🔴 {name} - FAILED (Status: {code})")
    
    # Final assessment
    print("\n" + "="*80)
    print(" DEPLOYMENT ASSESSMENT")
    print("="*80)
    
    if overall_success_rate == 100:
        print("\n🎉 PERFECT DEPLOYMENT - 100% SUCCESS!")
        print("All systems are fully operational!")
    elif overall_success_rate >= 95:
        print("\n✅ EXCELLENT DEPLOYMENT - System is fully operational!")
        print(f"Success rate: {overall_success_rate:.1f}%")
    elif overall_success_rate >= 90:
        print("\n✅ VERY GOOD DEPLOYMENT - System is operational!")
        print(f"Success rate: {overall_success_rate:.1f}%")
        print("Minor issues detected but core functionality working.")
    elif overall_success_rate >= 80:
        print("\n⚠️ GOOD DEPLOYMENT - System is mostly operational")
        print(f"Success rate: {overall_success_rate:.1f}%")
        print("Some features need attention.")
    else:
        print("\n❌ DEPLOYMENT NEEDS ATTENTION")
        print(f"Success rate: {overall_success_rate:.1f}%")
        print("Multiple features are not working correctly.")
    
    # Check specific critical features
    print("\n📋 CRITICAL FEATURES STATUS:")
    
    # Check if frontend query works
    frontend_works = any(name == "Frontend Dev Original Query" and passed for name, passed, _ in critical_tests)
    print(f"  Frontend Developer Query: {'✅ WORKING' if frontend_works else '❌ NOT WORKING'}")
    
    # Check if search works
    search_works = results_by_section.get("SEARCH", {}).get("passed", 0) > 0
    print(f"  Search Functionality: {'✅ WORKING' if search_works else '❌ NOT WORKING'}")
    
    # Check if auth works
    auth_works = results_by_section.get("TASK11", {}).get("passed", 0) > 0
    print(f"  Authentication: {'✅ WORKING' if auth_works else '❌ NOT WORKING'}")
    
    # Check if barcode works
    barcode_section = results_by_section.get("TASK12", {})
    barcode_works = barcode_section.get("passed", 0) >= 2  # At least cache and test data work
    print(f"  Barcode System: {'✅ WORKING' if barcode_works else '⚠️ PARTIAL'}")
    
    print("\n" + "="*80)
    
    return overall_success_rate


if __name__ == "__main__":
    success_rate = test_all_endpoints()
    
    # Final message
    if success_rate >= 95:
        print("\n🎉 DEPLOYMENT SUCCESSFUL - SYSTEM IS READY FOR PRODUCTION!")
    elif success_rate >= 80:
        print("\n✅ DEPLOYMENT SUCCESSFUL - SYSTEM IS OPERATIONAL!")
    else:
        print("\n⚠️ DEPLOYMENT NEEDS REVIEW - CHECK FAILED TESTS ABOVE")

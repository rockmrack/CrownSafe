#!/usr/bin/env python3
"""
Core API test - verify critical functionality
"""

import requests
import json
from datetime import datetime

API_URL = "https://babyshield.cureviax.ai"

def test_critical_endpoints():
    """Test the most critical endpoints"""
    print("="*70)
    print(" CRITICAL API FUNCTIONALITY TEST")
    print(f" Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    # 1. Test the main search that frontend developer reported
    print("\n1. Testing Frontend Developer's Exact Query:")
    print("-" * 50)
    try:
        response = requests.post(
            f"{API_URL}/api/v1/search/advanced",
            json={
                "product": "Triacting Night Time Cold",
                "agencies": ["FDA"],
                "date_from": "2014-01-01",
                "date_to": "2025-12-31",
                "limit": 5
            },
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ WORKING! Status: {response.status_code}")
            print(f"   Results found: {data.get('total_results', 0)}")
            if data.get('recalls'):
                print(f"   First result: {data['recalls'][0].get('title', 'N/A')[:60]}...")
        else:
            print(f"❌ FAILED! Status: {response.status_code}")
            print(f"   Error: {response.text[:200]}")
    except Exception as e:
        print(f"❌ ERROR: {str(e)[:100]}")
    
    # 2. Test database search capability
    print("\n2. Testing Database Search Capability:")
    print("-" * 50)
    test_searches = [
        {"product": "baby formula"},
        {"product": "car seat"},
        {"product": "crib"},
        {"product": "graco"}
    ]
    
    working = 0
    for search_params in test_searches:
        try:
            response = requests.post(
                f"{API_URL}/api/v1/search/advanced",
                json=search_params,
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                results = data.get('total_results', 0)
                print(f"✅ Search '{search_params['product']}': {results} results")
                working += 1
            else:
                print(f"❌ Search '{search_params['product']}': Failed ({response.status_code})")
        except:
            print(f"❌ Search '{search_params['product']}': Error")
    
    print(f"\nSearch Success Rate: {working}/{len(test_searches)}")
    
    # 3. Test API routes registration
    print("\n3. Checking Registered Routes:")
    print("-" * 50)
    try:
        response = requests.get(f"{API_URL}/openapi.json", timeout=10)
        if response.status_code == 200:
            openapi = response.json()
            paths = list(openapi.get('paths', {}).keys())
            print(f"✅ Found {len(paths)} registered routes:")
            
            # Check for new task routes
            task_routes = {
                "/api/v1/auth/apple": "Task 11 - OAuth",
                "/api/v1/user/data/export": "Task 11 - DSAR",
                "/api/v1/barcode/scan": "Task 12 - Barcode",
                "/api/v1/i18n/translations": "Task 13 - Localization",
                "/api/v1/monitoring/slo": "Task 14 - Monitoring",
                "/legal/privacy": "Task 15 - Legal",
                "/api/v1/feedback/submit": "Task 20 - Support"
            }
            
            for route, task in task_routes.items():
                if route in paths:
                    print(f"  ✅ {task}: {route}")
                else:
                    print(f"  ❌ {task}: {route} NOT FOUND")
    except:
        print("❌ Could not fetch OpenAPI spec")
    
    # 4. Test if new routers are included
    print("\n4. Checking Task Implementation Status:")
    print("-" * 50)
    
    endpoints_to_check = [
        # Task 11
        ("/api/v1/auth/apple", "POST", "Task 11: Apple OAuth"),
        ("/api/v1/auth/google", "POST", "Task 11: Google OAuth"),
        ("/api/v1/user/data/export", "GET", "Task 11: Data Export"),
        ("/api/v1/user/data/delete", "DELETE", "Task 11: Data Delete"),
        ("/api/v1/user/settings", "GET", "Task 11: User Settings"),
        
        # Task 12
        ("/api/v1/barcode/scan", "POST", "Task 12: Barcode Scan"),
        ("/api/v1/barcode/cache", "GET", "Task 12: Barcode Cache"),
        
        # Task 13
        ("/api/v1/i18n/translations", "GET", "Task 13: Translations"),
        ("/api/v1/i18n/accessibility", "GET", "Task 13: Accessibility"),
        
        # Task 14
        ("/api/v1/monitoring/slo", "GET", "Task 14: SLO Status"),
        ("/api/v1/monitoring/probe", "GET", "Task 14: Probe"),
        
        # Task 15
        ("/legal/privacy", "GET", "Task 15: Privacy Policy"),
        ("/legal/terms", "GET", "Task 15: Terms of Service"),
        
        # Task 20
        ("/api/v1/feedback/submit", "POST", "Task 20: Feedback"),
        ("/api/v1/feedback/categories", "GET", "Task 20: Categories"),
    ]
    
    implemented = 0
    for path, method, description in endpoints_to_check:
        try:
            if method == "GET":
                r = requests.get(f"{API_URL}{path}", timeout=2)
            elif method == "POST":
                r = requests.post(f"{API_URL}{path}", json={}, timeout=2)
            elif method == "DELETE":
                r = requests.delete(f"{API_URL}{path}", timeout=2)
            
            if r.status_code != 404:
                print(f"  ✅ {description}")
                implemented += 1
            else:
                print(f"  ❌ {description} - Not deployed")
        except:
            print(f"  ❌ {description} - Error")
    
    print(f"\nTasks Implemented: {implemented}/{len(endpoints_to_check)}")
    
    # 5. Summary
    print("\n" + "="*70)
    print(" DEPLOYMENT DIAGNOSIS")
    print("="*70)
    
    if implemented == 0:
        print("""
❌ ISSUE: New features from Tasks 11-22 are NOT deployed

TO FIX:
1. Ensure api/main_babyshield.py includes all routers:
   - oauth_endpoints (Task 11)
   - settings_endpoints (Task 11)
   - user_data_endpoints (Task 11)
   - barcode_bridge (Task 12)
   - localization (Task 13)
   - monitoring (Task 14)
   - legal_endpoints (Task 15)
   - feedback_endpoints (Task 20)

2. Rebuild Docker image:
   docker build -f Dockerfile.backend -t babyshield-backend:latest .

3. Push and deploy:
   docker push [YOUR_REGISTRY]/babyshield-backend:latest
   aws ecs update-service --force-new-deployment ...

4. Run database migrations:
   alembic upgrade head
        """)
    elif implemented < 10:
        print(f"⚠️ PARTIAL: Only {implemented} new endpoints deployed")
        print("Some routers may be missing from api/main_babyshield.py")
    else:
        print(f"✅ SUCCESS: {implemented} new endpoints are working!")


if __name__ == "__main__":
    test_critical_endpoints()

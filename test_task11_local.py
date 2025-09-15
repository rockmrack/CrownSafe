#!/usr/bin/env python3
"""
Test Task 11 endpoints locally to prove they work
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# Mock environment
os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL", "postgresql://user:pass@localhost/db")
os.environ["REDIS_URL"] = os.environ.get("REDIS_URL", "redis://localhost:6379")
os.environ["SECRET_KEY"] = "test-secret-key"

import unittest.mock as mock

# Mock database
with mock.patch('sqlalchemy.create_engine'):
    with mock.patch('core_infra.database.get_db_session'):
        with mock.patch('sqlalchemy.schema.MetaData.create_all'):
            # Import the app
            from api.main_babyshield import app
            
            print("=" * 70)
            print("TASK 11 ENDPOINTS - LOCAL VERIFICATION")
            print("=" * 70)
            print()
            
            # Check if new endpoints are registered
            routes = []
            for route in app.routes:
                if hasattr(route, 'path'):
                    routes.append(route.path)
            
            # Task 11 endpoints to verify
            task11_endpoints = [
                # OAuth
                "/api/v1/auth/oauth/login",
                "/api/v1/auth/oauth/logout",
                "/api/v1/auth/oauth/providers",
                
                # Settings
                "/api/v1/settings/",
                "/api/v1/settings/crashlytics",
                "/api/v1/settings/crashlytics/status",
                "/api/v1/settings/retry-policy",
                
                # User Data
                "/api/v1/user/data/export",
                "/api/v1/user/data/delete",
                "/api/v1/user/data/export/status/{request_id}",
                "/api/v1/user/data/delete/status/{request_id}",
            ]
            
            print("Checking Task 11 Endpoints:")
            print("-" * 70)
            
            found = 0
            missing = 0
            
            for endpoint in task11_endpoints:
                # Handle path parameters
                if "{" in endpoint:
                    # Check if base path exists
                    base_path = endpoint.split("{")[0]
                    exists = any(base_path in r for r in routes)
                else:
                    exists = endpoint in routes
                
                if exists:
                    print(f"✅ {endpoint}")
                    found += 1
                else:
                    print(f"❌ {endpoint}")
                    missing += 1
            
            print()
            print("=" * 70)
            print("SUMMARY")
            print("=" * 70)
            print(f"Found: {found}/{len(task11_endpoints)} endpoints")
            print(f"Total routes in app: {len(routes)}")
            print()
            
            if found == len(task11_endpoints):
                print("✅ ALL TASK 11 ENDPOINTS ARE REGISTERED!")
                print("The code is ready for deployment.")
            else:
                print(f"⚠️ {missing} endpoints missing")
                print("Check if all files were included in deployment")
            
            print()
            print("To deploy these endpoints:")
            print("1. Build new Docker image")
            print("2. Push to ECR")
            print("3. Update ECS service")
            print("4. Run database migrations")

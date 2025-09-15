#!/usr/bin/env python3
"""
Test if the API can start and routes are properly loaded
"""

import os
import sys

# Mock environment variables
os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL", "postgresql://user:pass@localhost/db")
os.environ["REDIS_URL"] = os.environ.get("REDIS_URL", "redis://localhost:6379")
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["ENVIRONMENT"] = "test"

# Mock the database connection to avoid connection errors
import unittest.mock as mock

# Mock SQLAlchemy engine
with mock.patch('sqlalchemy.create_engine') as mock_engine:
    mock_engine.return_value = mock.MagicMock()
    
    # Mock the database session
    with mock.patch('core_infra.database.get_db_session') as mock_session:
        mock_session.return_value = mock.MagicMock()
        
        # Mock Base.metadata.create_all
        with mock.patch('sqlalchemy.schema.MetaData.create_all'):
            
            # Now try to import the app
            try:
                from api.main_babyshield import app
                print("✅ App imported successfully!")
                
                # List all routes
                print("\n📋 Registered Routes:")
                print("=" * 60)
                
                routes = []
                for route in app.routes:
                    if hasattr(route, 'methods') and hasattr(route, 'path'):
                        for method in route.methods:
                            routes.append((method, route.path))
                
                # Sort routes for better readability
                routes.sort(key=lambda x: (x[1], x[0]))
                
                # Group by path prefix
                api_v1_routes = [r for r in routes if r[1].startswith('/api/v1')]
                other_routes = [r for r in routes if not r[1].startswith('/api/v1')]
                
                if api_v1_routes:
                    print("\n🔹 API v1 Routes:")
                    for method, path in api_v1_routes:
                        print(f"  {method:6} {path}")
                
                if other_routes:
                    print("\n🔹 Other Routes:")
                    for method, path in other_routes[:10]:  # Show first 10
                        print(f"  {method:6} {path}")
                
                # Check critical endpoints
                print("\n🔍 Critical Endpoints Check:")
                print("=" * 60)
                
                critical_paths = [
                    '/api/v1/healthz',
                    '/api/v1/version',
                    '/api/v1/search/advanced',
                    '/api/v1/user/privacy/summary',
                    '/api/v1/agencies',
                    '/api/v1/recall/{recall_id}'
                ]
                
                registered_paths = [r[1] for r in routes]
                
                for path in critical_paths:
                    # Check exact match or pattern match for parameterized routes
                    if path in registered_paths:
                        print(f"  ✅ {path}")
                    elif '{' in path:
                        # Check for parameterized route
                        base_path = path.split('{')[0]
                        if any(p.startswith(base_path) and '{' in p for p in registered_paths):
                            print(f"  ✅ {path}")
                        else:
                            print(f"  ❌ {path} - NOT FOUND")
                    else:
                        print(f"  ❌ {path} - NOT FOUND")
                
                # Count totals
                print(f"\n📊 Total Routes: {len(routes)}")
                print(f"   API v1 Routes: {len(api_v1_routes)}")
                
                # Check if search endpoint exists
                search_routes = [r for r in routes if 'search/advanced' in r[1]]
                if search_routes:
                    print(f"\n✅ SEARCH ENDPOINT FOUND: {search_routes}")
                else:
                    print("\n❌ SEARCH ENDPOINT NOT FOUND!")
                
            except Exception as e:
                print(f"❌ Failed to import app: {e}")
                import traceback
                traceback.print_exc()

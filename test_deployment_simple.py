#!/usr/bin/env python3
"""
Test if the API routes are properly loaded (simplified version without emojis)
"""

import os
import sys

# Set UTF-8 encoding
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

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
                print("[SUCCESS] App imported successfully!")
                
                # List all routes
                print("\n[ROUTES] Registered Routes:")
                print("=" * 60)
                
                routes = []
                for route in app.routes:
                    if hasattr(route, 'methods') and hasattr(route, 'path'):
                        for method in route.methods:
                            routes.append((method, route.path))
                
                # Sort routes for better readability
                routes.sort(key=lambda x: (x[1], x[0]))
                
                # Check for search endpoint
                search_found = False
                health_found = False
                
                for method, path in routes:
                    if path == '/api/v1/search/advanced':
                        print(f"[FOUND] {method} {path} <-- SEARCH ENDPOINT")
                        search_found = True
                    elif path == '/api/v1/healthz':
                        print(f"[FOUND] {method} {path} <-- HEALTH ENDPOINT")
                        health_found = True
                    elif '/api/v1' in path:
                        print(f"[ROUTE] {method} {path}")
                
                print(f"\n[STATS] Total Routes: {len(routes)}")
                print(f"[STATS] API v1 Routes: {len([r for r in routes if '/api/v1' in r[1]])}")
                
                if search_found:
                    print("\n[SUCCESS] SEARCH ENDPOINT IS REGISTERED!")
                else:
                    print("\n[ERROR] SEARCH ENDPOINT NOT FOUND!")
                
                if health_found:
                    print("[SUCCESS] HEALTH ENDPOINT IS REGISTERED!")
                else:
                    print("[ERROR] HEALTH ENDPOINT NOT FOUND!")
                
                # Check what happens when we access search service
                print("\n[TEST] Checking if search service can be imported...")
                try:
                    from services.search_service import SearchService
                    print("[SUCCESS] SearchService imported successfully")
                except Exception as e:
                    print(f"[ERROR] Cannot import SearchService: {e}")
                
            except Exception as e:
                print(f"[ERROR] Failed to import app: {e}")
                import traceback
                traceback.print_exc()

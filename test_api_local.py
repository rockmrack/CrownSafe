#!/usr/bin/env python3
"""Test if API can start locally and routes are registered"""

import os
import sys

# Set environment variables for testing
os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost/babyshield")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("ADMIN_API_KEY", "test-admin-key")

# Add path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from api.main_babyshield import app
    from fastapi.testclient import TestClient
    
    print("✅ App imported successfully")
    
    # List all routes
    print("\nRegistered routes:")
    for route in app.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            print(f"  {route.methods} {route.path}")
    
    # Check for search/advanced endpoint
    search_routes = [r for r in app.routes if hasattr(r, 'path') and 'search/advanced' in str(r.path)]
    if search_routes:
        print(f"\n✅ Found {len(search_routes)} search/advanced route(s)")
        for route in search_routes:
            print(f"  - {route.methods} {route.path}")
    else:
        print("\n❌ No search/advanced routes found!")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

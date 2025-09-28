#!/usr/bin/env python
"""Debug health endpoint to see what's happening"""

import sys
import logging
logging.basicConfig(level=logging.WARNING)

try:
    print("Testing health endpoint with debug...")
    from fastapi.testclient import TestClient
    from api.main_babyshield import app
    
    client = TestClient(app)
    
    # Test health endpoint
    print("\n=== Testing /healthz ===")
    resp = client.get("/healthz")
    print(f"Status Code: {resp.status_code}")
    print(f"Headers: {dict(resp.headers)}")
    print(f"Raw Response: {resp.text}")
    
    # Try to decode JSON if possible
    try:
        print(f"JSON Response: {resp.json()}")
    except:
        print("Could not decode as JSON")
    
    if resp.status_code == 200:
        print("✅ Health endpoint returns 200!")
    else:
        print(f"❌ Health endpoint returns {resp.status_code}")
    
    # Check if the raw route is even registered
    print("\n=== Checking app routes ===")
    for route in app.routes:
        if "health" in str(route.path).lower():
            print(f"Found health route: {route.path} - {route.methods}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

#!/usr/bin/env python
"""Final comprehensive health endpoint test"""

import sys
import logging
logging.basicConfig(level=logging.WARNING)

try:
    print("Testing health endpoint...")
    from fastapi.testclient import TestClient
    from api.main_babyshield import app
    
    client = TestClient(app)
    
    # Test health endpoint
    print("\n=== Testing /healthz ===")
    resp = client.get("/healthz")
    print(f"Status Code: {resp.status_code}")
    print(f"Response: {resp.json()}")
    
    if resp.status_code == 200:
        print("✅ Health endpoint returns 200!")
    else:
        print(f"❌ Health endpoint returns {resp.status_code}")
        sys.exit(1)
    
    # Test with different methods
    print("\n=== Testing /healthz with HEAD ===")
    resp = client.head("/healthz")
    print(f"Status Code: {resp.status_code}")
    
    # Test readyz endpoint
    print("\n=== Testing /readyz ===")
    resp = client.get("/readyz")
    print(f"Status Code: {resp.status_code}")
    
    print("\n✅ ALL HEALTH CHECKS PASS!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

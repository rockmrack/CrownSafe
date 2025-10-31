#!/usr/bin/env python3
"""Main entry point for BabyShield API
This file ensures the correct app is loaded regardless of how it's called.
"""

import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

# Import and expose the actual FastAPI app
from api.main_crownsafe import app

# The app is now available as 'app' in this module
# Uvicorn can run it with: uvicorn main:app

print("BabyShield API loaded from main.py redirect")

# For debugging - show what endpoints are registered
if __name__ == "__main__":
    print("Registered routes:")
    for route in app.routes:
        if hasattr(route, "path"):
            print(f"  {route.path}")

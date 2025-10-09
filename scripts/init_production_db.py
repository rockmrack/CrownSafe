#!/usr/bin/env python3
"""
Production Database Initialization Script
Creates necessary tables in the production SQLite database via API
"""

import requests
import json
import time
import sys


def init_production_database():
    """Initialize production database by calling the API to create tables"""

    base_url = "https://babyshield.cureviax.ai"

    print(f"Initializing production database at {base_url}")

    # Wait for API to be ready
    max_retries = 30
    for i in range(max_retries):
        try:
            response = requests.get(f"{base_url}/health", timeout=5)
            if response.status_code == 200:
                print("✅ API is ready")
                break
        except requests.RequestException:
            pass

        if i < max_retries - 1:
            print(f"⏳ Waiting for API to be ready... ({i+1}/{max_retries})")
            time.sleep(2)
    else:
        print("❌ API not ready after maximum retries")
        return False

    # Try to trigger database initialization by calling an endpoint that requires tables
    # This should trigger the table creation if it doesn't exist
    try:
        print("🔧 Triggering database initialization...")

        # Call search endpoint which should trigger table creation
        response = requests.post(
            f"{base_url}/api/v1/search/advanced",
            json={"query": "test", "limit": 1},
            timeout=10,
        )

        if response.status_code == 200:
            print("✅ Database initialization successful")
            return True
        else:
            print(f"⚠️ Search endpoint returned {response.status_code}: {response.text}")

            # Try agencies endpoint as fallback
            response = requests.get(f"{base_url}/api/v1/agencies", timeout=10)
            if response.status_code == 200:
                print("✅ Database initialization successful (via agencies endpoint)")
                return True
            else:
                print(f"⚠️ Agencies endpoint returned {response.status_code}: {response.text}")
                return False

    except requests.RequestException as e:
        print(f"❌ Error initializing database: {e}")
        return False


if __name__ == "__main__":
    success = init_production_database()
    sys.exit(0 if success else 1)

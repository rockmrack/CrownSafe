# scripts/setup_and_test.py

#!/usr/bin/env python3
"""
Complete setup and test script for BabyShield recall API
"""

import os
import subprocess
import sys
import time


def run_command(cmd, description):
    """Run a command and report status"""
    print(f"\n{'=' * 60}")
    print(f"🔧 {description}")
    print(f"Command: {cmd}")
    print("=" * 60)

    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    if result.returncode == 0:
        print("✅ Success")
        if result.stdout:
            print(result.stdout)
    else:
        print("❌ Failed")
        if result.stderr:
            print(f"Error: {result.stderr}")
        if result.stdout:
            print(f"Output: {result.stdout}")

    return result.returncode == 0


def main():
    print("🚀 BabyShield Live Test Setup")
    print("=" * 60)

    # Set environment variables
    db_path = os.path.abspath("babyshield_test.db")
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["TEST_MODE"] = "true"

    print(f"📁 Database path: {db_path}")
    print(f"🔗 Database URL: {os.environ['DATABASE_URL']}")

    # Step 1: Remove old database
    if os.path.exists(db_path):
        os.remove(db_path)
        print("🗑️  Removed old database")

    # Step 2: Seed the database
    if not run_command("python scripts/seed_for_live_test.py", "Seeding database with test data"):
        print("❌ Failed to seed database. Exiting.")
        return 1

    # Step 3: Start API server (if not already running)
    print("\n" + "=" * 60)
    print("📡 Checking API server...")
    print("=" * 60)

    # Check if API is already running
    import httpx

    try:
        response = httpx.get("http://127.0.0.1:8001/health", timeout=2)
        if response.status_code == 200:
            print("✅ API server is already running")
        else:
            print("⚠️  API server returned unexpected status")
    except (httpx.RequestError, httpx.TimeoutException):
        print("❌ API server is not running")
        print("Please start your API server with the same DATABASE_URL:")
        print(f"   export DATABASE_URL=sqlite:///{db_path}")
        print("   python main.py  # or docker-compose up")
        print("\nWaiting 10 seconds for you to start the server...")
        time.sleep(10)

    # Step 4: Run the live test
    if not run_command("python scripts/run_live_http_test.py", "Running live HTTP test"):
        print("❌ Live test failed")
        return 1

    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())

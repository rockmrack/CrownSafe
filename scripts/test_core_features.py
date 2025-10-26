#!/usr/bin/env python3
"""
Simplified test script for core BabyShield features
Tests only endpoints that don't require external dependencies
"""

import asyncio
import httpx
import json
from datetime import datetime

# API base URL
BASE_URL = "http://localhost:8001"


async def test_health():
    """Test health endpoint"""
    print("\n" + "=" * 60)
    print("Testing Health Endpoint")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/health")
            if response.status_code == 200:
                print("✅ Health check passed")
                print(f"Response: {response.json()}")
            else:
                print(f"❌ Health check failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Connection error: {e}")
            return False
    return True


async def test_safety_check():
    """Test basic safety check endpoint"""
    print("\n" + "=" * 60)
    print("Testing Safety Check Endpoint")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        request_data = {"user_id": 1, "product": "Baby Formula", "product_type": "food"}

        try:
            response = await client.post(f"{BASE_URL}/api/v1/safety-check", json=request_data)

            if response.status_code == 200:
                data = response.json()
                print("✅ Safety check completed")
                print(f"  Safety Level: {data.get('safety_level', 'Unknown')}")
                print(f"  Summary: {data.get('summary', 'No summary')[:100]}...")
            else:
                print(f"❌ Safety check failed: {response.status_code}")
                print(f"  Error: {response.text[:200]}")
        except Exception as e:
            print(f"❌ Connection error: {e}")


async def test_search_advanced():
    """Test advanced search endpoint"""
    print("\n" + "=" * 60)
    print("Testing Advanced Search Endpoint")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        request_data = {
            "product": "Baby Bottle",
            "agencies": ["FDA"],
            "date_from": "2020-01-01",
            "date_to": "2025-12-31",
            "limit": 5,
        }

        try:
            response = await client.post(f"{BASE_URL}/api/v1/search/advanced", json=request_data)

            if response.status_code == 200:
                data = response.json()
                print("✅ Advanced search completed")
                print(f"  Total Results: {data.get('total', 0)}")
                print(f"  Agencies: {data.get('agencies', 0)}")
                if data.get("recalls"):
                    print(f"  First Result: {data['recalls'][0].get('product_name', 'Unknown')[:50]}...")
            else:
                print(f"❌ Advanced search failed: {response.status_code}")
                print(f"  Error: {response.text[:200]}")
        except Exception as e:
            print(f"❌ Connection error: {e}")


async def test_mobile_scan():
    """Test mobile scan endpoint"""
    print("\n" + "=" * 60)
    print("Testing Mobile Scan Endpoint")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        request_data = {"barcode": "123456789012", "user_id": 1, "scan_type": "upc"}

        try:
            response = await client.post(f"{BASE_URL}/api/v1/mobile/scan", json=request_data)

            if response.status_code in [200, 404]:  # 404 is ok for non-existent barcode
                data = response.json()
                print("✅ Mobile scan completed")
                print(f"  Status: {data.get('status', 'Unknown')}")
                print(f"  Safety Level: {data.get('safety_level', 'Unknown')}")
                if data.get("summary"):
                    print(f"  Summary: {data['summary'][:100]}...")
            else:
                print(f"❌ Mobile scan failed: {response.status_code}")
                print(f"  Error: {response.text[:200]}")
        except Exception as e:
            print(f"❌ Connection error: {e}")


async def test_user_endpoints():
    """Test user management endpoints"""
    print("\n" + "=" * 60)
    print("Testing User Endpoints")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        # Test user creation
        user_data = {
            "email": f"test_{datetime.now().timestamp()}@example.com",
            "password": "TestPassword123!",
            "is_subscribed": True,
        }

        try:
            response = await client.post(f"{BASE_URL}/api/v1/users", json=user_data)

            if response.status_code in [200, 201]:
                data = response.json()
                print("✅ User creation successful")
                print(f"  User ID: {data.get('id', 'Unknown')}")
                print(f"  Email: {data.get('email', 'Unknown')}")
            elif response.status_code == 400:
                print("⚠️ User might already exist")
            else:
                print(f"❌ User creation failed: {response.status_code}")
                print(f"  Error: {response.text[:200]}")
        except Exception as e:
            print(f"❌ Connection error: {e}")


async def test_system_stats():
    """Test system statistics endpoint"""
    print("\n" + "=" * 60)
    print("Testing System Statistics")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/api/v1/admin/system-stats")

            if response.status_code == 200:
                data = response.json()
                print("✅ System stats retrieved")
                print(f"  Database: {data.get('database', {}).get('status', 'Unknown')}")
                print(f"  Total Recalls: {data.get('database', {}).get('total_recalls', 0)}")
                print(f"  API Version: {data.get('api_version', 'Unknown')}")
            else:
                print(f"❌ System stats failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Connection error: {e}")


async def main():
    """Run core tests"""
    print("\n" + "BABYSHIELD CORE FEATURES TEST".center(60, "="))
    print(f"Testing against: {BASE_URL}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Check if server is running
    if not await test_health():
        print("\n❌ API server is not running!")
        print("Please start the server with:")
        print('  $env:DATABASE_URL="sqlite:///./babyshield_test.db"')
        print('  $env:TEST_MODE="true"')
        print("  python -m uvicorn api.main_crownsafe:app --host 0.0.0.0 --port 8001")
        return

    # Run tests
    await test_safety_check()
    await test_search_advanced()
    await test_mobile_scan()
    await test_user_endpoints()
    await test_system_stats()

    print("\n" + "=" * 60)
    print("✅ Core feature tests completed!")
    print(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

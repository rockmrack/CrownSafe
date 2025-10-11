#!/usr/bin/env python3
"""
Test script for Premium Features API endpoints (Pregnancy & Allergy)
Tests both direct endpoints and integration with main safety check
"""

import asyncio
import httpx
import json
from datetime import datetime

# API base URL - adjust as needed
BASE_URL = "http://localhost:8001"  # Local testing
# BASE_URL = "https://babyshield.cureviax.ai"  # Production


async def test_pregnancy_endpoint():
    """Test the pregnancy safety check endpoint"""
    print("\n" + "=" * 60)
    print("Testing Pregnancy Safety Check Endpoint")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        # Test with a product containing retinol (unsafe for pregnancy)
        request_data = {
            "barcode": "5060381320015",  # Product with retinol in mock data
            "trimester": 2,
            "user_id": 1,
        }

        try:
            response = await client.post(
                f"{BASE_URL}/api/v1/premium/pregnancy/check", json=request_data
            )

            if response.status_code == 200:
                data = response.json()
                print(f"✅ Status: {data['status']}")
                print(f"Product: {data['product_name']}")
                print(f"Safe for pregnancy: {data['is_safe']}")
                print(f"Risk Level: {data.get('risk_level', 'N/A')}")

                if data["alerts"]:
                    print("\n⚠️ Pregnancy Safety Alerts:")
                    for alert in data["alerts"]:
                        print(
                            f"  - {alert['ingredient']}: {alert.get('reason', 'Risk during pregnancy')}"
                        )

                if data["recommendations"]:
                    print("\n📋 Recommendations:")
                    for rec in data["recommendations"]:
                        print(f"  - {rec}")
            else:
                print(f"❌ Error: {response.status_code} - {response.text}")

        except Exception as e:
            print(f"❌ Connection error: {e}")


async def test_allergy_endpoint():
    """Test the allergy check endpoint"""
    print("\n" + "=" * 60)
    print("Testing Allergy Check Endpoint")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        # Test with a product containing peanut traces
        request_data = {
            "barcode": "038000222015",  # Product with peanut traces in mock data
            "user_id": 1,
            "check_all_members": True,
        }

        try:
            response = await client.post(
                f"{BASE_URL}/api/v1/premium/allergy/check", json=request_data
            )

            if response.status_code == 200:
                data = response.json()
                print(f"✅ Status: {data['status']}")
                print(f"Product: {data['product_name']}")
                print(f"Safe for family: {data['is_safe']}")

                if data["alerts"]:
                    print("\n⚠️ Allergy Alerts:")
                    for alert in data["alerts"]:
                        allergens = ", ".join(alert.get("found_allergens", []))
                        print(f"  - {alert['member_name']}: Contains {allergens}")

                if data["safe_for_members"]:
                    print(f"\n✅ Safe for: {', '.join(data['safe_for_members'])}")

                if data["unsafe_for_members"]:
                    print("\n❌ Unsafe for:")
                    for member in data["unsafe_for_members"]:
                        print(
                            f"  - {member['member_name']}: {', '.join(member['allergens_found'])}"
                        )
            else:
                print(f"❌ Error: {response.status_code} - {response.text}")

        except Exception as e:
            print(f"❌ Connection error: {e}")


async def test_family_members_endpoint():
    """Test family member management endpoints"""
    print("\n" + "=" * 60)
    print("Testing Family Member Management")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        # 1. Get existing family members
        try:
            response = await client.get(
                f"{BASE_URL}/api/v1/premium/family/members", params={"user_id": 1}
            )

            if response.status_code == 200:
                members = response.json()
                print(f"✅ Current family members: {len(members)}")
                for member in members:
                    print(
                        f"  - {member['name']}: Allergies: {', '.join(member['allergies']) if member['allergies'] else 'None'}"
                    )
            else:
                print(f"❌ Error getting members: {response.status_code}")

        except Exception as e:
            print(f"❌ Connection error: {e}")

        # 2. Add a new family member
        print("\n📝 Adding new family member...")
        new_member = {
            "name": "Test Baby",
            "relationship": "Child",
            "allergies": ["milk", "eggs"],
            "age": 2,
        }

        try:
            response = await client.post(
                f"{BASE_URL}/api/v1/premium/family/members",
                params={"user_id": 1},
                json=new_member,
            )

            if response.status_code == 200:
                member = response.json()
                print(f"✅ Added: {member['name']} (ID: {member['id']})")
                print(f"  Allergies: {', '.join(member['allergies'])}")
                return member["id"]  # Return for later deletion
            else:
                print(f"❌ Error adding member: {response.status_code} - {response.text}")

        except Exception as e:
            print(f"❌ Connection error: {e}")

    return None


async def test_integrated_safety_check():
    """Test pregnancy and allergy integration in main safety check"""
    print("\n" + "=" * 60)
    print("Testing Integrated Safety Check (with Premium Features)")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        # Test with all features enabled
        request_data = {
            "user_id": 1,
            "barcode": "5060381320015",  # Product with retinol
            "check_pregnancy": True,
            "pregnancy_trimester": 1,
            "check_allergies": True,
        }

        try:
            response = await client.post(f"{BASE_URL}/api/v1/safety-check", json=request_data)

            if response.status_code == 200:
                data = response.json()
                print(f"✅ Status: {data['status']}")

                if data.get("data"):
                    result = data["data"]

                    # Check for pregnancy safety results
                    if "pregnancy_safety" in result:
                        print("\n🤰 Pregnancy Safety:")
                        preg = result["pregnancy_safety"]
                        print(f"  Safe: {preg.get('safe', 'Unknown')}")
                        if preg.get("alerts"):
                            for alert in preg["alerts"]:
                                print(f"  ⚠️ {alert['ingredient']}: {alert.get('reason', 'Risk')}")

                    # Check for allergy safety results
                    if "allergy_safety" in result:
                        print("\n🥜 Allergy Safety:")
                        allergy = result["allergy_safety"]
                        print(f"  Safe: {allergy.get('safe', 'Unknown')}")
                        if allergy.get("alerts"):
                            for alert in allergy["alerts"]:
                                print(
                                    f"  ⚠️ {alert['member_name']}: {', '.join(alert.get('found_allergens', []))}"
                                )

                    # Check if premium checks were performed
                    if result.get("premium_checks_performed"):
                        print("\n✨ Premium safety checks were included in the results")

                    # Display summary with premium alerts
                    if "summary" in result and "PREMIUM SAFETY ALERTS" in result["summary"]:
                        print("\n📄 Enhanced Summary (with premium alerts):")
                        print(result["summary"])

            else:
                print(f"❌ Error: {response.status_code} - {response.text}")

        except Exception as e:
            print(f"❌ Connection error: {e}")


async def test_mobile_scan_with_premium():
    """Test mobile scan with pregnancy and allergy features"""
    print("\n" + "=" * 60)
    print("Testing Mobile Scan with Premium Features")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        request_data = {
            "user_id": 1,
            "barcode": "5060381320015",
            "quick_scan": True,
            "check_pregnancy": True,
            "pregnancy_trimester": 2,
            "check_allergies": True,
        }

        try:
            response = await client.post(f"{BASE_URL}/api/v1/mobile/scan", json=request_data)

            if response.status_code == 200:
                data = response.json()
                print(f"✅ Status: {data['status']}")
                print(
                    f"Safety Level: {data['safety_level']} ({'🟢' if data['safety_level'] == 'SAFE' else '🔴' if data['safety_level'] == 'DANGER' else '🟡'})"
                )
                print(f"Response Time: {data.get('response_time_ms', 'N/A')}ms")

                if data.get("pregnancy_alerts"):
                    print("\n🤰 Pregnancy Alerts:")
                    for alert in data["pregnancy_alerts"]:
                        print(f"  - {alert}")

                if data.get("allergy_alerts"):
                    print("\n🥜 Allergy Alerts:")
                    for alert in data["allergy_alerts"]:
                        print(f"  - {alert}")

                print(f"\n📝 Summary: {data['summary']}")

            else:
                print(f"❌ Error: {response.status_code} - {response.text}")

        except Exception as e:
            print(f"❌ Connection error: {e}")


async def test_comprehensive_safety():
    """Test the comprehensive safety check endpoint"""
    print("\n" + "=" * 60)
    print("Testing Comprehensive Safety Check")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        request_data = {
            "barcode": "5060381320015",
            "user_id": 1,
            "check_pregnancy": True,
            "trimester": 1,
            "check_allergies": True,
        }

        try:
            response = await client.post(
                f"{BASE_URL}/api/v1/premium/safety/comprehensive", json=request_data
            )

            if response.status_code == 200:
                data = response.json()
                print(f"✅ Overall Safety: {data['overall_safety']}")
                print(f"Checks Performed: {', '.join(data['checks_performed'])}")

                if data["risk_factors"]:
                    print("\n⚠️ Risk Factors:")
                    for risk in data["risk_factors"]:
                        print(f"  Type: {risk['type']}")
                        for alert in risk.get("alerts", []):
                            if risk["type"] == "pregnancy":
                                print(f"    - {alert['ingredient']}: {alert.get('reason', 'Risk')}")
                            elif risk["type"] == "allergies":
                                print(
                                    f"    - {alert['member_name']}: {', '.join(alert.get('found_allergens', []))}"
                                )

                if data["recommendations"]:
                    print("\n📋 Recommendations:")
                    for rec in data["recommendations"]:
                        print(f"  - {rec}")

            else:
                print(f"❌ Error: {response.status_code} - {response.text}")

        except Exception as e:
            print(f"❌ Connection error: {e}")


async def main():
    """Run all tests"""
    print("\n" + "🚀 BABYSHIELD PREMIUM FEATURES API TEST SUITE 🚀".center(60, "="))
    print(f"Testing against: {BASE_URL}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Run individual endpoint tests
    await test_pregnancy_endpoint()
    await test_allergy_endpoint()
    _ = await test_family_members_endpoint()  # member_id

    # Test integration with main safety check
    await test_integrated_safety_check()

    # Test mobile endpoints
    await test_mobile_scan_with_premium()

    # Test comprehensive safety check
    await test_comprehensive_safety()

    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)


if __name__ == "__main__":
    # For local testing, make sure the API is running:
    # uvicorn api.main_babyshield:app --host 0.0.0.0 --port 8001
    asyncio.run(main())

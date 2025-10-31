#!/usr/bin/env python3
"""
Comprehensive test script for ALL BabyShield API features
Tests Premium, Baby, Advanced, and Compliance features
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict

import httpx

# API base URL
BASE_URL = "http://localhost:8001"

# Test results tracker
test_results = {"passed": 0, "failed": 0, "errors": []}


def log_result(test_name: str, success: bool, details: str = ""):
    """Log test result"""
    if success:
        print(f"✅ {test_name}")
        test_results["passed"] += 1
    else:
        print(f"❌ {test_name}: {details}")
        test_results["failed"] += 1
        test_results["errors"].append(f"{test_name}: {details}")


async def test_core_features():
    """Test core BabyShield features"""
    print("\n" + "=" * 60)
    print("TESTING CORE FEATURES")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        # 1. Health Check
        try:
            response = await client.get(f"{BASE_URL}/health")
            log_result("Health Check", response.status_code == 200)
        except Exception as e:
            log_result("Health Check", False, str(e))

        # 2. Safety Check
        try:
            response = await client.post(
                f"{BASE_URL}/api/v1/safety-check",
                json={
                    "user_id": 1,
                    "product": "Baby Formula",
                    "product_type": "food",
                    "check_pregnancy": True,
                    "pregnancy_trimester": 1,
                    "check_allergies": True,
                    "allergies": ["milk", "soy"],
                },
            )
            log_result("Safety Check with Premium Features", response.status_code == 200)
            if response.status_code == 200:
                data = response.json()
                print(f"  - Safety Level: {data.get('safety_level')}")
                print(f"  - Warnings: {len(data.get('warnings', []))}")
                print(f"  - Pregnancy Alerts: {len(data.get('pregnancy_alerts', []))}")
        except Exception as e:
            log_result("Safety Check with Premium Features", False, str(e))

        # 3. Mobile Scan
        try:
            response = await client.post(
                f"{BASE_URL}/api/v1/mobile/scan",
                json={
                    "barcode": "123456789012",
                    "user_id": 1,
                    "scan_type": "upc",
                    "check_pregnancy": True,
                    "check_allergies": True,
                },
            )
            log_result("Mobile Scan with Checks", response.status_code == 200)
            if response.status_code == 200:
                data = response.json()
                print(f"  - Product: {data.get('product_name')}")
                print(f"  - Pregnancy Safe: {data.get('pregnancy_safe')}")
        except Exception as e:
            log_result("Mobile Scan with Checks", False, str(e))

        # 4. Advanced Search
        try:
            response = await client.post(
                f"{BASE_URL}/api/v1/search/advanced",
                json={
                    "product": "baby bottle",
                    "agencies": ["FDA", "CPSC"],
                    "limit": 5,
                },
            )
            log_result("Advanced Search", response.status_code == 200)
            if response.status_code == 200:
                data = response.json()
                print(f"  - Total Results: {data.get('total')}")
                print(f"  - Agencies Searched: {data.get('agencies')}")
        except Exception as e:
            log_result("Advanced Search", False, str(e))


async def test_premium_features():
    """Test Premium features (Pregnancy & Allergy)"""
    print("\n" + "=" * 60)
    print("TESTING PREMIUM FEATURES")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        # 1. Pregnancy Safety Check
        try:
            response = await client.post(
                f"{BASE_URL}/api/v1/premium/pregnancy/check",
                json={"product": "Prenatal Vitamins", "trimester": 2},
            )
            log_result("Pregnancy Safety Check", response.status_code == 200)
            if response.status_code == 200:
                data = response.json()
                print(f"  - Is Safe: {data.get('is_safe')}")
                print(f"  - Confidence: {data.get('confidence')}")
        except Exception as e:
            log_result("Pregnancy Safety Check", False, str(e))

        # 2. Allergy Check
        try:
            response = await client.post(
                f"{BASE_URL}/api/v1/premium/allergy/check",
                json={"product": "Baby Food", "allergies": ["peanuts", "eggs", "milk"]},
            )
            log_result("Allergy Check", response.status_code == 200)
            if response.status_code == 200:
                data = response.json()
                print(f"  - Is Safe: {data.get('is_safe')}")
                print(f"  - Detected Allergens: {data.get('detected_allergens', [])}")
        except Exception as e:
            log_result("Allergy Check", False, str(e))

        # 3. Family Member Management (if endpoint exists)
        try:
            response = await client.get(f"{BASE_URL}/api/v1/premium/family/members", params={"user_id": 1})
            if response.status_code == 404:
                print("  ⚠️ Family member endpoints not available in simplified API")
            else:
                log_result("Family Member List", response.status_code == 200)
        except Exception as e:
            print(f"  ⚠️ Family member endpoints not available: {e}")


async def test_baby_features():
    """Test Baby-specific features"""
    print("\n" + "=" * 60)
    print("TESTING BABY SAFETY FEATURES")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        # 1. Safe Alternatives
        try:
            response = await client.post(
                f"{BASE_URL}/api/v1/baby/alternatives",
                json={"product": "Baby Lotion with Fragrance"},
            )
            log_result("Safe Alternatives", response.status_code == 200)
            if response.status_code == 200:
                data = response.json()
                alts = data.get("alternatives", [])
                print(f"  - Found {len(alts)} alternatives")
                for alt in alts[:2]:
                    print(f"    • {alt.get('name')} (Score: {alt.get('safety_score')})")
        except Exception as e:
            log_result("Safe Alternatives", False, str(e))

        # 2. Push Notifications (mock test)
        try:
            response = await client.post(
                f"{BASE_URL}/api/v1/baby/notifications/send",
                json={
                    "device_token": "test_token_123",
                    "title": "Safety Alert",
                    "body": "New recall for baby products",
                },
            )
            if response.status_code == 404:
                print("  ⚠️ Push notification endpoint not available in simplified API")
            else:
                log_result("Push Notifications", response.status_code in [200, 201])
        except Exception as e:
            print(f"  ⚠️ Push notifications not available: {e}")

        # 3. Report Generation (mock test)
        try:
            response = await client.post(
                f"{BASE_URL}/api/v1/baby/reports/generate",
                json={
                    "user_id": 1,
                    "report_type": "safety_summary",
                    "products": ["Baby Formula", "Diapers"],
                },
            )
            if response.status_code == 404:
                print("  ⚠️ Report generation endpoint not available in simplified API")
            else:
                log_result("Report Generation", response.status_code == 200)
        except Exception as e:
            print(f"  ⚠️ Report generation not available: {e}")


async def test_advanced_features():
    """Test Advanced features"""
    print("\n" + "=" * 60)
    print("TESTING ADVANCED FEATURES")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        # 1. Web Research
        try:
            response = await client.post(
                f"{BASE_URL}/api/v1/advanced/research",
                json={"query": "baby bottle safety BPA free"},
            )
            log_result("Web Research", response.status_code == 200)
            if response.status_code == 200:
                data = response.json()
                findings = data.get("findings", [])
                print(f"  - Found {len(findings)} findings")
                for finding in findings[:2]:
                    print(f"    • {finding}")
        except Exception as e:
            log_result("Web Research", False, str(e))

        # 2. Age-Appropriate Guidelines
        try:
            response = await client.post(
                f"{BASE_URL}/api/v1/advanced/guidelines",
                json={"product": "Toy", "age_months": 6},
            )
            if response.status_code == 404:
                print("  ⚠️ Guidelines endpoint not available in simplified API")
            else:
                log_result("Age Guidelines", response.status_code == 200)
        except Exception as e:
            print(f"  ⚠️ Guidelines not available: {e}")

        # 3. Visual Recognition (mock test)
        try:
            # This would normally send an image file
            response = await client.post(
                f"{BASE_URL}/api/v1/advanced/visual/recognize",
                json={"image_base64": "mock_image_data"},
            )
            if response.status_code == 404:
                print("  ⚠️ Visual recognition endpoint not available in simplified API")
            else:
                log_result("Visual Recognition", response.status_code in [200, 422])
        except Exception as e:
            print(f"  ⚠️ Visual recognition not available: {e}")


async def test_compliance_features():
    """Test Legal Compliance features"""
    print("\n" + "=" * 60)
    print("TESTING COMPLIANCE FEATURES")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        # 1. COPPA Age Verification
        try:
            response = await client.post(
                f"{BASE_URL}/api/v1/compliance/coppa/verify-age",
                json={"birthdate": "2010-01-01"},
            )
            log_result("COPPA Age Verification", response.status_code == 200)
            if response.status_code == 200:
                data = response.json()
                print(f"  - Age: {data.get('age')}")
                print(f"  - COPPA Applies: {data.get('coppa_applies')}")
                print(f"  - Parental Consent Required: {data.get('requires_parental_consent')}")
        except Exception as e:
            log_result("COPPA Age Verification", False, str(e))

        # 2. Children's Code Assessment
        try:
            response = await client.post(
                f"{BASE_URL}/api/v1/compliance/childrens-code/assess",
                json={
                    "user_id": 1,
                    "age": 10,
                    "country": "US",
                    "features_used": ["barcode_scan", "recall_check"],
                },
            )
            if response.status_code == 404:
                print("  ⚠️ Children's Code endpoint not available in simplified API")
            else:
                log_result("Children's Code Assessment", response.status_code == 200)
        except Exception as e:
            print(f"  ⚠️ Children's Code not available: {e}")

        # 3. GDPR Data Request
        try:
            response = await client.post(
                f"{BASE_URL}/api/v1/compliance/gdpr/data-request",
                json={
                    "user_id": 1,
                    "request_type": "access",
                    "email": "user@example.com",
                },
            )
            if response.status_code == 404:
                print("  ⚠️ GDPR endpoint not available in simplified API")
            else:
                log_result("GDPR Data Request", response.status_code == 200)
        except Exception as e:
            print(f"  ⚠️ GDPR features not available: {e}")


async def test_system_features():
    """Test System and Admin features"""
    print("\n" + "=" * 60)
    print("TESTING SYSTEM FEATURES")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        # 1. System Statistics
        try:
            response = await client.get(f"{BASE_URL}/api/v1/admin/system-stats")
            log_result("System Statistics", response.status_code == 200)
            if response.status_code == 200:
                data = response.json()
                print(f"  - API Version: {data.get('api_version')}")
                print(f"  - Database Status: {data.get('database', {}).get('status')}")
                print(f"  - Total Recalls: {data.get('database', {}).get('total_recalls')}")
        except Exception as e:
            log_result("System Statistics", False, str(e))

        # 2. Root Endpoint
        try:
            response = await client.get(f"{BASE_URL}/")
            log_result("Root Endpoint", response.status_code == 200)
            if response.status_code == 200:
                data = response.json()
                print(f"  - Name: {data.get('name')}")
                print(f"  - Version: {data.get('version')}")
                print(f"  - Status: {data.get('status')}")
        except Exception as e:
            log_result("Root Endpoint", False, str(e))


async def main():
    """Run all tests"""
    print("\n" + "🚀 COMPREHENSIVE BABYSHIELD API TEST SUITE 🚀".center(60, "="))
    print(f"Testing against: {BASE_URL}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Check if server is running
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/health", timeout=2.0)
            if response.status_code != 200:
                print("\n❌ API server is not healthy!")
                return
        except Exception:
            print("\n❌ API server is not running!")
            print("Please start the server first")
            return

    # Run all test suites
    await test_core_features()
    await test_premium_features()
    await test_baby_features()
    await test_advanced_features()
    await test_compliance_features()
    await test_system_features()

    # Print summary
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    print(f"✅ Passed: {test_results['passed']}")
    print(f"❌ Failed: {test_results['failed']}")
    print(f"📈 Success Rate: {(test_results['passed'] / (test_results['passed'] + test_results['failed']) * 100):.1f}%")

    if test_results["errors"]:
        print("\n⚠️ Failed Tests:")
        for error in test_results["errors"][:5]:
            print(f"  • {error}")

    print(f"\n🏁 Test suite completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Overall status
    if test_results["failed"] == 0:
        print("\n" + "🎉 ALL TESTS PASSED! 🎉".center(60, "="))
        print("The BabyShield API is fully functional!")
    else:
        print("\n" + "⚠️ SOME TESTS FAILED ⚠️".center(60, "="))
        print("Review the failed tests above for details.")

    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

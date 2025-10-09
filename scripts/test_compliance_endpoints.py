#!/usr/bin/env python3
"""
Test script for Legal Compliance API endpoints
Tests COPPA, Children's Code, GDPR, and legal content management
"""

import asyncio
import httpx
import json
from datetime import datetime, date

# API base URL - adjust as needed
BASE_URL = "http://localhost:8001"  # Local testing
# BASE_URL = "https://babyshield.cureviax.ai"  # Production


async def test_coppa_age_verification():
    """Test COPPA age verification"""
    print("\n" + "=" * 60)
    print("Testing COPPA Age Verification")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        # Test different age scenarios
        test_cases = [
            {"birthdate": "2015-01-01", "age": 9, "desc": "Under 13 (COPPA applies)"},
            {"birthdate": "2008-01-01", "age": 16, "desc": "Teenager (no COPPA)"},
            {"birthdate": "2000-01-01", "age": 24, "desc": "Adult"},
        ]

        for test in test_cases:
            print(f"\n📋 Testing: {test['desc']}")

            request_data = {
                "email": f"test{test['age']}@example.com",
                "birthdate": test["birthdate"],
                "country": "US",
                "verification_method": "birthdate",
            }

            try:
                response = await client.post(
                    f"{BASE_URL}/api/v1/compliance/coppa/verify-age", json=request_data
                )

                if response.status_code == 200:
                    data = response.json()
                    print(f"  ✅ Age: {data['age']} years")
                    print(f"  COPPA Applies: {'Yes ⚠️' if data['coppa_applies'] else 'No ✅'}")
                    print(
                        f"  Parental Consent Required: {'Yes' if data['requires_parental_consent'] else 'No'}"
                    )

                    if data.get("verification_token"):
                        print(f"  Token Generated: {data['verification_token'][:20]}...")

                    if data.get("restrictions"):
                        print(f"  Restrictions: {len(data['restrictions'])} applied")
                        for restriction in data["restrictions"][:2]:
                            print(f"    • {restriction}")
                else:
                    print(f"  ❌ Error: {response.status_code}")

            except Exception as e:
                print(f"  ❌ Connection error: {e}")


async def test_parental_consent():
    """Test parental consent submission"""
    print("\n" + "=" * 60)
    print("Testing Parental Consent")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        request_data = {
            "child_email": "child@example.com",
            "parent_email": "parent@example.com",
            "parent_name": "John Parent",
            "consent_types": ["coppa_parental", "data_processing"],
            "verification_token": "test_token_123",
            "verification_method": "credit_card",
            "credit_card_last4": "1234",
        }

        try:
            response = await client.post(
                f"{BASE_URL}/api/v1/compliance/coppa/parental-consent",
                json=request_data,
            )

            if response.status_code == 200:
                data = response.json()
                print(f"✅ Consent Status: {data['status']}")
                print(f"  Consent ID: {data['consent_id']}")
                print(f"  Parent: {data['parent_email']}")
                print(f"  Child: {data['child_email']}")
                print(f"  Verification Method: {data['verification_method']}")

                if data.get("expires_at"):
                    print(f"  Expires: {data['expires_at']}")

                if data.get("consents_granted"):
                    print(f"  Consents Granted: {', '.join(data['consents_granted'])}")
            else:
                print(f"❌ Error: {response.status_code} - {response.text[:200]}")

        except Exception as e:
            print(f"❌ Connection error: {e}")


async def test_childrens_code():
    """Test Children's Code compliance assessment"""
    print("\n" + "=" * 60)
    print("Testing Children's Code Compliance")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        # Test for different age groups
        test_cases = [
            {"age": 8, "country": "GB"},
            {"age": 14, "country": "EU"},
            {"age": 17, "country": "US"},
        ]

        for test in test_cases:
            print(f"\n📋 Age {test['age']} in {test['country']}")

            request_data = {
                "user_id": 1,
                "age": test["age"],
                "country": test["country"],
                "features_used": ["barcode_scan", "recall_check", "notifications"],
                "data_collected": ["personal", "behavioral"],
                "third_party_sharing": False,
            }

            try:
                response = await client.post(
                    f"{BASE_URL}/api/v1/compliance/childrens-code/assess",
                    json=request_data,
                )

                if response.status_code == 200:
                    data = response.json()
                    print(f"  Compliant: {'✅ Yes' if data['compliant'] else '❌ No'}")
                    print(f"  Age Appropriate: {'✅' if data['age_appropriate'] else '❌'}")
                    print(
                        f"  Parental Controls Required: {'Yes' if data['parental_controls_required'] else 'No'}"
                    )

                    if data.get("prohibited_features"):
                        print(f"  ⛔ Prohibited Features:")
                        for feature in data["prohibited_features"]:
                            print(f"    • {feature}")

                    if data.get("required_safeguards"):
                        print(f"  🛡️ Required Safeguards: {len(data['required_safeguards'])}")
                        for safeguard in data["required_safeguards"][:2]:
                            print(f"    • {safeguard}")

                    if data.get("privacy_settings"):
                        print(f"  🔒 Privacy Settings:")
                        for key, value in list(data["privacy_settings"].items())[:3]:
                            print(f"    • {key}: {value}")
                else:
                    print(f"  ❌ Error: {response.status_code}")

            except Exception as e:
                print(f"  ❌ Connection error: {e}")


async def test_gdpr_data_requests():
    """Test GDPR data request submission"""
    print("\n" + "=" * 60)
    print("Testing GDPR Data Requests")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        # Test different request types
        request_types = ["access", "erasure", "portability"]

        for req_type in request_types:
            print(f"\n📋 Testing: Right to {req_type}")

            request_data = {
                "user_id": 1,
                "request_type": req_type,
                "email": "user@example.com",
                "reason": f"Testing {req_type} request",
            }

            try:
                response = await client.post(
                    f"{BASE_URL}/api/v1/compliance/gdpr/data-request", json=request_data
                )

                if response.status_code == 200:
                    data = response.json()
                    print(f"  ✅ Request ID: {data['request_id']}")
                    print(f"  Status: {data['status']}")
                    print(f"  Estimated Completion: {data['estimated_completion']}")
                    print(f"  Message: {data['message']}")

                    # Check status
                    if data.get("request_id"):
                        status_response = await client.get(
                            f"{BASE_URL}/api/v1/compliance/gdpr/request-status/{data['request_id']}",
                            params={"user_id": 1},
                        )

                        if status_response.status_code == 200:
                            status_data = status_response.json()
                            print(f"  📊 Status Check: {status_data['status']}")
                else:
                    print(f"  ❌ Error: {response.status_code}")

            except Exception as e:
                print(f"  ❌ Connection error: {e}")


async def test_legal_documents():
    """Test legal document retrieval"""
    print("\n" + "=" * 60)
    print("Testing Legal Documents")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        # Test different document types for different ages
        test_cases = [
            {"doc_type": "privacy", "age": 10, "desc": "Child privacy policy"},
            {"doc_type": "privacy", "age": 25, "desc": "Adult privacy policy"},
            {"doc_type": "tos", "age": None, "desc": "Terms of Service"},
        ]

        for test in test_cases:
            print(f"\n📄 {test['desc']}")

            request_data = {
                "document_type": test["doc_type"],
                "language": "en",
                "country": "US",
                "format": "html",
            }

            if test["age"]:
                request_data["user_age"] = test["age"]

            try:
                response = await client.post(
                    f"{BASE_URL}/api/v1/compliance/legal/document", json=request_data
                )

                if response.status_code == 200:
                    data = response.json()
                    print(f"  ✅ Document Type: {data['document_type']}")
                    print(f"  Version: {data['version']}")
                    print(f"  Age Appropriate: {'✅' if data['age_appropriate'] else '❌'}")
                    print(
                        f"  Requires Acceptance: {'Yes' if data['requires_acceptance'] else 'No'}"
                    )

                    if data.get("summary_points"):
                        print(f"  📝 Key Points:")
                        for point in data["summary_points"][:2]:
                            print(f"    • {point}")

                    # Check content length
                    if data.get("content"):
                        print(f"  Content Length: {len(data['content'])} characters")
                else:
                    print(f"  ❌ Error: {response.status_code}")

            except Exception as e:
                print(f"  ❌ Connection error: {e}")


async def test_privacy_dashboard():
    """Test privacy dashboard"""
    print("\n" + "=" * 60)
    print("Testing Privacy Dashboard")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/api/v1/compliance/privacy/dashboard/1")

            if response.status_code == 200:
                data = response.json()
                print(f"✅ Privacy Dashboard Retrieved")

                # Compliance status
                if data.get("compliance_status"):
                    print("\n🛡️ Compliance Status:")
                    for standard, status in data["compliance_status"].items():
                        emoji = "✅" if status == "compliant" else "⚠️"
                        print(f"  {emoji} {standard.upper()}: {status}")

                # Age verification
                if data.get("age_verification"):
                    age_data = data["age_verification"]
                    print(f"\n👤 Age Verification:")
                    print(f"  Verified: {'✅' if age_data['verified'] else '❌'}")
                    print(f"  Age Group: {age_data.get('age_group', 'Unknown')}")
                    print(f"  Parental Consent: {'✅' if age_data.get('parental_consent') else '❌'}")

                # Privacy settings
                if data.get("privacy_settings"):
                    print(f"\n🔒 Privacy Settings:")
                    for setting, value in list(data["privacy_settings"].items())[:4]:
                        print(f"  • {setting}: {value}")

                # Available rights
                if data.get("rights_available"):
                    print(f"\n⚖️ Your Rights:")
                    for right in data["rights_available"][:3]:
                        print(f"  • {right}")

            else:
                print(f"❌ Error: {response.status_code} - {response.text[:200]}")

        except Exception as e:
            print(f"❌ Connection error: {e}")


async def main():
    """Run all compliance tests"""
    print("\n" + "⚖️ LEGAL COMPLIANCE API TEST SUITE ⚖️".center(60, "="))
    print(f"Testing against: {BASE_URL}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Test all compliance features
    await test_coppa_age_verification()
    await test_parental_consent()
    await test_childrens_code()
    await test_gdpr_data_requests()
    await test_legal_documents()
    await test_privacy_dashboard()

    print("\n" + "=" * 60)
    print("✅ All compliance tests completed!")
    print(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n📝 Summary of Compliance Features Tested:")
    print("  ⚖️ COPPA - US child privacy protection")
    print("  🇪🇺 Children's Code - EU/UK age-appropriate design")
    print("  🔐 GDPR - Data rights and governance")
    print("  📄 Legal Documents - Age-appropriate content")
    print("  🛡️ Privacy Dashboard - Comprehensive privacy control")
    print("=" * 60)


if __name__ == "__main__":
    # For local testing, make sure the API is running:
    # uvicorn api.main_babyshield:app --host 0.0.0.0 --port 8001
    asyncio.run(main())

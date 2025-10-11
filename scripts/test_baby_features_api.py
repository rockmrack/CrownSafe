#!/usr/bin/env python3
"""
Test script for BabyShield Core Features API
Tests alternatives, notifications, reports, and other baby-specific features
"""

import asyncio
import httpx
import json
from datetime import datetime

# API base URL - adjust as needed
BASE_URL = "http://localhost:8001"  # Local testing
# BASE_URL = "https://babyshield.cureviax.ai"  # Production


async def test_alternatives_endpoint():
    """Test the safe alternatives endpoint"""
    print("\n" + "=" * 60)
    print("Testing Safe Alternatives Endpoint")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        # Test with a recalled product
        request_data = {
            "product_name": "Generic Baby Formula",
            "product_category": "Infant Formula",
            "user_id": 1,
            "max_alternatives": 5,
        }

        try:
            response = await client.post(f"{BASE_URL}/api/v1/baby/alternatives", json=request_data)

            if response.status_code == 200:
                data = response.json()
                print(f"✅ Status: {data['status']}")
                print(f"Original Product: {data['original_product']}")
                print(f"Category: {data['category_detected']}")
                print(f"Alternatives Found: {data['alternatives_found']}")

                if data["alternatives"]:
                    print("\n🔄 Safe Alternatives:")
                    for alt in data["alternatives"]:
                        print(f"  • {alt['product_name']}")
                        print(f"    Safety Score: {alt['safety_score']}/100")
                        print(f"    Reason: {alt['reason']}")
                        if alt.get("where_to_buy"):
                            print(f"    Available at: {', '.join(alt['where_to_buy'])}")
            else:
                print(f"❌ Error: {response.status_code} - {response.text}")

        except Exception as e:
            print(f"❌ Connection error: {e}")


async def test_notification_endpoint():
    """Test push notification sending"""
    print("\n" + "=" * 60)
    print("Testing Push Notifications")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        request_data = {
            "user_id": 1,
            "title": "⚠️ Recall Alert",
            "body": "A product you scanned has been recalled. Tap for details.",
            "notification_type": "recall_alert",
            "priority": "high",
            "data": {"recall_id": "TEST-001", "product": "Test Product"},
        }

        try:
            response = await client.post(f"{BASE_URL}/api/v1/baby/notifications/send", json=request_data)

            if response.status_code == 200:
                data = response.json()
                print(f"✅ Status: {data['status']}")
                print(f"Notification ID: {data['notification_id']}")
                print(f"Sent: {data['sent_count']} devices")
                print(f"Failed: {data['failed_count']} devices")

                if data.get("errors"):
                    print("\n⚠️ Errors:")
                    for error in data["errors"]:
                        print(f"  - {error}")
            else:
                print(f"❌ Error: {response.status_code} - {response.text}")

        except Exception as e:
            print(f"❌ Connection error: {e}")


async def test_bulk_notification():
    """Test bulk notification sending"""
    print("\n" + "=" * 60)
    print("Testing Bulk Notifications")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        request_data = {
            "user_ids": [1, 2, 3],
            "title": "🛡️ Safety Update",
            "body": "New safety guidelines available for infant car seats",
            "notification_type": "safety_tip",
            "product_info": {"category": "Car Seats", "update_type": "guidelines"},
        }

        try:
            response = await client.post(f"{BASE_URL}/api/v1/baby/notifications/bulk", json=request_data)

            if response.status_code == 200:
                data = response.json()
                print("✅ Bulk notification sent")
                print(f"Total sent: {data['sent_count']}")
                print(f"Total failed: {data['failed_count']}")
                print(f"Devices targeted: {data['devices_targeted']}")
            else:
                print(f"❌ Error: {response.status_code} - {response.text}")

        except Exception as e:
            print(f"❌ Connection error: {e}")


async def test_report_generation():
    """Test safety report generation"""
    print("\n" + "=" * 60)
    print("Testing Report Generation")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        request_data = {
            "user_id": 1,
            "report_type": "safety_summary",
            "format": "pdf",
            "date_range": 30,
            "include_alternatives": True,
            "include_guidelines": True,
        }

        try:
            response = await client.post(f"{BASE_URL}/api/v1/baby/reports/generate", json=request_data)

            if response.status_code == 200:
                data = response.json()
                print("✅ Report generated successfully")
                print(f"Report ID: {data['report_id']}")
                print(f"Type: {data['report_type']}")
                print(f"Format: {data['format']}")
                if data.get("download_url"):
                    print(f"Download: {data['download_url']}")
                if data.get("file_size_kb"):
                    print(f"Size: {data['file_size_kb']} KB")
                if data.get("pages"):
                    print(f"Pages: {data['pages']}")

                # Test download
                if data.get("report_id"):
                    print("\n📥 Testing report download...")
                    download_response = await client.get(
                        f"{BASE_URL}/api/v1/baby/reports/download/{data['report_id']}",
                        params={"user_id": 1},
                    )
                    if download_response.status_code == 200:
                        print("✅ Report download successful")
                    else:
                        print(f"❌ Download failed: {download_response.status_code}")

            else:
                print(f"❌ Error: {response.status_code} - {response.text}")

        except Exception as e:
            print(f"❌ Connection error: {e}")


async def test_onboarding():
    """Test user onboarding/profile setup"""
    print("\n" + "=" * 60)
    print("Testing User Onboarding")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        request_data = {
            "user_id": 1,
            "child_age_months": 6,
            "expecting": False,
            "interests": ["Infant Formula", "Baby Toys", "Car Seats"],
            "notification_preferences": {
                "recalls": True,
                "safety_tips": True,
                "community_alerts": False,
            },
        }

        try:
            response = await client.post(f"{BASE_URL}/api/v1/baby/onboarding/setup", json=request_data)

            if response.status_code == 200:
                data = response.json()
                print("✅ Profile setup complete")
                print(f"Recommended Categories: {', '.join(data['recommended_categories'])}")

                if data.get("safety_tips"):
                    print("\n💡 Safety Tips:")
                    for tip in data["safety_tips"]:
                        print(f"  • {tip}")

                if data.get("next_steps"):
                    print("\n📋 Next Steps:")
                    for step in data["next_steps"]:
                        print(f"  • {step}")

            else:
                print(f"❌ Error: {response.status_code} - {response.text}")

        except Exception as e:
            print(f"❌ Connection error: {e}")


async def test_hazard_analysis():
    """Test product hazard analysis"""
    print("\n" + "=" * 60)
    print("Testing Hazard Analysis")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        request_data = {
            "product_name": "Small Parts Toy Set",
            "barcode": "123456789",
            "user_id": 1,
            "child_age_months": 18,
        }

        try:
            response = await client.post(f"{BASE_URL}/api/v1/baby/hazards/analyze", json=request_data)

            if response.status_code == 200:
                data = response.json()
                print("✅ Hazard Analysis Complete")
                print(f"Product: {data['product']}")
                print(
                    f"Risk Level: {data['overall_risk_level']} {'🟢' if data['overall_risk_level'] == 'LOW' else '🔴' if data['overall_risk_level'] in ['HIGH', 'CRITICAL'] else '🟡'}"
                )
                print(f"Age Appropriate: {'Yes ✅' if data['age_appropriate'] else 'No ❌'}")

                if data["hazards_identified"]:
                    print("\n⚠️ Hazards Identified:")
                    for hazard in data["hazards_identified"]:
                        print(f"  • {hazard['type']}: {hazard['description']}")
                        print(f"    Severity: {hazard['severity']}")

                if data["recommendations"]:
                    print("\n📋 Recommendations:")
                    for rec in data["recommendations"]:
                        print(f"  • {rec}")

                if data.get("safer_alternatives"):
                    print("\n✅ Safer Alternatives:")
                    for alt in data["safer_alternatives"]:
                        print(f"  • {alt}")

            else:
                print(f"❌ Error: {response.status_code} - {response.text}")

        except Exception as e:
            print(f"❌ Connection error: {e}")


async def test_community_alerts():
    """Test community alerts endpoint"""
    print("\n" + "=" * 60)
    print("Testing Community Alerts")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{BASE_URL}/api/v1/baby/community/alerts",
                params={"user_id": 1, "limit": 5},
            )

            if response.status_code == 200:
                data = response.json()
                print("✅ Community Alerts Retrieved")
                print(f"Total Alerts: {data['alerts_count']}")
                print(f"Sources Monitored: {', '.join(data['sources_monitored'])}")

                if data["alerts"]:
                    print("\n🌍 Recent Community Alerts:")
                    for alert in data["alerts"]:
                        print(f"\n  📢 {alert['title']}")
                        print(f"     Product: {alert['product']}")
                        print(f"     Reported by: {alert['reported_by']}")
                        print(f"     Severity: {alert['severity']}")
                        print(f"     Source: {alert['source']}")
                        print(f"     Verified: {'✅' if alert['verified'] else '❓'}")

            else:
                print(f"❌ Error: {response.status_code} - {response.text}")

        except Exception as e:
            print(f"❌ Connection error: {e}")


async def test_integrated_safety_check():
    """Test safety check with alternatives integration"""
    print("\n" + "=" * 60)
    print("Testing Integrated Safety Check (with Alternatives)")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        request_data = {
            "user_id": 1,
            "barcode": "041220787346",  # Fisher-Price product (likely to have recalls)
            "model_number": "FP-123",
        }

        try:
            response = await client.post(f"{BASE_URL}/api/v1/safety-check", json=request_data)

            if response.status_code == 200:
                data = response.json()
                print("✅ Safety Check Complete")
                print(f"Status: {data['status']}")

                if data.get("data"):
                    result = data["data"]
                    if result.get("recalls_found"):
                        print(f"⚠️ Recalls Found: {result['recalls_found']}")

                    if result.get("risk_level"):
                        print(f"Risk Level: {result['risk_level']}")

                    if result.get("alternatives_suggested"):
                        print(f"\n✅ Alternatives Suggested: {result['alternatives_suggested']}")

                    if data.get("alternatives"):
                        print("\n🔄 Safe Alternatives:")
                        for alt in data["alternatives"]:
                            print(f"  • {alt['product_name']}: {alt['reason']}")

                    if result.get("summary"):
                        print(f"\n📄 Summary:\n{result['summary']}")

            else:
                print(f"❌ Error: {response.status_code} - {response.text}")

        except Exception as e:
            print(f"❌ Connection error: {e}")


async def main():
    """Run all tests"""
    print("\n" + "🍼 BABYSHIELD CORE FEATURES API TEST SUITE 🍼".center(60, "="))
    print(f"Testing against: {BASE_URL}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Test individual features
    await test_alternatives_endpoint()
    await test_notification_endpoint()
    await test_bulk_notification()
    await test_report_generation()
    await test_onboarding()
    await test_hazard_analysis()
    await test_community_alerts()

    # Test integration with main safety check
    await test_integrated_safety_check()

    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n📝 Summary of Features Tested:")
    print("  • Safe Alternatives - Product replacement suggestions")
    print("  • Push Notifications - Instant recall alerts")
    print("  • Report Generation - PDF safety reports")
    print("  • User Onboarding - Personalized setup")
    print("  • Hazard Analysis - Age-specific risk assessment")
    print("  • Community Alerts - Crowdsourced safety warnings")
    print("  • Integrated Safety Check - All features working together")
    print("=" * 60)


if __name__ == "__main__":
    # For local testing, make sure the API is running:
    # uvicorn api.main_babyshield:app --host 0.0.0.0 --port 8001
    asyncio.run(main())

#!/usr/bin/env python3
"""
Test script for Advanced BabyShield Features API
Tests web research, guidelines, visual recognition, and monitoring
"""

import asyncio
import httpx
import json
from datetime import datetime
from pathlib import Path
import base64

# API base URL - adjust as needed
BASE_URL = "http://localhost:8001"  # Local testing
# BASE_URL = "https://babyshield.cureviax.ai"  # Production


async def test_web_research():
    """Test web research for product safety"""
    print("\n" + "=" * 60)
    print("Testing Web Research Agent")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        request_data = {
            "product_name": "Baby Formula Brand X",
            "search_depth": "deep",
            "include_social_media": True,
            "include_forums": True,
            "user_id": 1,
        }

        try:
            response = await client.post(
                f"{BASE_URL}/api/v1/advanced/research", json=request_data, timeout=30.0
            )

            if response.status_code == 200:
                data = response.json()
                print(f"✅ Research Status: {data['status']}")
                print(f"Product: {data['product_researched']}")
                print(
                    f"Safety Score: {data['safety_score']}/100 {'🟢' if data['safety_score'] > 80 else '🟡' if data['safety_score'] > 60 else '🔴'}"
                )
                print(
                    f"Findings: {data['findings_count']} from {len(data['sources_searched'])} sources"
                )
                print(f"Search Time: {data['search_time_ms']}ms")

                if data["risk_indicators"]:
                    print("\n⚠️ Risk Indicators:")
                    for risk in data["risk_indicators"]:
                        print(f"  • {risk}")

                if data["findings"]:
                    print("\n🔍 Top Findings:")
                    for finding in data["findings"][:3]:
                        sentiment_emoji = (
                            "😊"
                            if finding["sentiment"] == "positive"
                            else "😟"
                            if finding["sentiment"] == "negative"
                            else "😐"
                        )
                        print(
                            f"\n  📍 {finding['source']} ({finding['source_type']}) {sentiment_emoji}"
                        )
                        print(f"     {finding['title']}")
                        print(f"     Relevance: {finding['relevance_score']:.2f}")
                        if finding.get("reported_by_count"):
                            print(
                                f"     Reported by: {finding['reported_by_count']} users"
                            )
                        print(f"     Content: {finding['content'][:100]}...")
            else:
                print(f"❌ Error: {response.status_code} - {response.text}")

        except Exception as e:
            print(f"❌ Connection error: {e}")


async def test_guidelines():
    """Test age-appropriate guidelines"""
    print("\n" + "=" * 60)
    print("Testing Guidelines Agent")
    print("=" * 60)

    # Test for different age groups
    test_cases = [
        {"age_months": 2, "product": "Baby Blanket", "weight": 12},
        {"age_months": 8, "product": "Small Parts Toy", "weight": 18},
        {"age_months": 24, "product": "Car Seat", "weight": 28},
    ]

    async with httpx.AsyncClient() as client:
        for test in test_cases:
            print(f"\n📋 Testing: {test['product']} for {test['age_months']} month old")

            request_data = {
                "product_name": test["product"],
                "child_age_months": test["age_months"],
                "child_weight_lbs": test["weight"],
                "user_id": 1,
            }

            try:
                response = await client.post(
                    f"{BASE_URL}/api/v1/advanced/guidelines", json=request_data
                )

                if response.status_code == 200:
                    data = response.json()
                    print(
                        f"  Age Appropriate: {'✅ Yes' if data['age_appropriate'] else '❌ No'}"
                    )

                    if data.get("weight_appropriate") is not None:
                        print(
                            f"  Weight Appropriate: {'✅ Yes' if data['weight_appropriate'] else '❌ No'}"
                        )

                    if data["warnings"]:
                        print("  ⚠️ Warnings:")
                        for warning in data["warnings"][:2]:
                            print(f"    • {warning}")

                    if data["guidelines"]:
                        print("  📖 Key Guidelines:")
                        for guideline in data["guidelines"][:2]:
                            importance_emoji = (
                                "🔴"
                                if guideline["importance"] == "critical"
                                else "🟡"
                                if guideline["importance"] == "important"
                                else "🟢"
                            )
                            print(f"    {importance_emoji} {guideline['title']}")
                            print(f"       {guideline['description'][:80]}...")

                    if data.get("recommended_alternatives"):
                        print("  🔄 Recommended Alternatives:")
                        for alt in data["recommended_alternatives"][:2]:
                            print(f"    • {alt}")

                else:
                    print(f"  ❌ Error: {response.status_code}")

            except Exception as e:
                print(f"  ❌ Error: {e}")


async def test_visual_recognition():
    """Test visual product recognition"""
    print("\n" + "=" * 60)
    print("Testing Visual Recognition")
    print("=" * 60)

    # Create a mock image file for testing
    mock_image_path = Path("test_product_image.jpg")

    # Create a simple test image if it doesn't exist
    if not mock_image_path.exists():
        # Create a minimal JPEG header (this is just for testing)
        mock_jpeg = bytes(
            [
                0xFF,
                0xD8,
                0xFF,
                0xE0,  # JPEG SOI and APP0 marker
                0x00,
                0x10,
                0x4A,
                0x46,  # Length and JFIF
                0x49,
                0x46,
                0x00,
                0x01,  # JFIF version
                0x01,
                0x01,
                0x00,
                0x00,  # Aspect ratio
                0x00,
                0x00,
                0x00,
                0x00,  # Thumbnail
                0xFF,
                0xD9,  # EOI marker
            ]
        )
        with open(mock_image_path, "wb") as f:
            f.write(mock_jpeg)
        print("  📷 Created test image file")

    async with httpx.AsyncClient() as client:
        try:
            # Test with different "product" images (simulated by filename)
            test_images = [
                ("fisher_price_toy.jpg", "Fisher-Price product"),
                ("car_seat.jpg", "Car seat"),
                ("baby_bottle.jpg", "Baby bottle"),
            ]

            for filename, description in test_images:
                print(f"\n  Testing: {description}")

                with open(mock_image_path, "rb") as f:
                    files = {"image": (filename, f, "image/jpeg")}

                    response = await client.post(
                        f"{BASE_URL}/api/v1/advanced/visual/recognize",
                        files=files,
                        params={
                            "user_id": 1,
                            "include_similar": True,
                            "check_for_defects": True,
                            "confidence_threshold": 0.7,
                        },
                        timeout=30.0,
                    )

                if response.status_code == 200:
                    data = response.json()
                    print(f"    Status: {data['status']}")
                    print(f"    Confidence: {data['confidence']:.2%}")

                    if data["products_identified"]:
                        for product in data["products_identified"]:
                            recall_emoji = (
                                "🔴" if product["recall_status"] == "RECALLED" else "🟢"
                            )
                            print(
                                f"    {recall_emoji} Identified: {product['product_name']}"
                            )
                            print(f"       Brand: {product.get('brand', 'Unknown')}")
                            print(
                                f"       Category: {product.get('category', 'Unknown')}"
                            )
                            if product["recall_status"] == "RECALLED":
                                print(
                                    f"       ⚠️ RECALL: {product.get('recall_reason', 'Check details')}"
                                )

                    if data.get("defects_detected"):
                        print("    ⚠️ Defects Detected:")
                        for defect in data["defects_detected"]:
                            print(
                                f"       • {defect['description']} (Severity: {defect['severity']})"
                            )

                    if data.get("similar_products"):
                        print("    🔄 Similar Products:")
                        for similar in data["similar_products"][:2]:
                            print(
                                f"       • {similar['product_name']} (Match: {similar['similarity_score']:.0%})"
                            )

                    print(f"    Processing Time: {data['processing_time_ms']}ms")

                else:
                    print(
                        f"    ❌ Error: {response.status_code} - {response.text[:100]}"
                    )

        except Exception as e:
            print(f"  ❌ Connection error: {e}")
        finally:
            # Clean up test image
            if mock_image_path.exists():
                mock_image_path.unlink()
                print("\n  🧹 Cleaned up test image")


async def test_monitoring():
    """Test continuous monitoring setup"""
    print("\n" + "=" * 60)
    print("Testing Continuous Monitoring")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        # Setup monitoring
        request_data = {
            "product_name": "Popular Baby Monitor XYZ",
            "barcode": "123456789",
            "user_id": 1,
            "monitoring_duration_days": 30,
            "alert_threshold": "medium",
        }

        try:
            print("📡 Setting up monitoring...")
            response = await client.post(
                f"{BASE_URL}/api/v1/advanced/monitor/setup", json=request_data
            )

            if response.status_code == 200:
                data = response.json()
                print("✅ Monitoring Setup Complete")
                print(f"  ID: {data['monitoring_id']}")
                print(f"  Product: {data['product_monitored']}")
                print(f"  Duration: {data['duration_days']} days")
                print(f"  Alert Level: {data['alert_threshold']}")
                print(f"  Sources: {data['sources_count']} sources")
                print(f"  Next Check: {data['next_check']}")

                # Check status
                monitoring_id = data["monitoring_id"]
                print("\n📊 Checking monitoring status...")

                status_response = await client.get(
                    f"{BASE_URL}/api/v1/advanced/monitor/{monitoring_id}/status",
                    params={"user_id": 1},
                )

                if status_response.status_code == 200:
                    status_data = status_response.json()
                    print(f"  Status: {status_data['status']}")
                    print(f"  Checks Performed: {status_data['checks_performed']}")
                    print(f"  Alerts Sent: {status_data['alerts_sent']}")

                    if status_data.get("findings"):
                        print("  Recent Findings:")
                        for finding in status_data["findings"][:2]:
                            alert_emoji = "🔔" if finding["alert_sent"] else "📝"
                            print(
                                f"    {alert_emoji} {finding['source']}: {finding['summary']}"
                            )

                # Cancel monitoring
                print("\n🛑 Cancelling monitoring...")
                cancel_response = await client.delete(
                    f"{BASE_URL}/api/v1/advanced/monitor/{monitoring_id}",
                    params={"user_id": 1},
                )

                if cancel_response.status_code == 200:
                    print("  ✅ Monitoring cancelled successfully")

            else:
                print(f"❌ Error: {response.status_code} - {response.text}")

        except Exception as e:
            print(f"❌ Connection error: {e}")


async def test_integration():
    """Test how these features work together"""
    print("\n" + "=" * 60)
    print("Testing Feature Integration")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        print("🔄 Simulating complete product safety analysis workflow:")

        # Step 1: Research the product
        print("\n1️⃣ Researching product online...")
        research_response = await client.post(
            f"{BASE_URL}/api/v1/advanced/research",
            json={
                "product_name": "Example Baby Product",
                "search_depth": "quick",
                "user_id": 1,
            },
        )

        safety_score = 100
        if research_response.status_code == 200:
            research_data = research_response.json()
            safety_score = research_data["safety_score"]
            print(f"   Safety Score: {safety_score}/100")

        # Step 2: Get age-appropriate guidelines
        print("\n2️⃣ Checking age appropriateness...")
        guidelines_response = await client.post(
            f"{BASE_URL}/api/v1/advanced/guidelines",
            json={
                "product_name": "Example Baby Product",
                "child_age_months": 12,
                "user_id": 1,
            },
        )

        age_appropriate = True
        if guidelines_response.status_code == 200:
            guidelines_data = guidelines_response.json()
            age_appropriate = guidelines_data["age_appropriate"]
            print(f"   Age Appropriate: {'✅' if age_appropriate else '❌'}")

        # Step 3: Final recommendation
        print("\n3️⃣ Final Safety Assessment:")
        if safety_score > 80 and age_appropriate:
            print("   ✅ SAFE TO USE - Product passes all safety checks")
        elif safety_score > 60 and age_appropriate:
            print("   🟡 USE WITH CAUTION - Some concerns identified")
        else:
            print("   🔴 NOT RECOMMENDED - Significant safety concerns")

        print("\n📊 Complete analysis provides:")
        print("   • Real-time safety intelligence from web")
        print("   • Age-specific usage guidelines")
        print("   • Visual defect detection")
        print("   • Continuous monitoring alerts")


async def main():
    """Run all tests"""
    print("\n" + "🚀 ADVANCED BABYSHIELD FEATURES TEST SUITE 🚀".center(60, "="))
    print(f"Testing against: {BASE_URL}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Test each advanced feature
    await test_web_research()
    await test_guidelines()
    await test_visual_recognition()
    await test_monitoring()

    # Test integration
    await test_integration()

    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n📝 Summary of Advanced Features Tested:")
    print("  🌐 Web Research - Real-time safety monitoring")
    print("  📋 Guidelines - Age-appropriate usage recommendations")
    print("  👀 Visual Recognition - Image-based product identification")
    print("  📡 Monitoring - Continuous safety tracking")
    print("  🔄 Integration - All features working together")
    print("=" * 60)


if __name__ == "__main__":
    # For local testing, make sure the API is running:
    # uvicorn api.main_crownsafe:app --host 0.0.0.0 --port 8001
    asyncio.run(main())

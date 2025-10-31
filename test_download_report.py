"""
Test Download Report Functionality
Tests the complete report generation and download workflow
"""

import json
from datetime import datetime

import requests

BASE_URL = "http://localhost:8001"  # Change to production URL if testing production
# BASE_URL = "https://babyshield.cureviax.ai"


def test_download_report_workflow():
    """
    Test complete report download workflow:
    1. Generate a report
    2. Get the download URL
    3. Download the PDF
    """

    print("=" * 80)
    print("🧪 Testing Download Report Functionality")
    print("=" * 80)

    # Test 1: Generate a Product Safety Report
    print("\n📝 Test 1: Generate Product Safety Report")
    print("-" * 80)

    payload = {
        "user_id": 12345,  # Test user
        "report_type": "product_safety",
        "format": "pdf",
        "date_range": 90,
        "product_name": "Baby Einstein Activity Jumper",
        "barcode": "0074451090361",
        "model_number": "90361",
        "lot_or_serial": None,
    }

    try:
        response = requests.post(f"{BASE_URL}/api/v1/baby/reports/generate", json=payload, timeout=30)

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("✅ Report generated successfully!")
            print(f"   Report ID: {data.get('report_id')}")
            print(f"   Report Type: {data.get('report_type')}")
            print(f"   Download URL: {data.get('download_url')}")
            print(f"   File Size: {data.get('file_size_kb')} KB")
            print(f"   Generated At: {data.get('generated_at')}")

            report_id = data.get("report_id")
            download_url = data.get("download_url")

            # Test 2: Download the report using the provided URL
            if download_url and report_id:
                print(f"\n📥 Test 2: Download Report (ID: {report_id})")
                print("-" * 80)

                # Handle both full URL and relative path
                if download_url.startswith("http"):
                    full_download_url = download_url
                else:
                    full_download_url = f"{BASE_URL}{download_url}"

                print(f"Download URL: {full_download_url}")

                try:
                    download_response = requests.get(full_download_url, timeout=30)

                    print(f"Download Status Code: {download_response.status_code}")

                    if download_response.status_code == 200:
                        content_type = download_response.headers.get("Content-Type", "")
                        content_length = len(download_response.content)

                        print("✅ Report downloaded successfully!")
                        print(f"   Content-Type: {content_type}")
                        print(f"   File Size: {content_length} bytes ({content_length / 1024:.2f} KB)")

                        if "application/pdf" in content_type:
                            print("   ✅ Correct content type (PDF)")

                            # Save to file for inspection
                            filename = f"test_report_{report_id}.pdf"
                            with open(filename, "wb") as f:
                                f.write(download_response.content)
                            print(f"   💾 Saved to: {filename}")

                            # Verify PDF header
                            if download_response.content[:4] == b"%PDF":
                                print("   ✅ Valid PDF file (header check)")
                            else:
                                print("   ⚠️ Warning: File doesn't have PDF header")
                        else:
                            print("   ⚠️ Warning: Content type is not PDF")
                            print(f"   Response: {download_response.text[:500]}")
                    elif download_response.status_code == 401:
                        print("❌ Unauthorized - Authentication required")
                        print("   Note: This endpoint requires user authentication")
                    elif download_response.status_code == 403:
                        print("❌ Forbidden - User doesn't own this report")
                    elif download_response.status_code == 404:
                        print("❌ Report file not found on server")
                        print("   The report may have been generated but file is missing")
                    else:
                        print(f"❌ Download failed with status {download_response.status_code}")
                        print(f"   Response: {download_response.text[:500]}")

                except requests.exceptions.ConnectionError:
                    print(f"❌ Connection error - Is the API running at {BASE_URL}?")
                except requests.exceptions.Timeout:
                    print("❌ Download timed out")
                except Exception as e:
                    print(f"❌ Download error: {e}")
            else:
                print("⚠️ No download URL provided in response")

        elif response.status_code == 503:
            print("❌ Service unavailable - Report generation service not available")
            print("   Check if report_agent is initialized")
        else:
            print("❌ Report generation failed")
            print(f"Response: {json.dumps(response.json(), indent=2)}")

    except requests.exceptions.ConnectionError:
        print(f"❌ Connection error - Is the API running at {BASE_URL}?")
        print("💡 Start the API with: uvicorn api.main_crownsafe:app --reload --port 8001")
    except requests.exceptions.Timeout:
        print("❌ Request timed out")
    except Exception as e:
        print(f"❌ Error: {e}")

    # Test 3: Generate Safety Summary Report
    print("\n📝 Test 3: Generate Safety Summary Report")
    print("-" * 80)

    payload = {
        "user_id": 12345,
        "report_type": "safety_summary",
        "format": "pdf",
        "date_range": 30,
    }

    try:
        response = requests.post(f"{BASE_URL}/api/v1/baby/reports/generate", json=payload, timeout=30)

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("✅ Safety summary generated!")
            print(f"   Report ID: {data.get('report_id')}")
            print(f"   Download URL: {data.get('download_url')}")
        else:
            print(f"⚠️ Failed with status {response.status_code}")

    except Exception as e:
        print(f"⚠️ Error: {e}")

    # Test 4: Generate Nursery Quarterly Report
    print("\n📝 Test 4: Generate Nursery Quarterly Report")
    print("-" * 80)

    payload = {
        "user_id": 12345,
        "report_type": "nursery_quarterly",
        "format": "pdf",
        "date_range": 90,
        "products": ["Baby crib", "Stroller", "Baby monitor", "High chair", "Car seat"],
    }

    try:
        response = requests.post(f"{BASE_URL}/api/v1/baby/reports/generate", json=payload, timeout=30)

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("✅ Nursery quarterly report generated!")
            print(f"   Report ID: {data.get('report_id')}")
            print(f"   Download URL: {data.get('download_url')}")
        else:
            print(f"⚠️ Failed with status {response.status_code}")

    except Exception as e:
        print(f"⚠️ Error: {e}")

    print("\n" + "=" * 80)
    print("✅ Download Report Testing Complete!")
    print("=" * 80)


if __name__ == "__main__":
    test_download_report_workflow()

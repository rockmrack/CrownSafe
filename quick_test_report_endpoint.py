"""Quick verification that Report Unsafe Product endpoints work
"""

import json

import requests

BASE_URL = "http://localhost:8001"  # Change to production when deployed


def test_report_unsafe_product():
    """Test creating an unsafe product report"""
    print("\n🧪 Testing POST /api/v1/report-unsafe-product...")

    payload = {
        "user_id": 99999,  # Test user
        "product_name": "Test Dangerous Crib",
        "hazard_description": "This is a test report to verify the endpoint works correctly",
        "barcode": "9999999999999",
        "severity": "MEDIUM",
        "category": "Cribs",
    }

    try:
        response = requests.post(f"{BASE_URL}/api/v1/report-unsafe-product", json=payload, timeout=10)

        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

        if response.status_code == 201:
            print("✅ Report created successfully!")
            data = response.json()
            report_id = data.get("report_id")
            print(f"Report ID: {report_id}")

            # Test retrieving the report
            print("\n🧪 Testing GET /api/v1/user-reports/99999...")
            get_response = requests.get(f"{BASE_URL}/api/v1/user-reports/99999", timeout=10)

            print(f"Status Code: {get_response.status_code}")
            print(f"Response: {json.dumps(get_response.json(), indent=2)}")

            if get_response.status_code == 200:
                print("✅ Successfully retrieved user reports!")

                reports_data = get_response.json()
                if reports_data.get("total", 0) > 0:
                    print(f"📊 Found {reports_data['total']} report(s)")
                else:
                    print("⚠️ No reports found (might be on a different database)")
            else:
                print(f"❌ Failed to retrieve reports: {get_response.status_code}")
        else:
            print(f"❌ Failed to create report: {response.status_code}")
            print(f"Error: {response.json()}")

    except requests.exceptions.ConnectionError:
        print("❌ Connection error - is the API running?")
        print("💡 Start the API with: uvicorn api.main_crownsafe:app --reload --port 8001")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("🛡️ BabyShield - Report Unsafe Product Endpoint Verification")
    print("=" * 60)
    test_report_unsafe_product()
    print("\n" + "=" * 60)
    print("✅ Verification Complete!")
    print("=" * 60)

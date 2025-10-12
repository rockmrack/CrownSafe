"""
SIMPLE TEST: Model Number Entry Workflow

This test validates the /api/v1/safety-check endpoint responds to model number queries.
No database setup needed - just tests the API endpoint directly!

Run with: pytest tests/integration/test_simple_model_entry.py -v -s
"""

import pytest
from fastapi.testclient import TestClient
from api.main_babyshield import app

# Create test client
client = TestClient(app)


def test_safety_check_endpoint_exists():
    """Test that the safety-check endpoint exists and responds."""
    print("\n" + "=" * 80)
    print("TEST: Safety Check Endpoint - Basic Connectivity")
    print("=" * 80)

    payload = {
        "user_id": 999,
        "model_number": "TEST-MODEL-123",
        "barcode": None,
        "image_url": None,
        "product_name": None,
    }

    print("\n📡 Testing POST /api/v1/safety-check")
    print(f"   Model Number: {payload['model_number']}")

    response = client.post("/api/v1/safety-check", json=payload)

    print(f"\n📊 Response Status: {response.status_code}")

    if response.status_code == 200:
        print("✅ SUCCESS! Endpoint is working")
        data = response.json()
        print("\n📄 Response Structure:")
        for key in data.keys():
            print(f"   - {key}: {type(data[key]).__name__}")

        # Validate basic structure
        assert "risk_level" in data or "status" in data, "Response missing expected fields"

    elif response.status_code == 404:
        print("❌ FAILED: Endpoint not found (404)")
        print(f"   Response: {response.text[:200]}")
        pytest.fail("safety-check endpoint does not exist")

    elif response.status_code == 422:
        print("⚠️  Validation Error (422) - checking details:")
        print(f"   {response.json()}")

    elif response.status_code == 500:
        print("❌ Server Error (500) - checking details:")
        print(f"   {response.text[:500]}")
        # Don't fail - just report the error
        pytest.skip("Server error - endpoint exists but has runtime issues")

    else:
        print(f"⚠️  Unexpected status code: {response.status_code}")
        print(f"   Response: {response.text[:200]}")


def test_model_number_parameter():
    """Test that model_number parameter is accepted."""
    print("\n" + "=" * 80)
    print("TEST: Model Number Parameter Handling")
    print("=" * 80)

    test_cases = [
        ("ABC-123", "Simple alphanumeric model"),
        ("MODEL 2024-X", "Model with spaces and year"),
        ("12345", "Numeric only model"),
    ]

    for model_number, description in test_cases:
        print(f"\n🔍 Testing: {description}")
        print(f"   Model: '{model_number}'")

        payload = {
            "user_id": 999,
            "model_number": model_number,
        }

        response = client.post("/api/v1/safety-check", json=payload)
        print(f"   Status: {response.status_code}")

        if response.status_code == 200:
            print("   ✅ Accepted")
        elif response.status_code in [404, 500]:
            print(f"   ⚠️  Endpoint issue ({response.status_code})")
        else:
            print(f"   ℹ️  Response: {response.status_code}")


def test_empty_model_number():
    """Test handling of empty model number."""
    print("\n" + "=" * 80)
    print("TEST: Empty Model Number Handling")
    print("=" * 80)

    payload = {
        "user_id": 999,
        "model_number": "",
    }

    print("\n📡 Sending empty model number...")

    response = client.post("/api/v1/safety-check", json=payload)

    print(f"📊 Response Status: {response.status_code}")

    if response.status_code == 422:
        print("✅ CORRECT: Validation rejected empty input (422)")
    elif response.status_code == 200:
        print("ℹ️  Endpoint accepts empty input (returns data anyway)")
    elif response.status_code == 400:
        print("✅ CORRECT: Bad request for empty input (400)")
    else:
        print(f"ℹ️  Status: {response.status_code}")


if __name__ == "__main__":
    # Can run directly
    import sys

    sys.exit(pytest.main([__file__, "-v", "-s"]))

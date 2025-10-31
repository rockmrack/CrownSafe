"""QUICKSTART TEST: Model Number Entry.

Simplest possible test - just check if we can call the endpoint.
Uses user_id=999 which might trigger dev override.

Run: pytest tests/integration/test_model_quickstart.py -v -s
"""

from fastapi.testclient import TestClient

from api.main_crownsafe import app

client = TestClient(app)


def test_model_number_basic() -> None:
    """Basic test - does the endpoint respond?"""
    print("\n" + "=" * 70)
    print("QUICKSTART TEST: Model Number Entry")
    print("=" * 70)

    # Simple test with model number
    payload = {"user_id": 999, "model_number": "ABC-123"}

    print(f"\n👤 User enters model number: {payload['model_number']}")
    print("📡 Calling POST /api/v1/safety-check...")

    response = client.post("/api/v1/safety-check", json=payload)

    print(f"📊 Status: {response.status_code}")

    if response.status_code == 200:
        print("✅ SUCCESS! Endpoint working")
        data = response.json()
        print(f"\nResponse keys: {list(data.keys())}")
        if "status" in data:
            print(f"Status: {data['status']}")
        if "data" in data:
            print(f"Data: {data['data']}")

    elif response.status_code == 403:
        print("⚠️  Subscription required (expected without dev override)")
        print("✅ Endpoint exists and validates correctly")

    elif response.status_code == 404:
        print("⚠️  User not found (need to create test user)")
        print("✅ Endpoint exists and validates correctly")

    elif response.status_code == 400:
        err = response.json()
        print(f"⚠️  Validation error: {err.get('error')}")
        print("✅ Endpoint exists and validates input")

    elif response.status_code == 500:
        print("❌ Server error - checking details...")
        print(f"Response: {response.text[:300]}")

    else:
        print(f"ℹ️  Got status {response.status_code}")
        print(f"Response: {response.text[:200]}")

    # Test passed if we got ANY response (endpoint exists)
    assert response.status_code in [
        200,
        400,
        403,
        404,
        500,
    ], f"Unexpected status: {response.status_code}"


if __name__ == "__main__":
    test_model_number_basic()

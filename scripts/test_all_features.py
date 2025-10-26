#!/usr/bin/env python3
"""
Master test script that runs all BabyShield API tests
Tests all implemented features to ensure everything is working
"""

import asyncio
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


def print_section(title):
    """Print a formatted section header"""
    print("\n" + "=" * 70)
    print(f"🚀 {title}".center(70))
    print("=" * 70 + "\n")


def check_api_running():
    """Check if the API server is running"""
    import httpx

    try:
        response = httpx.get("http://localhost:8001/health", timeout=2.0)
        return response.status_code == 200
    except:
        return False


def start_api_server():
    """Start the API server in the background"""
    print("Starting BabyShield API server...")
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "api.main_crownsafe:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8001",
    ]
    process = subprocess.Popen(
        cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

    # Wait for server to start
    for i in range(10):
        time.sleep(2)
        if check_api_running():
            print("✅ API server is running on http://localhost:8001")
            return process
        print(f"  Waiting for server to start... ({i + 1}/10)")

    print("❌ Failed to start API server")
    process.terminate()
    return None


async def run_test_script(script_name, description):
    """Run a single test script"""
    print(f"\n{'=' * 60}")
    print(f"Running: {description}")
    print(f"Script: {script_name}")
    print("=" * 60)

    script_path = Path(__file__).parent / script_name

    if not script_path.exists():
        print(f"❌ Test script not found: {script_path}")
        return False

    try:
        # Run the test script
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=60,
        )

        # Print output
        if result.stdout:
            print(result.stdout)

        if result.stderr and "error" in result.stderr.lower():
            print("⚠️ Errors/Warnings:")
            print(result.stderr[:500])

        if result.returncode == 0:
            print(f"✅ {description} - PASSED")
            return True
        else:
            print(f"❌ {description} - FAILED (exit code: {result.returncode})")
            return False

    except subprocess.TimeoutExpired:
        print(f"⏱️ {description} - TIMEOUT (exceeded 60 seconds)")
        return False
    except Exception as e:
        print(f"❌ {description} - ERROR: {e}")
        return False


async def main():
    """Run all tests"""
    print("\n" + "🎯 BABYSHIELD COMPLETE TEST SUITE 🎯".center(70, "="))
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # Check if API is running
    print_section("Checking API Server")
    api_process = None

    if not check_api_running():
        print("⚠️ API server not running. Attempting to start...")
        api_process = start_api_server()
        if not api_process:
            print("❌ Cannot run tests without API server")
            print("Please start the server manually with:")
            print("  uvicorn api.main_crownsafe:app --host 0.0.0.0 --port 8001")
            return
    else:
        print("✅ API server is already running")

    # List of all test scripts to run
    test_scripts = [
        ("test_premium_features_api.py", "Premium Features (Pregnancy & Allergy)"),
        (
            "test_baby_features_api.py",
            "Baby Safety Features (Alternatives, Notifications, Reports)",
        ),
        (
            "test_advanced_features_api.py",
            "Advanced Features (Web Research, Guidelines, Visual)",
        ),
        (
            "test_compliance_endpoints.py",
            "Legal Compliance (COPPA, GDPR, Children's Code)",
        ),
    ]

    # Run each test script
    results = {}
    for script, description in test_scripts:
        success = await run_test_script(script, description)
        results[description] = success
        await asyncio.sleep(1)  # Brief pause between tests

    # Print summary
    print_section("TEST RESULTS SUMMARY")

    total_tests = len(results)
    passed_tests = sum(1 for success in results.values() if success)
    failed_tests = total_tests - passed_tests

    print("📊 Test Results:")
    for test_name, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"  {status} - {test_name}")

    print("\n📈 Statistics:")
    print(f"  Total Tests: {total_tests}")
    print(f"  Passed: {passed_tests}")
    print(f"  Failed: {failed_tests}")
    print(f"  Success Rate: {(passed_tests / total_tests) * 100:.1f}%")

    print(
        f"\n🏁 Test suite completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    # Cleanup
    if api_process:
        print("\n🛑 Stopping API server...")
        api_process.terminate()
        api_process.wait(timeout=5)
        print("✅ API server stopped")

    # Final status
    if failed_tests == 0:
        print("\n" + "🎉 ALL TESTS PASSED! 🎉".center(70, "="))
        print("The BabyShield API is fully functional and ready for deployment!")
    else:
        print("\n" + "⚠️ SOME TESTS FAILED ⚠️".center(70, "="))
        print("Please review the failed tests and fix any issues before deployment.")

    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())

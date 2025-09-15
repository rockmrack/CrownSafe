#!/usr/bin/env python3
"""
Run local tests with proper database configuration
Sets environment variables for local testing
"""

import os
import sys
import time
import subprocess
import asyncio
from pathlib import Path

def setup_local_environment():
    """Set up environment variables for local testing"""
    print("🔧 Setting up local test environment...")
    
    # Use SQLite for local testing
    os.environ["DATABASE_URL"] = "sqlite:///./babyshield_test.db"
    os.environ["TEST_MODE"] = "true"
    os.environ["REDIS_URL"] = "redis://localhost:6379/0"
    os.environ["ENABLE_CACHE"] = "false"
    os.environ["ENABLE_BACKGROUND_TASKS"] = "false"
    os.environ["SECRET_KEY"] = "local-test-secret-key"
    os.environ["JWT_SECRET_KEY"] = "local-jwt-secret-key"
    
    print("✅ Environment variables set for local testing")
    print(f"  DATABASE_URL: {os.environ['DATABASE_URL']}")
    print(f"  TEST_MODE: {os.environ['TEST_MODE']}")

def start_api_server():
    """Start the API server in the background"""
    print("\n🚀 Starting API server...")
    
    # Start the server with the local environment
    cmd = [sys.executable, "-m", "uvicorn", "api.main_babyshield:app", 
           "--host", "0.0.0.0", "--port", "8001", "--reload"]
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        universal_newlines=True
    )
    
    # Wait for server to start
    import httpx
    for i in range(15):
        time.sleep(2)
        try:
            response = httpx.get("http://localhost:8001/health", timeout=2.0)
            if response.status_code == 200:
                print("✅ API server is running on http://localhost:8001")
                return process
        except:
            pass
        print(f"  Waiting for server to start... ({i+1}/15)")
    
    print("❌ Failed to start API server")
    process.terminate()
    return None

async def run_test(script_name, description):
    """Run a single test script"""
    print(f"\n{'='*60}")
    print(f"🧪 {description}")
    print(f"Script: {script_name}")
    print('='*60)
    
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
            timeout=60
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
    """Main test runner"""
    print("\n" + "🎯 BABYSHIELD LOCAL TEST SUITE 🎯".center(70, "="))
    print("Running tests with local SQLite database")
    print("="*70)
    
    # Setup environment
    setup_local_environment()
    
    # Start API server
    api_process = start_api_server()
    if not api_process:
        print("❌ Cannot run tests without API server")
        return
    
    # List of test scripts to run
    test_scripts = [
        ("test_premium_features_api.py", "Premium Features (Pregnancy & Allergy)"),
        ("test_baby_features_api.py", "Baby Safety Features (Alternatives, Notifications, Reports)"),
        ("test_advanced_features_api.py", "Advanced Features (Web Research, Guidelines, Visual)"),
        ("test_compliance_endpoints.py", "Legal Compliance (COPPA, GDPR, Children's Code)")
    ]
    
    # Run each test
    results = {}
    for script, description in test_scripts:
        success = await run_test(script, description)
        results[description] = success
        await asyncio.sleep(1)
    
    # Print summary
    print("\n" + "="*70)
    print("📊 TEST RESULTS SUMMARY")
    print("="*70)
    
    total_tests = len(results)
    passed_tests = sum(1 for success in results.values() if success)
    failed_tests = total_tests - passed_tests
    
    for test_name, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status} - {test_name}")
    
    print(f"\n📈 Statistics:")
    print(f"  Total Tests: {total_tests}")
    print(f"  Passed: {passed_tests}")
    print(f"  Failed: {failed_tests}")
    print(f"  Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    
    # Cleanup
    print("\n🛑 Stopping API server...")
    api_process.terminate()
    try:
        api_process.wait(timeout=5)
        print("✅ API server stopped")
    except subprocess.TimeoutExpired:
        api_process.kill()
        print("⚠️ API server force killed")
    
    # Final status
    if failed_tests == 0:
        print("\n" + "🎉 ALL TESTS PASSED! 🎉".center(70, "="))
        print("The BabyShield API is fully functional and ready for deployment!")
    else:
        print("\n" + "⚠️ SOME TESTS FAILED ⚠️".center(70, "="))
        print("Please review the failed tests and fix any issues.")
    
    print("="*70)

if __name__ == "__main__":
    asyncio.run(main())

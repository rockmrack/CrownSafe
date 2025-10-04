#!/usr/bin/env python3
"""
Test script to verify cleanup fixes
Tests import paths and application startup
"""

import sys
import io

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def test_import_paths():
    """Test that all import paths are now correct"""
    print("\n=== Testing Import Paths ===")
    
    try:
        # Test api.services imports
        from api.services.dev_override import dev_entitled
        print("✅ api.services.dev_override imported successfully")
        
        from api.services.search_service import SearchService
        print("✅ api.services.search_service imported successfully")
        
        # Test api.security imports
        from api.security.monitoring_dashboard import router
        print("✅ api.security.monitoring_dashboard imported successfully")
        
        print("\n✅ All import paths corrected successfully!")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_application_startup():
    """Test that the application still starts correctly"""
    print("\n=== Testing Application Startup ===")
    
    try:
        from api.main_babyshield import app
        route_count = len(app.routes)
        print(f"✅ Application created successfully with {route_count} routes")
        
        if route_count >= 280:
            print(f"✅ Route count looks good ({route_count} routes)")
            return True
        else:
            print(f"⚠️  Route count lower than expected: {route_count} (expected ~280)")
            return False
    except Exception as e:
        print(f"❌ Application startup failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_legacy_scripts_removed():
    """Test that legacy FIX_ scripts have been removed"""
    print("\n=== Testing Legacy Scripts Removal ===")
    
    import os
    
    legacy_scripts = [
        'FIX_CHAT_ROUTER_IMPORT.py',
        'fix_imports.py',
        'fix_deployment.py',
        'fix_scan_history.py',
        'fix_database.py'
    ]
    
    all_removed = True
    for script in legacy_scripts:
        if os.path.exists(script):
            print(f"❌ Legacy script still exists: {script}")
            all_removed = False
        else:
            print(f"✅ Legacy script removed: {script}")
    
    if all_removed:
        print("\n✅ All legacy scripts removed successfully!")
    
    return all_removed

def main():
    """Run all tests"""
    print("=" * 60)
    print("CLEANUP FIXES - VERIFICATION TESTS")
    print("=" * 60)
    
    tests = [
        ("Import Paths", test_import_paths),
        ("Application Startup", test_application_startup),
        ("Legacy Scripts Removal", test_legacy_scripts_removed),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test '{test_name}' crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Cleanup complete. Ready for PR.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Review errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())


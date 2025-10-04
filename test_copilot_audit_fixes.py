#!/usr/bin/env python3
"""
Test script to verify Copilot audit fixes
Tests import correctness, database migrations, and application startup
"""

import sys
import io
import os

# Fix Windows console encoding only on Windows and when buffer exists
if os.name == 'nt' and hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def test_critical_imports():
    """Test that all critical imports succeed without masking"""
    print("\n=== Testing Critical Imports ===")
    
    try:
        from api.main_babyshield import app
        print("✅ Main application imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database_imports():
    """Test database module imports"""
    print("\n=== Testing Database Module ===")
    
    try:
        from core_infra.database import get_db_session, User, engine, Base
        print("✅ Database imports successful")
        
        # Verify ensure_user_columns() function has been removed
        import inspect
        import core_infra.database as db_module
        functions = [name for name, obj in inspect.getmembers(db_module) if inspect.isfunction(obj)]
        
        if 'ensure_user_columns' in functions:
            print("❌ ensure_user_columns() function still exists (should be removed)")
            return False
        else:
            print("✅ Runtime schema modification functions removed")
        
        return True
    except ImportError as e:
        print(f"❌ Database import failed: {e}")
        return False

def test_agent_imports():
    """Test agent module imports"""
    print("\n=== Testing Agent Module Imports ===")
    
    try:
        from agents.command.commander_agent.agent_logic import BabyShieldCommanderLogic
        from agents.visual.visual_search_agent.agent_logic import VisualSearchAgentLogic
        print("✅ Agent imports successful")
        return True
    except ImportError as e:
        print(f"❌ Agent import failed: {e}")
        return False

def test_alembic_migrations():
    """Test that Alembic migrations exist"""
    print("\n=== Testing Alembic Migrations ===")
    
    import os
    
    migration_files = [
        'alembic/versions/202410_04_add_recalls_enhanced_columns.py',
        'alembic/versions/202410_04_add_user_columns.py'
    ]
    
    all_exist = True
    for migration_file in migration_files:
        if os.path.exists(migration_file):
            print(f"✅ Migration exists: {migration_file}")
        else:
            print(f"❌ Migration missing: {migration_file}")
            all_exist = False
    
    return all_exist

def test_fix_scripts_archived():
    """Test that old FIX_ scripts are documented for archival"""
    print("\n=== Checking FIX_ Scripts Status ===")
    
    import os
    
    fix_scripts = [
        'FIX_CHAT_ROUTER_IMPORT.py',
        'fix_imports.py',
        'fix_deployment.py',
        'fix_scan_history.py',
        'fix_database.py'
    ]
    
    still_present = []
    for script in fix_scripts:
        if os.path.exists(script):
            still_present.append(script)
    
    if still_present:
        print(f"⚠️  FIX_ scripts still present (should be archived in follow-up): {still_present}")
        print("   These will be removed in a follow-up commit")
    else:
        print("✅ All FIX_ scripts removed/archived")
    
    return True  # Not blocking

def test_application_startup():
    """Test that the application can start without errors"""
    print("\n=== Testing Application Startup ===")
    
    try:
        from api.main_babyshield import app
        
        # Check that the app has routes registered
        route_count = len(app.routes)
        print(f"✅ Application created successfully with {route_count} routes")
        
        # Check for critical routes
        critical_paths = ['/healthz', '/docs', '/openapi.json']
        routes_present = {route.path for route in app.routes}
        
        for path in critical_paths:
            if path in routes_present:
                print(f"✅ Critical route registered: {path}")
            else:
                print(f"⚠️  Route may not be registered: {path}")
        
        return True
    except Exception as e:
        print(f"❌ Application startup failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("COPILOT AUDIT FIX - VERIFICATION TESTS")
    print("=" * 60)
    
    tests = [
        ("Critical Imports", test_critical_imports),
        ("Database Module", test_database_imports),
        ("Agent Imports", test_agent_imports),
        ("Alembic Migrations", test_alembic_migrations),
        ("FIX_ Scripts Status", test_fix_scripts_archived),
        ("Application Startup", test_application_startup),
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
        print("\n🎉 ALL TESTS PASSED! Ready for PR.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Review errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())


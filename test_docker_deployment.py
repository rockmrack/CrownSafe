#!/usr/bin/env python3
"""
Test script to verify all deployment fixes are working
"""

import os
import sys
import subprocess

def check_requirement(module_name):
    """Check if a Python module can be imported"""
    try:
        __import__(module_name)
        print(f"✅ {module_name} is available")
        return True
    except ImportError:
        print(f"❌ {module_name} is NOT available")
        return False

def main():
    print("🔍 DEPLOYMENT VERIFICATION TEST")
    print("="*50)
    
    # Check critical modules
    print("\n📋 Checking Required Modules:")
    print("-"*30)
    
    required_modules = [
        'fastapi',
        'uvicorn', 
        'sqlalchemy',
        'pydantic',
        'httpx',
        'psutil',  # The missing module that was causing issues
        'passlib',
        'jose',
        'requests'
    ]
    
    all_good = True
    for module in required_modules:
        if not check_requirement(module):
            all_good = False
    
    # Check psutil specifically
    print("\n📋 Testing psutil Functionality:")
    print("-"*30)
    try:
        import psutil
        print(f"✅ psutil version: {psutil.__version__}")
        print(f"✅ CPU count: {psutil.cpu_count()}")
        print(f"✅ Memory available: {psutil.virtual_memory().available / (1024**3):.2f} GB")
    except Exception as e:
        print(f"❌ psutil error: {e}")
        all_good = False
    
    # Check if API can be imported
    print("\n📋 Testing API Import:")
    print("-"*30)
    try:
        from api.main_babyshield import app
        print("✅ main_babyshield imports successfully")
    except ImportError as e:
        print(f"⚠️ main_babyshield import failed: {e}")
        try:
            from api.main_babyshield_simplified import app
            print("✅ Fallback to simplified API successful")
        except ImportError:
            print("❌ No API module can be imported!")
            all_good = False
    
    # Check database imports
    print("\n📋 Testing Database Import:")
    print("-"*30)
    try:
        from core_infra.database import get_db, get_db_session
        print("✅ Database functions import successfully")
    except ImportError as e:
        print(f"❌ Database import error: {e}")
        all_good = False
    
    # Final verdict
    print("\n" + "="*50)
    if all_good:
        print("✅✅✅ ALL CHECKS PASSED - READY FOR DEPLOYMENT!")
    else:
        print("⚠️ Some issues found - review above")
    print("="*50)
    
    return 0 if all_good else 1

if __name__ == "__main__":
    sys.exit(main())

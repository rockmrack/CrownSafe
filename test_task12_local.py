#!/usr/bin/env python3
"""
Test Task 12 endpoints are registered locally
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_local_registration():
    """Test that Task 12 endpoints are registered in the app"""
    
    print("="*70)
    print("TASK 12: LOCAL ENDPOINT REGISTRATION TEST")
    print("="*70)
    
    try:
        # Import the app
        from api.main_babyshield import app
        
        # Get all routes
        routes = []
        for route in app.routes:
            if hasattr(route, 'path'):
                routes.append(route.path)
        
        # Task 12 endpoints
        task12_endpoints = [
            "/api/v1/barcode/scan",
            "/api/v1/barcode/cache/status",
            "/api/v1/barcode/cache/clear",
            "/api/v1/barcode/test/barcodes"
        ]
        
        print("\nChecking Task 12 endpoints:")
        print("-"*70)
        
        found = 0
        missing = []
        
        for endpoint in task12_endpoints:
            if endpoint in routes:
                print(f"✅ {endpoint}")
                found += 1
            else:
                print(f"❌ {endpoint} - NOT FOUND")
                missing.append(endpoint)
        
        # Also check for existing barcode endpoints
        existing_barcode = [
            "/api/v1/scan/barcode",
            "/api/v1/scan/image",
            "/api/v1/scan/qr/generate"
        ]
        
        print("\nExisting barcode endpoints (should still work):")
        print("-"*70)
        
        for endpoint in existing_barcode:
            if endpoint in routes:
                print(f"✅ {endpoint}")
        
        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70)
        
        if found == len(task12_endpoints):
            print(f"✅ ALL TASK 12 ENDPOINTS REGISTERED! ({found}/{len(task12_endpoints)})")
            print("\nBoth barcode systems available:")
            print("1. Original: /api/v1/scan/* (comprehensive scanning)")
            print("2. Task 12: /api/v1/barcode/* (optimized for mobile)")
            return True
        else:
            print(f"⚠️ SOME ENDPOINTS MISSING: {found}/{len(task12_endpoints)}")
            print("\nMissing endpoints:")
            for endpoint in missing:
                print(f"  - {endpoint}")
            
            print("\nPossible issues:")
            print("1. Check if api/barcode_bridge.py exists")
            print("2. Check for import errors in the file")
            print("3. Check main_babyshield.py includes the router")
            return False
            
    except ImportError as e:
        print(f"❌ Failed to import app: {e}")
        print("\nMake sure you're in the project root directory")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_barcode_bridge_import():
    """Test that barcode_bridge module can be imported"""
    
    print("\n" + "="*70)
    print("MODULE IMPORT TEST")
    print("="*70)
    
    try:
        from api.barcode_bridge import router, BarcodeCache, normalize_barcode
        print("✅ barcode_bridge module imported successfully")
        
        # Test cache instantiation
        cache = BarcodeCache(max_size=10)
        print("✅ BarcodeCache instantiated")
        
        # Test barcode normalization
        test_barcode, barcode_type = normalize_barcode("123456789012")
        print(f"✅ Barcode normalization works: {test_barcode} ({barcode_type})")
        
        # Check router endpoints
        print("\nRouter paths:")
        for route in router.routes:
            if hasattr(route, 'path'):
                print(f"  - {route.path} [{', '.join(route.methods)}]")
        
        return True
        
    except ImportError as e:
        print(f"❌ Failed to import barcode_bridge: {e}")
        return False
    except Exception as e:
        print(f"❌ Error testing module: {e}")
        return False


if __name__ == "__main__":
    success = True
    
    # Test module import
    if not test_barcode_bridge_import():
        success = False
    
    # Test endpoint registration
    if not test_local_registration():
        success = False
    
    if success:
        print("\n" + "="*70)
        print("🎉 TASK 12 IMPLEMENTATION SUCCESSFUL!")
        print("="*70)
        print("\nNext steps:")
        print("1. Run the API locally: python api/main_babyshield.py")
        print("2. Test with: python test_task12_barcodes.py")
        print("3. Deploy to production")
    else:
        print("\n⚠️ Please fix the issues above before proceeding")
        sys.exit(1)

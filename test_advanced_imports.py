#!/usr/bin/env python3
"""
Quick test to verify advanced visual recognition imports are working
"""

def test_imports():
    """Test that all required imports are available"""
    try:
        # Test the specific import that was failing
        import os
        print("✅ os import: OK")
        
        # Test other critical imports used in the endpoint
        from datetime import datetime
        print("✅ datetime import: OK")
        
        import uuid
        print("✅ uuid import: OK")
        
        import hashlib
        print("✅ hashlib import: OK")
        
        # Test the endpoint can be imported without errors
        from api.advanced_features_endpoints import router
        print("✅ advanced_features_endpoints import: OK")
        
        print("\n🎉 All critical imports working!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_imports()
    exit(0 if success else 1)

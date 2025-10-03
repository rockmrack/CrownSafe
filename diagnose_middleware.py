"""
Diagnose Middleware Issues
Quick test to see if Phase 2 middleware is executing
"""

import requests
import sys

def test_middleware_execution():
    """Test if Phase 2 middleware is actually executing"""
    print("\n=== Middleware Execution Diagnostic ===\n")
    
    url = "http://localhost:8001/docs"
    
    try:
        response = requests.get(url, timeout=5)
        headers = dict(response.headers)
        
        print("ALL Response Headers:")
        print("-" * 60)
        for key, value in sorted(headers.items()):
            print(f"{key}: {value[:100]}...")
        
        print("\n" + "=" * 60)
        print("ANALYSIS:")
        print("-" * 60)
        
        # Check OLD middleware headers (from core_infra)
        old_headers = {
            'x-frame-options': 'Old Middleware',
            'x-content-type-options': 'Old Middleware',
            'x-xss-protection': 'Old Middleware',
            'referrer-policy': 'Old Middleware',
            'strict-transport-security': 'Old Middleware',
        }
        
        # Check NEW middleware headers (from Phase 2)
        new_headers = {
            'content-security-policy': 'Phase 2 Middleware',
            'permissions-policy': 'Phase 2 Middleware',
            'x-permitted-cross-domain-policies': 'Phase 2 Middleware',
        }
        
        print("\nOLD Middleware (core_infra):")
        for header, source in old_headers.items():
            status = "✓ PRESENT" if header in headers else "✗ MISSING"
            print(f"  {status}: {header}")
        
        print("\nNEW Middleware (Phase 2):")
        for header, source in new_headers.items():
            status = "✓ PRESENT" if header in headers else "✗ MISSING"
            print(f"  {status}: {header}")
        
        # Diagnosis
        old_count = sum(1 for h in old_headers if h in headers)
        new_count = sum(1 for h in new_headers if h in headers)
        
        print("\n" + "=" * 60)
        print("DIAGNOSIS:")
        print("-" * 60)
        
        if old_count > 0 and new_count == 0:
            print("❌ OLD middleware IS working")
            print("❌ NEW middleware NOT executing")
            print("\nPOSSIBLE CAUSES:")
            print("1. Middleware order issue (old middleware terminating chain)")
            print("2. Exception in new middleware being caught silently")
            print("3. Middleware not properly registered with FastAPI")
            print("4. Import error at runtime")
            print("\nSOLUTION: Check middleware registration order in main_babyshield.py")
            
        elif old_count > 0 and new_count > 0:
            print("✓ BOTH middlewares working!")
            print("Your security headers are fully active.")
            
        elif old_count == 0 and new_count > 0:
            print("✓ NEW middleware working")
            print("❌ OLD middleware not working")
            
        else:
            print("❌ NO middleware headers detected")
            print("Something is seriously wrong!")
        
        print("\n" + "=" * 60)
        return old_count, new_count
        
    except Exception as e:
        print(f"[ERROR] Diagnostic failed: {e}")
        return 0, 0


if __name__ == "__main__":
    old, new = test_middleware_execution()
    
    if old > 0 and new == 0:
        print("\n🔧 ACTION REQUIRED:")
        print("Phase 2 middleware is NOT executing.")
        print("Checking middleware registration...\n")
        sys.exit(1)
    elif old > 0 and new > 0:
        print("\n✓ SUCCESS: All middleware operational!\n")
        sys.exit(0)
    else:
        print("\n⚠ PARTIAL: Check middleware configuration\n")
        sys.exit(1)


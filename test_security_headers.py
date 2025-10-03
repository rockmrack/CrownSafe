"""
Test Security Headers Integration
Verifies that Phase 2 security headers are properly applied
"""

import sys
import requests
from typing import Dict, List

def test_security_headers(url: str = "http://localhost:8001/docs") -> Dict[str, bool]:
    """
    Test if security headers are present in API responses
    
    Returns:
        Dictionary of header checks and their status
    """
    print(f"\n=== Testing Security Headers ===")
    print(f"URL: {url}\n")
    
    try:
        response = requests.head(url, timeout=5)
        headers = response.headers
        
        # Expected security headers
        checks = {
            "X-Frame-Options": "DENY",
            "X-Content-Type-Options": "nosniff",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Content-Security-Policy": None,  # Just check it exists
            "Permissions-Policy": None,
            "X-Permitted-Cross-Domain-Policies": "none",
        }
        
        # HSTS only in production
        # "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
        
        results = {}
        print("Security Header Checks:")
        print("-" * 60)
        
        for header, expected_value in checks.items():
            if header in headers:
                actual_value = headers[header]
                if expected_value is None:
                    # Just check presence
                    results[header] = True
                    print(f"[OK] {header}: {actual_value[:50]}...")
                elif actual_value == expected_value:
                    results[header] = True
                    print(f"[OK] {header}: {actual_value}")
                else:
                    results[header] = False
                    print(f"[WARN] {header}: Expected '{expected_value}', got '{actual_value}'")
            else:
                results[header] = False
                print(f"[FAIL] {header}: MISSING")
        
        # Additional headers
        print("\nAdditional Headers:")
        print("-" * 60)
        
        rate_limit_headers = ["X-RateLimit-Limit", "X-RateLimit-Remaining"]
        for header in rate_limit_headers:
            if header in headers:
                print(f"[OK] {header}: {headers[header]}")
            else:
                print(f"[INFO] {header}: Not present (may appear after first request)")
        
        # Summary
        print("\n" + "=" * 60)
        passed = sum(1 for v in results.values() if v)
        total = len(results)
        
        if passed == total:
            print(f"[SUCCESS] All {total}/{total} security headers present!")
            print("\nPhase 2 security headers are ACTIVE and working! ✓")
            return results
        else:
            print(f"[PARTIAL] {passed}/{total} security headers present")
            print("\nSome headers missing. Check middleware activation.")
            return results
            
    except requests.exceptions.ConnectionError:
        print("[ERROR] Could not connect to API")
        print("Make sure the server is running: python -m uvicorn api.main_babyshield:app --reload")
        return {}
    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        return {}


def test_full_request(url: str = "http://localhost:8001/docs"):
    """Test with a full GET request"""
    print(f"\n\n=== Testing Full GET Request ===")
    print(f"URL: {url}\n")
    
    try:
        response = requests.get(url, timeout=5)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        print("\nAll Response Headers:")
        print("-" * 60)
        for header, value in response.headers.items():
            # Truncate long values
            display_value = value if len(value) < 100 else value[:97] + "..."
            print(f"{header}: {display_value}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Full request test failed: {e}")
        return False


if __name__ == "__main__":
    # Test both HEAD and GET requests
    # NOTE: Don't use /healthz - it bypasses middleware for ultra-fast health checks!
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8001/docs"
    
    results_head = test_security_headers(url)
    results_get = test_full_request(url)
    
    # Final verdict
    print("\n" + "=" * 60)
    if results_head and all(results_head.values()):
        print("✓ VERDICT: Security headers are properly configured!")
        print("\nYour API now has OWASP-compliant security headers.")
        sys.exit(0)
    elif results_head:
        print("⚠ VERDICT: Some security headers are missing")
        print("\nRestart the server and try again.")
        sys.exit(1)
    else:
        print("✗ VERDICT: Could not verify security headers")
        print("\nMake sure the server is running.")
        sys.exit(2)


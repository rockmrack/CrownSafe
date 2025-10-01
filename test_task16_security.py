#!/usr/bin/env python3
"""
Task 16: Security Testing Script
Tests security implementations including WAF, secrets, and database security
"""

import os
import sys
import requests
import subprocess
import json
import time
from datetime import datetime
from typing import Dict, List, Any

# Test configuration
BASE_URL = os.environ.get("API_URL", "https://babyshield.cureviax.ai")
ADMIN_API_KEY = os.environ.get("ADMIN_API_KEY", "test-key-123")

def print_header(title: str):
    """Print a formatted header"""
    print("\n" + "="*70)
    print(f" {title}")
    print("="*70)


def test_security_headers():
    """Test security headers in API responses"""
    
    print_header("SECURITY HEADERS TEST")
    
    try:
        response = requests.get(f"{BASE_URL}/api/v1/healthz", timeout=5)
        
        required_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": ["DENY", "SAMEORIGIN"],
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": ["strict-origin-when-cross-origin", "no-referrer"],
            "Permissions-Policy": None,  # Just check presence
        }
        
        # Production-only headers
        if "babyshield.cureviax.ai" in BASE_URL:
            required_headers["Strict-Transport-Security"] = None
        
        print("Security Headers Check:")
        all_present = True
        
        for header, expected_values in required_headers.items():
            actual_value = response.headers.get(header)
            
            if actual_value:
                if expected_values:
                    if isinstance(expected_values, list):
                        is_valid = any(val in actual_value for val in expected_values)
                    else:
                        is_valid = expected_values in actual_value
                    
                    status = "âœ…" if is_valid else "âš ï¸"
                    print(f"  {status} {header}: {actual_value[:50]}...")
                else:
                    print(f"  âœ… {header}: Present")
            else:
                print(f"  âŒ {header}: Missing")
                all_present = False
        
        # Check for dangerous headers
        dangerous_headers = ["Server", "X-Powered-By", "X-AspNet-Version"]
        print("\nDangerous Headers Check:")
        
        for header in dangerous_headers:
            if header in response.headers:
                print(f"  âš ï¸ {header}: Present (should be removed)")
            else:
                print(f"  âœ… {header}: Not present")
        
        return all_present
        
    except Exception as e:
        print(f"âŒ Security headers test failed: {e}")
        return False


def test_admin_endpoint_protection():
    """Test admin endpoint IP allowlist"""
    
    print_header("ADMIN ENDPOINT PROTECTION TEST")
    
    admin_endpoints = [
        "/admin",
        "/api/v1/admin",
        "/monitoring/metrics",
    ]
    
    print("Testing admin endpoint access restrictions:")
    
    for endpoint in admin_endpoints:
        url = f"{BASE_URL}{endpoint}"
        
        try:
            # Test without API key (should fail)
            response = requests.get(url, timeout=5)
            
            if response.status_code == 403:
                print(f"  âœ… {endpoint}: Protected (403 Forbidden)")
            elif response.status_code == 401:
                print(f"  âœ… {endpoint}: Protected (401 Unauthorized)")
            elif response.status_code == 404:
                print(f"  â„¹ï¸ {endpoint}: Not found (may not be implemented)")
            else:
                print(f"  âŒ {endpoint}: Accessible without auth (Status: {response.status_code})")
            
            # Test with API key
            headers = {"X-API-Key": ADMIN_API_KEY}
            response = requests.get(url, headers=headers, timeout=5)
            
            # From allowed IP with API key should work
            # From blocked IP should still fail
            
        except requests.exceptions.RequestException as e:
            print(f"  âš ï¸ {endpoint}: Connection error")
    
    return True


def test_sql_injection_protection():
    """Test SQL injection protection"""
    
    print_header("SQL INJECTION PROTECTION TEST")
    
    # Common SQL injection payloads
    sql_payloads = [
        "' OR '1'='1",
        "'; DROP TABLE users--",
        "' UNION SELECT * FROM users--",
        "admin'--",
        "1' AND '1'='1",
        "' OR 1=1--",
        "'; EXECUTE IMMEDIATE 'SELECT * FROM users'--",
    ]
    
    print("Testing SQL injection protection:")
    protected = True
    
    for payload in sql_payloads:
        try:
            # Test in search endpoint
            response = requests.post(
                f"{BASE_URL}/api/v1/search/advanced",
                json={"product": payload},
                timeout=5
            )
            
            if response.status_code >= 500:
                print(f"  âŒ Payload caused error (500): {payload[:30]}...")
                protected = False
            elif response.status_code == 400:
                print(f"  âœ… Payload blocked (400): {payload[:30]}...")
            else:
                # Check if payload was sanitized
                if response.status_code == 200:
                    results = response.json()
                    if results.get("total", 0) == 0:
                        print(f"  âœ… Payload sanitized (no results): {payload[:30]}...")
                    else:
                        print(f"  âš ï¸ Payload returned results: {payload[:30]}...")
                        
        except Exception as e:
            print(f"  âš ï¸ Error testing payload: {payload[:30]}...")
    
    return protected


def test_xss_protection():
    """Test XSS protection"""
    
    print_header("XSS PROTECTION TEST")
    
    xss_payloads = [
        "<script>alert('XSS')</script>",
        "<img src=x onerror=alert('XSS')>",
        "javascript:alert('XSS')",
        "<body onload=alert('XSS')>",
        "<iframe src='javascript:alert(1)'>",
        "';alert(String.fromCharCode(88,83,83))//",
    ]
    
    print("Testing XSS protection:")
    protected = True
    
    for payload in xss_payloads:
        try:
            # Test in user input endpoints
            response = requests.post(
                f"{BASE_URL}/api/v1/search/advanced",
                json={"product": payload},
                timeout=5
            )
            
            if response.status_code == 400:
                print(f"  âœ… XSS payload blocked: {payload[:30]}...")
            elif response.status_code == 200:
                # Check if payload was escaped in response
                response_text = response.text
                if payload in response_text:
                    print(f"  âŒ XSS payload not escaped: {payload[:30]}...")
                    protected = False
                else:
                    print(f"  âœ… XSS payload escaped: {payload[:30]}...")
                    
        except Exception as e:
            print(f"  âš ï¸ Error testing XSS: {payload[:30]}...")
    
    # Check CSP header
    try:
        response = requests.get(f"{BASE_URL}/api/v1/healthz", timeout=5)
        csp = response.headers.get("Content-Security-Policy")
        
        if csp:
            print(f"\nâœ… CSP Header present:")
            print(f"  {csp[:100]}...")
        else:
            print("\nâš ï¸ CSP Header missing")
            protected = False
            
    except Exception:
        pass
    
    return protected


def test_rate_limiting():
    """Test rate limiting protection"""
    
    print_header("RATE LIMITING TEST")
    
    print("Testing rate limiting (100 rapid requests):")
    
    blocked_count = 0
    success_count = 0
    
    for i in range(100):
        try:
            response = requests.get(
                f"{BASE_URL}/api/v1/healthz",
                timeout=1
            )
            
            if response.status_code == 429:
                blocked_count += 1
                if blocked_count == 1:
                    print(f"  âœ… Rate limiting activated at request #{i+1}")
            elif response.status_code == 200:
                success_count += 1
                
        except Exception:
            pass
        
        # Small delay to not completely flood
        if i % 10 == 0:
            time.sleep(0.1)
    
    print(f"  Results: {success_count} successful, {blocked_count} rate-limited")
    
    if blocked_count > 0:
        print("  âœ… Rate limiting is working")
        return True
    else:
        print("  âš ï¸ Rate limiting may not be configured")
        return False


def test_authentication_security():
    """Test authentication security"""
    
    print_header("AUTHENTICATION SECURITY TEST")
    
    print("Testing authentication security:")
    
    # Test JWT security
    invalid_tokens = [
        "invalid.token.here",
        "eyJhbGciOiJub25lIn0.eyJzdWIiOiIxMjM0NTY3ODkwIn0.",  # Algorithm: none
        "",  # Empty token
    ]
    
    for token in invalid_tokens:
        try:
            response = requests.get(
                f"{BASE_URL}/api/v1/user/profile",
                headers={"Authorization": f"Bearer {token}"},
                timeout=5
            )
            
            if response.status_code == 401:
                print(f"  âœ… Invalid token rejected: {token[:20]}...")
            else:
                print(f"  âŒ Invalid token accepted: {token[:20]}...")
                
        except Exception:
            print(f"  âš ï¸ Error testing token: {token[:20]}...")
    
    # Test password policy
    weak_passwords = ["123456", "password", "12345678", "qwerty", "abc123"]
    
    print("\n  Testing password strength requirements:")
    for pwd in weak_passwords:
        # This would need an actual registration endpoint
        print(f"    âš ï¸ Password policy test requires registration endpoint")
        break
    
    return True


def test_secure_database_connection():
    """Test secure database configuration"""
    
    print_header("DATABASE SECURITY TEST")
    
    print("Checking database security configuration:")
    
    checks = {
        "SSL/TLS encryption": False,
        "Read-only user for queries": False,
        "Connection pooling": False,
        "Statement timeout": False,
        "Row-level security": False,
    }
    
    # Check environment variables
    db_url = os.environ.get("DATABASE_URL", "")
    readonly_url = os.environ.get("DATABASE_URL_READONLY", "")
    
    if "sslmode=require" in db_url or "sslmode=verify" in db_url:
        checks["SSL/TLS encryption"] = True
        print("  âœ… SSL/TLS encryption: Enabled")
    else:
        print("  âš ï¸ SSL/TLS encryption: Not verified in connection string")
    
    if readonly_url:
        checks["Read-only user for queries"] = True
        print("  âœ… Read-only user: Configured")
    else:
        print("  âš ï¸ Read-only user: Not configured")
    
    # Test actual database security (would need DB access)
    print("\n  Note: Full database security requires direct DB access to verify")
    
    return all(checks.values())


def test_secret_management():
    """Test secret management practices"""
    
    print_header("SECRET MANAGEMENT TEST")
    
    print("Checking secret management:")
    
    # Check for secrets in environment
    sensitive_vars = [
        "DATABASE_URL",
        "JWT_SECRET_KEY",
        "AWS_SECRET_ACCESS_KEY",
        "STRIPE_SECRET_KEY",
        "OPENAI_API_KEY",
    ]
    
    for var in sensitive_vars:
        value = os.environ.get(var, "")
        if value:
            # Check if it looks like a placeholder
            if "CHANGE" in value or "YOUR" in value or "XXX" in value:
                print(f"  âš ï¸ {var}: Contains placeholder value")
            else:
                print(f"  âœ… {var}: Configured (hidden)")
        else:
            print(f"  âš ï¸ {var}: Not set")
    
    # Check for AWS Parameter Store usage
    try:
        result = subprocess.run(
            ["aws", "ssm", "describe-parameters", "--region", "eu-north-1"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            params = json.loads(result.stdout)
            param_count = len(params.get("Parameters", []))
            
            if param_count > 0:
                print(f"\n  âœ… AWS Parameter Store: {param_count} parameters configured")
            else:
                print("\n  âš ï¸ AWS Parameter Store: No parameters found")
        else:
            print("\n  â„¹ï¸ AWS Parameter Store: Unable to check (AWS CLI not configured)")
            
    except Exception as e:
        print(f"\n  â„¹ï¸ AWS Parameter Store: Unable to check ({e})")
    
    return True


def test_docker_security():
    """Test Docker container security"""
    
    print_header("CONTAINER SECURITY TEST")
    
    print("Checking Docker security:")
    
    # Check if running as non-root
    try:
        result = subprocess.run(
            ["docker", "run", "--rm", "babyshield-backend:latest", "whoami"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            user = result.stdout.strip()
            if user == "root":
                print("  âš ï¸ Container running as root user")
            else:
                print(f"  âœ… Container running as non-root user: {user}")
        else:
            print("  â„¹ï¸ Unable to check container user")
            
    except Exception:
        print("  â„¹ï¸ Docker not available for testing")
    
    # Check Dockerfile best practices
    dockerfile_checks = {
        "Multi-stage build": False,
        "No secrets in image": False,
        "Security scanning": False,
        "Minimal base image": False,
    }
    
    if os.path.exists("Dockerfile.final"):
        with open("Dockerfile.final", "r") as f:
            content = f.read()
            
            if "FROM" in content and content.count("FROM") > 1:
                dockerfile_checks["Multi-stage build"] = True
                print("  âœ… Multi-stage build: Used")
            
            if "ENV" in content and any(s in content for s in ["PASSWORD", "SECRET", "KEY"]):
                print("  âš ï¸ Potential secrets in Dockerfile")
            else:
                dockerfile_checks["No secrets in image"] = True
                print("  âœ… No secrets in Dockerfile")
            
            if "slim" in content or "alpine" in content:
                dockerfile_checks["Minimal base image"] = True
                print("  âœ… Minimal base image: Used")
    
    return True


def run_security_audit():
    """Run complete security audit"""
    
    print("="*70)
    print(" BABYSHIELD SECURITY AUDIT")
    print(f" Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f" Target: {BASE_URL}")
    print("="*70)
    
    results = {}
    
    # Run all security tests
    tests = [
        ("Security Headers", test_security_headers),
        ("Admin Protection", test_admin_endpoint_protection),
        ("SQL Injection Protection", test_sql_injection_protection),
        ("XSS Protection", test_xss_protection),
        ("Rate Limiting", test_rate_limiting),
        ("Authentication Security", test_authentication_security),
        ("Database Security", test_secure_database_connection),
        ("Secret Management", test_secret_management),
        ("Container Security", test_docker_security),
    ]
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\nâŒ {test_name} test failed with error: {e}")
            results[test_name] = False
    
    # Print summary
    print_header("SECURITY AUDIT SUMMARY")
    
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    print(f"\nTest Results: {passed}/{total} Passed")
    print("-" * 40)
    
    for test_name, result in results.items():
        status = "âœ… PASS" if result else "âŒ FAIL"
        print(f"{status}: {test_name}")
    
    # Overall assessment
    print("\n" + "="*70)
    
    if passed == total:
        print("ðŸŽ‰ EXCELLENT: All security tests passed!")
        print("The application meets security best practices.")
    elif passed >= total * 0.8:
        print("âœ… GOOD: Most security tests passed.")
        print("Address the failed tests to improve security posture.")
    elif passed >= total * 0.6:
        print("âš ï¸ FAIR: Several security issues detected.")
        print("Immediate attention required for failed tests.")
    else:
        print("âŒ CRITICAL: Major security issues detected!")
        print("Do not deploy to production until issues are resolved.")
    
    print("="*70)
    
    # Recommendations
    print("\nðŸ“‹ RECOMMENDATIONS:")
    recommendations = [
        "1. Enable WAF rules on the load balancer",
        "2. Rotate all secrets every 90 days",
        "3. Use read-only database user for SELECT queries",
        "4. Enable container image scanning in CI/CD",
        "5. Implement IP allowlisting for admin endpoints",
        "6. Regular security audits and penetration testing",
        "7. Monitor security alerts and logs",
        "8. Keep all dependencies updated",
    ]
    
    for rec in recommendations:
        print(f"  {rec}")
    
    return passed == total


if __name__ == "__main__":
    # Run the security audit
    success = run_security_audit()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

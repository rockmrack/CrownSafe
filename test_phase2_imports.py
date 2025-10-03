"""
Test Phase 2 Imports
Quick validation that all new modules can be imported
"""

import sys
import os
from pathlib import Path

# Fix Windows console encoding
if os.name == 'nt':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Ensure root is in path
root_dir = Path(__file__).parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

def test_imports():
    """Test that all new modules can be imported"""
    print("\n=== Testing Phase 2 Imports ===\n")
    
    tests = []
    
    # Test 1: Security utilities
    try:
        from utils.security.input_validator import InputValidator
        print("[OK] input_validator imports successfully")
        tests.append(("input_validator", True, None))
    except Exception as e:
        print(f"[FAIL] input_validator failed: {e}")
        tests.append(("input_validator", False, str(e)))
    
    # Test 2: Security headers
    try:
        from utils.security.security_headers import SecurityHeadersMiddleware
        print("[OK] security_headers imports successfully")
        tests.append(("security_headers", True, None))
    except Exception as e:
        print(f"[FAIL] security_headers failed: {e}")
        tests.append(("security_headers", False, str(e)))
    
    # Test 3: Endpoint helpers
    try:
        from utils.common.endpoint_helpers import success_response, error_response
        print("[OK] endpoint_helpers imports successfully")
        tests.append(("endpoint_helpers", True, None))
    except Exception as e:
        print(f"[FAIL] endpoint_helpers failed: {e}")
        tests.append(("endpoint_helpers", False, str(e)))
    
    # Test 4: Query optimizer
    try:
        from utils.database.query_optimizer import OptimizedQuery
        print("[OK] query_optimizer imports successfully")
        tests.append(("query_optimizer", True, None))
    except Exception as e:
        print(f"[FAIL] query_optimizer failed: {e}")
        tests.append(("query_optimizer", False, str(e)))
    
    # Test 5: App factory
    try:
        from api.app_factory import create_app
        print("[OK] app_factory imports successfully")
        tests.append(("app_factory", True, None))
    except Exception as e:
        print(f"[FAIL] app_factory failed: {e}")
        tests.append(("app_factory", False, str(e)))
    
    # Test 6: Shared models
    try:
        from api.schemas.shared_models import ApiResponse, BarcodeScanRequest
        print("[OK] shared_models imports successfully")
        tests.append(("shared_models", True, None))
    except Exception as e:
        print(f"[FAIL] shared_models failed: {e}")
        tests.append(("shared_models", False, str(e)))
    
    # Summary
    print("\n=== Import Test Summary ===\n")
    passed = sum(1 for _, success, _ in tests if success)
    failed = len(tests) - passed
    
    print(f"Passed: {passed}/{len(tests)}")
    print(f"Failed: {failed}/{len(tests)}")
    
    if failed > 0:
        print("\nFailed imports:")
        for name, success, error in tests:
            if not success:
                print(f"  - {name}: {error}")
    
    return failed == 0


def test_basic_functionality():
    """Test basic functionality of imported modules"""
    print("\n=== Testing Basic Functionality ===\n")
    
    tests_passed = 0
    tests_failed = 0
    
    # Test 1: Input validation
    try:
        from utils.security.input_validator import InputValidator
        
        # Test barcode validation
        barcode = InputValidator.validate_barcode("012345678905")
        assert barcode == "012345678905"
        
        # Test invalid barcode
        try:
            InputValidator.validate_barcode("'; DROP TABLE users; --")
            print("[FAIL] SQL injection should have been blocked")
            tests_failed += 1
        except ValueError:
            print("[OK] Input validation blocks SQL injection")
            tests_passed += 1
        
        # Test email validation
        email = InputValidator.validate_email("test@example.com")
        assert email == "test@example.com"
        print("[OK] Email validation works")
        tests_passed += 1
        
    except Exception as e:
        print(f"[FAIL] Input validation test failed: {e}")
        tests_failed += 1
    
    # Test 2: Response helpers
    try:
        from utils.common.endpoint_helpers import success_response, error_response
        
        # Test success response
        response = success_response(data={"test": "value"}, message="Success")
        assert response["success"] is True
        assert response["data"]["test"] == "value"
        print("[OK] Success response works")
        tests_passed += 1
        
        # Test error response
        response = error_response(error="Test error", status_code=400)
        assert response["success"] is False
        assert response["error"] == "Test error"
        print("[OK] Error response works")
        tests_passed += 1
        
    except Exception as e:
        print(f"[FAIL] Response helpers test failed: {e}")
        tests_failed += 1
    
    # Test 3: Shared models
    try:
        from api.schemas.shared_models import BarcodeScanRequest, ApiResponse
        from pydantic import ValidationError
        
        # Test valid request
        request = BarcodeScanRequest(barcode="012345678905", user_id=123)
        assert request.barcode == "012345678905"
        assert request.user_id == 123
        print("[OK] Shared models work")
        tests_passed += 1
        
        # Test invalid request (should raise validation error)
        try:
            request = BarcodeScanRequest(barcode="'; DROP TABLE", user_id=123)
            print("[FAIL] Pydantic validation should have failed")
            tests_failed += 1
        except ValidationError:
            print("[OK] Pydantic validation blocks invalid input")
            tests_passed += 1
        
    except Exception as e:
        print(f"[FAIL] Shared models test failed: {e}")
        tests_failed += 1
    
    # Summary
    print(f"\n=== Functionality Test Summary ===\n")
    print(f"Passed: {tests_passed}")
    print(f"Failed: {tests_failed}")
    
    return tests_failed == 0


if __name__ == "__main__":
    import_success = test_imports()
    functionality_success = test_basic_functionality()
    
    print("\n=== OVERALL RESULTS ===\n")
    if import_success and functionality_success:
        print("[SUCCESS] ALL TESTS PASSED!")
        print("\nPhase 2 improvements are working correctly.")
        print("You can now integrate them into your codebase.\n")
        sys.exit(0)
    else:
        print("[FAILED] SOME TESTS FAILED")
        print("\nPlease review the errors above.\n")
        sys.exit(1)


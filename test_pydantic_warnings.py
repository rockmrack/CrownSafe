#!/usr/bin/env python3
"""
Test script to check for Pydantic model_number warnings
Run with: PYTHONWARNINGS=error python test_pydantic_warnings.py
"""

import warnings
import sys
import os

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, PROJECT_ROOT)

# Set warnings to error to catch any Pydantic warnings
warnings.simplefilter("error")

def test_model_imports():
    """Test importing all models that might have model_number fields"""
    print("🔍 Testing Pydantic model imports for warnings...")
    
    try:
        # Test core schemas
        from core.schemas.base import BaseSchema, AppModel, APIResponse, ErrorResponse
        print("✅ Core schemas imported successfully")
        
        # Test main API models
        from api.main_babyshield import SafetyCheckRequest, SafetyCheckResponse, AdvancedSearchRequest
        print("✅ Main API models imported successfully")
        
        # Test scan results models
        from api.models.scan_results import ProductSummary, BarcodeDetectionResult
        print("✅ Scan results models imported successfully")
        
        # Test recall models
        from api.recalls_endpoints import RecallItem, RecallListResponse
        print("✅ Recall models imported successfully")
        
        # Test monitoring models
        from api.monitoring_endpoints import AddProductRequest, MonitoredProductResponse
        print("✅ Monitoring models imported successfully")
        
        # Test scan history models
        from api.scan_history_endpoints import ScanHistoryItem
        print("✅ Scan history models imported successfully")
        
        # Test risk assessment models
        from api.risk_assessment_endpoints import RiskAssessmentRequest, RiskAssessmentResponse
        print("✅ Risk assessment models imported successfully")
        
        # Test barcode bridge models
        from api.barcode_bridge import BarcodeScanRequest, BarcodeScanResponse
        print("✅ Barcode bridge models imported successfully")
        
        # Test incident report models
        from api.incident_report_endpoints import IncidentSubmitRequest
        print("✅ Incident report models imported successfully")
        
        # Test baby features models
        from api.baby_features_endpoints import ReportRequest
        print("✅ Baby features models imported successfully")
        
        # Test validators
        from core_infra.validators import ValidatedSafetyCheckRequest
        print("✅ Validator models imported successfully")
        
        print("\n🎉 ALL MODELS IMPORTED SUCCESSFULLY - NO PYDANTIC WARNINGS!")
        return True
        
    except Warning as w:
        print(f"\n❌ PYDANTIC WARNING DETECTED: {w}")
        print(f"   This warning was converted to an error by PYTHONWARNINGS=error")
        return False
    except Exception as e:
        print(f"\n❌ ERROR IMPORTING MODELS: {e}")
        return False

def test_model_instantiation():
    """Test creating instances of models with model_number fields"""
    print("\n🔍 Testing model instantiation...")
    
    try:
        from api.main_babyshield import SafetyCheckRequest
        from api.models.scan_results import ProductSummary
        from api.recalls_endpoints import RecallItem
        from api.monitoring_endpoints import AddProductRequest
        from api.scan_history_endpoints import ScanHistoryItem
        
        # Test creating instances
        safety_req = SafetyCheckRequest(
            user_id=1,
            barcode="123456789012",
            model_number="ABC-123"
        )
        print("✅ SafetyCheckRequest created successfully")
        
        product = ProductSummary(
            name="Test Product",
            brand="Test Brand",
            model_number="MODEL-123"
        )
        print("✅ ProductSummary created successfully")
        
        recall = RecallItem(
            id=1,
            model_number="RECALL-123"
        )
        print("✅ RecallItem created successfully")
        
        monitor_req = AddProductRequest(
            product_name="Test Product",
            model_number="MONITOR-123"
        )
        print("✅ AddProductRequest created successfully")
        
        scan_item = ScanHistoryItem(
            job_id="test-123",
            scan_date="2024-01-01T00:00:00Z",
            status="completed",
            model_number="SCAN-123"
        )
        print("✅ ScanHistoryItem created successfully")
        
        print("\n🎉 ALL MODEL INSTANCES CREATED SUCCESSFULLY - NO PYDANTIC WARNINGS!")
        return True
        
    except Warning as w:
        print(f"\n❌ PYDANTIC WARNING DETECTED: {w}")
        return False
    except Exception as e:
        print(f"\n❌ ERROR CREATING MODEL INSTANCES: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testing for Pydantic model_number warnings...")
    print("   (Run with: PYTHONWARNINGS=error python test_pydantic_warnings.py)")
    print()
    
    success1 = test_model_imports()
    success2 = test_model_instantiation()
    
    if success1 and success2:
        print("\n✅ ALL TESTS PASSED - NO PYDANTIC WARNINGS DETECTED!")
        sys.exit(0)
    else:
        print("\n❌ TESTS FAILED - PYDANTIC WARNINGS DETECTED!")
        sys.exit(1)

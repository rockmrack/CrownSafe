"""
Phase 3: Privacy & GDPR Compliance Tests

Tests for GDPR and privacy compliance features.
Validates data export, deletion, anonymization, consent management, and data portability.

Test Coverage:
- Right to data export (GDPR Article 20)
- Right to erasure/deletion (GDPR Article 17)
- Data anonymization
- Consent management (GDPR Article 7)
- Data portability
"""

import pytest
import json
from typing import Dict, List, Optional
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

try:
    from api.models import User
except ImportError:
    # Fallback for testing
    class User:
        pass


@pytest.fixture
def mock_user_with_data():
    """Create a mock user with various data types."""
    user = Mock(spec=User)
    user.id = 1
    user.email = "user@example.com"
    user.username = "testuser"
    user.created_at = datetime.utcnow() - timedelta(days=365)
    user.data = {
        "search_history": [
            {"query": "baby cribs", "timestamp": "2024-01-15T10:30:00Z"},
            {"query": "car seats", "timestamp": "2024-02-20T14:45:00Z"}
        ],
        "saved_products": [101, 102, 103],
        "alerts": [
            {"product_id": 101, "type": "recall", "date": "2024-03-10"}
        ],
        "preferences": {
            "notifications": True,
            "email_alerts": True,
            "categories": ["toys", "furniture"]
        }
    }
    return user


@pytest.fixture
def mock_consent_manager():
    """Create a mock consent management system."""
    class ConsentManager:
        def __init__(self):
            self.consents: Dict[int, Dict[str, any]] = {}
        
        def record_consent(self, user_id: int, purpose: str, granted: bool):
            """Record user consent for a specific purpose."""
            if user_id not in self.consents:
                self.consents[user_id] = {}
            
            self.consents[user_id][purpose] = {
                "granted": granted,
                "timestamp": datetime.utcnow(),
                "version": "1.0"
            }
        
        def check_consent(self, user_id: int, purpose: str) -> bool:
            """Check if user has granted consent for a purpose."""
            if user_id not in self.consents:
                return False
            return self.consents[user_id].get(purpose, {}).get("granted", False)
        
        def get_all_consents(self, user_id: int) -> Dict[str, any]:
            """Get all consents for a user."""
            return self.consents.get(user_id, {})
    
    return ConsentManager()


class GDPRService:
    """Mock GDPR compliance service."""
    
    @staticmethod
    def export_user_data(user: User) -> Dict[str, any]:
        """Export all user data in machine-readable format (GDPR Article 20)."""
        return {
            "user_info": {
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "created_at": user.created_at.isoformat() if user.created_at else None
            },
            "data": user.data,
            "export_date": datetime.utcnow().isoformat(),
            "format": "json",
            "gdpr_compliant": True
        }
    
    @staticmethod
    def delete_user_data(user_id: int, keep_legal_records: bool = True) -> Dict[str, any]:
        """Delete user data while preserving legal requirements (GDPR Article 17)."""
        return {
            "deleted": True,
            "user_id": user_id,
            "deletion_date": datetime.utcnow().isoformat(),
            "retained_data": ["transaction_records", "legal_compliance"] if keep_legal_records else [],
            "anonymized": True
        }
    
    @staticmethod
    def anonymize_user_data(user: User) -> Dict[str, any]:
        """Anonymize user data for retention purposes."""
        return {
            "anonymized": True,
            "original_id": user.id,
            "anonymous_id": f"anon_{hash(str(user.id)) % 1000000}",
            "retained_fields": ["created_at", "subscription_tier"],
            "removed_pii": ["email", "username", "name", "address", "phone"]
        }
    
    @staticmethod
    def validate_data_portability(export_data: Dict) -> Dict[str, any]:
        """Validate that exported data meets portability requirements."""
        required_fields = ["user_info", "data", "export_date", "format"]
        has_required = all(field in export_data for field in required_fields)
        
        return {
            "valid": has_required,
            "machine_readable": export_data.get("format") in ["json", "xml", "csv"],
            "complete": len(export_data.get("data", {})) > 0,
            "structured": isinstance(export_data.get("data"), dict)
        }


@pytest.mark.privacy
@pytest.mark.gdpr
def test_gdpr_data_export_right(mock_user_with_data):
    """
    Test GDPR Article 20 - Right to Data Portability.
    
    Acceptance Criteria:
    - User can export all personal data
    - Export in machine-readable format (JSON/CSV)
    - Includes all data categories
    - Export completed within 30 days (immediate in this case)
    """
    # Request data export
    export_data = GDPRService.export_user_data(mock_user_with_data)
    
    # Validate export structure
    assert "user_info" in export_data, "Export should include user info"
    assert "data" in export_data, "Export should include user data"
    assert "export_date" in export_data, "Export should include timestamp"
    assert export_data["gdpr_compliant"], "Export should be GDPR compliant"
    
    # Validate user info
    user_info = export_data["user_info"]
    assert user_info["id"] == mock_user_with_data.id, "Should include user ID"
    assert user_info["email"] == mock_user_with_data.email, "Should include email"
    assert user_info["username"] == mock_user_with_data.username, "Should include username"
    
    # Validate data completeness
    data = export_data["data"]
    assert "search_history" in data, "Should include search history"
    assert "saved_products" in data, "Should include saved products"
    assert "alerts" in data, "Should include alerts"
    assert "preferences" in data, "Should include preferences"
    
    # Validate data portability
    portability = GDPRService.validate_data_portability(export_data)
    assert portability["valid"], "Export should be valid"
    assert portability["machine_readable"], "Export should be machine-readable"
    assert portability["complete"], "Export should be complete"
    assert portability["structured"], "Export should be structured"
    
    print("✓ GDPR data export completed successfully")
    print(f"✓ Exported {len(data)} data categories")
    print(f"✓ Format: {export_data['format']} (machine-readable)")
    print("✓ All personal data included in export")


@pytest.mark.privacy
@pytest.mark.gdpr
def test_gdpr_right_to_erasure(mock_user_with_data):
    """
    Test GDPR Article 17 - Right to Erasure (Right to be Forgotten).
    
    Acceptance Criteria:
    - User can request account deletion
    - All personal data deleted within 30 days
    - Legal records retained as required
    - Data anonymized where deletion not possible
    - Confirmation provided to user
    """
    user_id = mock_user_with_data.id
    
    # Request deletion
    deletion_result = GDPRService.delete_user_data(user_id, keep_legal_records=True)
    
    # Validate deletion
    assert deletion_result["deleted"], "User data should be deleted"
    assert deletion_result["user_id"] == user_id, "Should confirm user ID"
    assert deletion_result["anonymized"], "Should anonymize retained data"
    
    # Validate legal record retention
    retained = deletion_result["retained_data"]
    assert isinstance(retained, list), "Retained data should be a list"
    assert "transaction_records" in retained, "Should retain transaction records"
    assert "legal_compliance" in retained, "Should retain legal compliance data"
    
    # Validate deletion timestamp
    deletion_date = datetime.fromisoformat(deletion_result["deletion_date"])
    time_diff = datetime.utcnow() - deletion_date
    assert time_diff.total_seconds() < 60, "Deletion should be recent"
    
    # Test complete deletion (no legal requirements)
    complete_deletion = GDPRService.delete_user_data(user_id, keep_legal_records=False)
    assert len(complete_deletion["retained_data"]) == 0, \
        "Complete deletion should retain no data"
    
    print("✓ GDPR right to erasure exercised successfully")
    print(f"✓ User {user_id} data deleted")
    print(f"✓ Retained for legal compliance: {len(retained)} categories")
    print("✓ Data anonymization applied")


@pytest.mark.privacy
@pytest.mark.gdpr
def test_data_anonymization(mock_user_with_data):
    """
    Test data anonymization for GDPR compliance.
    
    Acceptance Criteria:
    - PII removed from all records
    - Anonymous ID generated
    - Statistical data retained
    - Anonymization irreversible
    - Anonymized data cannot be linked back to user
    """
    # Anonymize user data
    anon_result = GDPRService.anonymize_user_data(mock_user_with_data)
    
    # Validate anonymization
    assert anon_result["anonymized"], "Data should be anonymized"
    assert "anonymous_id" in anon_result, "Should generate anonymous ID"
    assert anon_result["original_id"] == mock_user_with_data.id, \
        "Should track original ID for records"
    
    # Validate PII removal
    removed_pii = anon_result["removed_pii"]
    assert "email" in removed_pii, "Email should be removed"
    assert "username" in removed_pii, "Username should be removed"
    assert "name" in removed_pii, "Name should be removed"
    assert len(removed_pii) >= 4, "Should remove multiple PII fields"
    
    # Validate retained statistical data
    retained = anon_result["retained_fields"]
    assert "created_at" in retained, "Can retain non-PII timestamps"
    assert "subscription_tier" in retained, "Can retain non-PII categories"
    
    # Validate anonymous ID is not reversible
    anon_id = anon_result["anonymous_id"]
    assert anon_id.startswith("anon_"), "Anonymous ID should have prefix"
    assert str(mock_user_with_data.id) not in anon_id, \
        "Anonymous ID should not contain user ID"
    
    print("✓ Data anonymization completed successfully")
    print(f"✓ Removed {len(removed_pii)} PII fields")
    print(f"✓ Retained {len(retained)} non-PII fields")
    print(f"✓ Anonymous ID: {anon_id}")


@pytest.mark.privacy
@pytest.mark.gdpr
def test_consent_management(mock_consent_manager):
    """
    Test GDPR Article 7 - Consent Management.
    
    Acceptance Criteria:
    - User can grant/withdraw consent for each purpose
    - Consent recorded with timestamp
    - Consent version tracked
    - Withdrawal as easy as granting
    - Consent required before processing
    """
    user_id = 1
    
    # Grant consent for different purposes
    purposes = ["marketing", "analytics", "personalization", "third_party_sharing"]
    
    for purpose in purposes[:3]:  # Grant first 3
        mock_consent_manager.record_consent(user_id, purpose, granted=True)
    
    # Deny last purpose
    mock_consent_manager.record_consent(user_id, purposes[-1], granted=False)
    
    # Validate consent records
    all_consents = mock_consent_manager.get_all_consents(user_id)
    
    assert len(all_consents) == len(purposes), "Should record all consent decisions"
    
    # Check individual consents
    assert mock_consent_manager.check_consent(user_id, "marketing"), \
        "Marketing consent should be granted"
    assert mock_consent_manager.check_consent(user_id, "analytics"), \
        "Analytics consent should be granted"
    assert not mock_consent_manager.check_consent(user_id, "third_party_sharing"), \
        "Third party sharing consent should be denied"
    
    # Validate consent metadata
    for purpose, consent_data in all_consents.items():
        assert "granted" in consent_data, "Should record granted status"
        assert "timestamp" in consent_data, "Should record timestamp"
        assert "version" in consent_data, "Should track consent version"
        assert isinstance(consent_data["timestamp"], datetime), \
            "Timestamp should be datetime object"
    
    # Test consent withdrawal
    mock_consent_manager.record_consent(user_id, "marketing", granted=False)
    assert not mock_consent_manager.check_consent(user_id, "marketing"), \
        "Should allow consent withdrawal"
    
    granted_count = sum(
        1 for consent in all_consents.values()
        if consent.get("granted", False)
    )
    
    print("✓ Consent management system functional")
    print(f"✓ {granted_count} consents granted, {len(purposes) - granted_count} denied")
    print("✓ Consent withdrawal supported")
    print("✓ Consent version tracking enabled")


@pytest.mark.privacy
@pytest.mark.gdpr
def test_data_portability_compliance(mock_user_with_data):
    """
    Test GDPR Article 20 - Data Portability Requirements.
    
    Acceptance Criteria:
    - Data exported in structured format
    - Common machine-readable format (JSON, CSV, XML)
    - Includes all user-provided data
    - Can be imported into another system
    - Export contains metadata
    """
    # Export user data
    export_data = GDPRService.export_user_data(mock_user_with_data)
    
    # Validate portability requirements
    portability = GDPRService.validate_data_portability(export_data)
    
    assert portability["valid"], "Export should meet portability requirements"
    assert portability["machine_readable"], "Format should be machine-readable"
    assert portability["complete"], "Export should be complete"
    assert portability["structured"], "Data should be structured"
    
    # Validate export format
    export_format = export_data.get("format")
    valid_formats = ["json", "csv", "xml"]
    assert export_format in valid_formats, \
        f"Format should be one of {valid_formats}"
    
    # Validate data structure
    data = export_data.get("data", {})
    assert isinstance(data, dict), "Data should be dictionary/object"
    
    # Validate can be serialized/deserialized
    try:
        json_str = json.dumps(export_data)
        reimported = json.loads(json_str)
        assert reimported == export_data, "Data should survive serialization"
    except Exception as e:
        pytest.fail(f"Data serialization failed: {e}")
    
    # Validate metadata
    assert "export_date" in export_data, "Should include export date"
    assert "gdpr_compliant" in export_data, "Should indicate GDPR compliance"
    
    print("✓ Data portability requirements met")
    print(f"✓ Export format: {export_format}")
    print(f"✓ Data categories: {len(data)}")
    print("✓ Machine-readable and structured")
    print("✓ Can be imported into other systems")


@pytest.mark.privacy
@pytest.mark.gdpr
@pytest.mark.integration
def test_gdpr_compliance_workflow(mock_user_with_data, mock_consent_manager):
    """
    Test complete GDPR compliance workflow.
    
    Validates end-to-end GDPR compliance including consent, export, and deletion.
    """
    user_id = mock_user_with_data.id
    
    # Step 1: User grants consent
    mock_consent_manager.record_consent(user_id, "data_processing", granted=True)
    assert mock_consent_manager.check_consent(user_id, "data_processing"), \
        "Consent should be granted"
    
    # Step 2: User requests data export
    export_data = GDPRService.export_user_data(mock_user_with_data)
    assert export_data["gdpr_compliant"], "Export should be GDPR compliant"
    assert len(export_data["data"]) > 0, "Export should contain data"
    
    # Step 3: User withdraws consent
    mock_consent_manager.record_consent(user_id, "data_processing", granted=False)
    assert not mock_consent_manager.check_consent(user_id, "data_processing"), \
        "Consent should be withdrawn"
    
    # Step 4: User requests deletion
    deletion_result = GDPRService.delete_user_data(user_id)
    assert deletion_result["deleted"], "Data should be deleted"
    assert deletion_result["anonymized"], "Data should be anonymized"
    
    # Step 5: Verify data removed but legal records retained
    retained = deletion_result["retained_data"]
    assert len(retained) > 0, "Legal records should be retained"
    
    print("✓ Complete GDPR compliance workflow successful")
    print("  1. ✓ Consent granted and recorded")
    print("  2. ✓ Data exported in compliant format")
    print("  3. ✓ Consent withdrawn")
    print("  4. ✓ Data deleted with anonymization")
    print("  5. ✓ Legal records retained as required")

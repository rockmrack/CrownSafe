"""Tests for core_infra/risk_ingestion_tasks.py"""
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime


class MockSafetyDataRecord:
    def __init__(self):
        self.gtin = "01234567890123"
        self.upc = "012345678905"
        self.product_name = "Test Product"
        self.brand = "Test Brand"
        self.manufacturer = "Test Manufacturer"
        self.model_number = "MODEL-123"
        self.source = "CPSC"
        self.source_id = "TEST-001"
        self.recall_date = datetime.utcnow()
        self.hazard_type = "choking"
        self.severity = "high"
        self.hazard_description = "Test hazard"
        self.url = "http://example.com"
        self.raw_data = {}


class TestRiskIngestionTasks(unittest.TestCase):
    
    def setUp(self):
        self.mock_db = Mock()
        self.mock_record = MockSafetyDataRecord()
    
    @patch('core_infra.risk_ingestion_tasks.ProductGoldenRecord')
    def test_find_or_create_product_from_record(self, mock_product_class):
        """Test finding or creating product from record"""
        from core_infra.risk_ingestion_tasks import _find_or_create_product_from_record
        mock_query = MagicMock()
        self.mock_db.query.return_value = mock_query
        mock_query.filter_by.return_value.first.return_value = None
        mock_query.filter.return_value.first.return_value = None
        result = _find_or_create_product_from_record(self.mock_record, self.mock_db)
        self.mock_db.add.assert_called()
    
    @patch('core_infra.risk_ingestion_tasks.SafetyIncident')
    def test_create_incident_from_record(self, mock_incident_class):
        """Test creating incident from record"""
        from core_infra.risk_ingestion_tasks import _create_incident_from_record
        mock_query = MagicMock()
        self.mock_db.query.return_value = mock_query
        mock_query.filter_by.return_value.first.return_value = None
        result = _create_incident_from_record(self.mock_record, "product-123", self.mock_db)
        self.mock_db.add.assert_called()
    
    @patch('core_infra.risk_ingestion_tasks.ProductDataSource')
    def test_update_product_data_source(self, mock_source_class):
        """Test updating product data source"""
        from core_infra.risk_ingestion_tasks import _update_product_data_source
        mock_query = MagicMock()
        self.mock_db.query.return_value = mock_query
        mock_query.filter_by.return_value.first.return_value = None
        _update_product_data_source("product-123", self.mock_record, self.mock_db)
        self.mock_db.add.assert_called()


if __name__ == '__main__':
    unittest.main()

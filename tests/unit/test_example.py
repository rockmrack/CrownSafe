"""
Example unit tests demonstrating proper test structure
This file shows best practices for unit testing in the BabyShield backend
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta


@pytest.mark.unit
class TestBasicFunctionality:
    """Basic unit tests for core functionality"""
    
    def test_string_manipulation(self):
        """Test basic string operations"""
        test_string = "BabyShield"
        assert test_string.lower() == "babyshield"
        assert test_string.upper() == "BABYSHIELD"
        assert len(test_string) == 10
    
    def test_list_operations(self):
        """Test list operations"""
        items = [1, 2, 3, 4, 5]
        assert sum(items) == 15
        assert max(items) == 5
        assert min(items) == 1
        assert len(items) == 5
    
    def test_dictionary_operations(self):
        """Test dictionary operations"""
        data = {"name": "BabyShield", "version": "1.0.0", "active": True}
        assert data["name"] == "BabyShield"
        assert data.get("missing", "default") == "default"
        assert "version" in data
        assert len(data) == 3


@pytest.mark.unit
class TestDateTimeOperations:
    """Test date and time related operations"""
    
    def test_date_calculations(self):
        """Test date arithmetic"""
        now = datetime.now()
        tomorrow = now + timedelta(days=1)
        yesterday = now - timedelta(days=1)
        
        assert tomorrow > now
        assert yesterday < now
        assert (tomorrow - yesterday).days == 2
    
    def test_date_formatting(self):
        """Test date formatting"""
        test_date = datetime(2024, 1, 15, 10, 30, 0)
        
        assert test_date.year == 2024
        assert test_date.month == 1
        assert test_date.day == 15
        assert test_date.strftime("%Y-%m-%d") == "2024-01-15"


@pytest.mark.unit
class TestMockingExamples:
    """Demonstrate mocking patterns"""
    
    @patch('requests.get')
    def test_api_call_mocking(self, mock_get):
        """Test mocking external API calls"""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success", "data": [1, 2, 3]}
        mock_get.return_value = mock_response
        
        # Simulate API call
        import requests
        response = requests.get("https://api.example.com/data")
        
        # Assertions
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        assert len(response.json()["data"]) == 3
        mock_get.assert_called_once_with("https://api.example.com/data")
    
    def test_function_mocking(self):
        """Test mocking internal functions"""
        mock_func = MagicMock(return_value=42)
        
        result = mock_func(10, 20)
        
        assert result == 42
        mock_func.assert_called_once_with(10, 20)


@pytest.mark.unit
class TestExceptionHandling:
    """Test exception handling patterns"""
    
    def test_exception_raised(self):
        """Test that exceptions are raised correctly"""
        with pytest.raises(ValueError) as exc_info:
            raise ValueError("Invalid value")
        
        assert str(exc_info.value) == "Invalid value"
    
    def test_exception_not_raised(self):
        """Test that valid operations don't raise exceptions"""
        try:
            result = 10 / 2
            assert result == 5
        except ZeroDivisionError:
            pytest.fail("Unexpected ZeroDivisionError")


@pytest.mark.unit
@pytest.mark.parametrize("input_val,expected", [
    (0, 1),  # 0! = 1 by mathematical definition
    (1, 1),
    (5, 120),  # 5! = 120
    (10, 3628800),  # 10! = 3628800
])
def test_factorial_parametrized(input_val, expected):
    """Test factorial calculation with multiple inputs"""
    import math
    assert math.factorial(input_val) == expected


@pytest.mark.unit
class TestFixtureUsage:
    """Demonstrate fixture usage"""
    
    @pytest.fixture
    def sample_data(self):
        """Provide sample data for tests"""
        return {
            "users": ["alice", "bob", "charlie"],
            "scores": [95, 87, 92],
            "active": True
        }
    
    def test_with_fixture(self, sample_data):
        """Test using a fixture"""
        assert len(sample_data["users"]) == 3
        assert sample_data["active"] is True
        assert sum(sample_data["scores"]) == 274
        assert max(sample_data["scores"]) == 95


# Performance test example (usually in tests/performance/)
@pytest.mark.performance
@pytest.mark.benchmark
def test_performance_example(benchmark):
    """Example performance benchmark"""
    def compute_sum():
        return sum(range(1000))
    
    result = benchmark(compute_sum)
    assert result == 499500


# Skip example for incomplete tests
@pytest.mark.skip(reason="Feature not yet implemented")
def test_future_feature():
    """Test for a feature that's not yet implemented"""
    # This test will be skipped
    assert False, "This should not run"


# Conditional skip example
@pytest.mark.skipif(
    not pytest.importorskip("pandas", reason="pandas not installed"),
    reason="Requires pandas"
)
def test_pandas_operations():
    """Test that requires pandas (skipped if not installed)"""
    import pandas as pd
    df = pd.DataFrame({"a": [1, 2, 3]})
    assert len(df) == 3

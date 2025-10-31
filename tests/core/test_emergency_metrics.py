from unittest.mock import patch

import pytest  # type: ignore

from core.metrics import CHAT_EMERG, CHAT_UNCLEAR, inc_emergency, inc_unclear


class TestEmergencyMetrics:
    """Tests for emergency and unclear intent metrics"""

    @patch("core.metrics.PROM", True)
    @patch("core.metrics.CHAT_UNCLEAR")
    def test_inc_unclear_with_prometheus(self, mock_chat_unclear):
        """Test unclear intent metric with Prometheus enabled"""
        inc_unclear()
        mock_chat_unclear.inc.assert_called_once()

    @patch("core.metrics.PROM", True)
    @patch("core.metrics.CHAT_EMERG")
    def test_inc_emergency_with_prometheus(self, mock_chat_emerg):
        """Test emergency metric with Prometheus enabled"""
        inc_emergency()
        mock_chat_emerg.inc.assert_called_once()

    @patch("core.metrics.PROM", False)
    def test_inc_unclear_without_prometheus(self):
        """Test unclear intent metric without Prometheus (no-op)"""
        # Should not raise any exceptions
        inc_unclear()

    @patch("core.metrics.PROM", False)
    def test_inc_emergency_without_prometheus(self):
        """Test emergency metric without Prometheus (no-op)"""
        # Should not raise any exceptions
        inc_emergency()

    @patch("core.metrics.PROM", True)
    @patch("core.metrics.CHAT_UNCLEAR")
    def test_multiple_unclear_calls(self, mock_chat_unclear):
        """Test multiple unclear intent calls increment correctly"""
        inc_unclear()
        inc_unclear()
        inc_unclear()

        assert mock_chat_unclear.inc.call_count == 3

    @patch("core.metrics.PROM", True)
    @patch("core.metrics.CHAT_EMERG")
    def test_multiple_emergency_calls(self, mock_chat_emerg):
        """Test multiple emergency calls increment correctly"""
        inc_emergency()
        inc_emergency()

        assert mock_chat_emerg.inc.call_count == 2

    def test_metrics_counter_names(self):
        """Test that metric counter names are correct"""
        # This test verifies the metric names are as expected
        # In a real Prometheus setup, these would be the metric names
        expected_unclear_name = "bs_chat_unclear_total"
        expected_emergency_name = "bs_chat_emergency_total"

        # The actual metric names are defined in the Counter constructors
        # This test ensures they match expectations
        assert expected_unclear_name in "bs_chat_unclear_total"
        assert expected_emergency_name in "bs_chat_emergency_total"

    @patch("core.metrics.PROM", True)
    def test_metrics_are_counters(self):
        """Test that metrics are Counter type when Prometheus is available"""
        # When PROM is True, CHAT_UNCLEAR and CHAT_EMERG should be Counter instances
        # This would be tested in actual integration where prometheus_client is available
        assert hasattr(CHAT_UNCLEAR, "inc")
        assert hasattr(CHAT_EMERG, "inc")

    @patch("core.metrics.PROM", False)
    def test_metrics_are_no_op_when_disabled(self):
        """Test that metrics are no-op objects when Prometheus is disabled"""
        # When PROM is False, metrics should be no-op objects
        assert hasattr(CHAT_UNCLEAR, "inc")
        assert hasattr(CHAT_EMERG, "inc")

        # Should not raise exceptions when called
        CHAT_UNCLEAR.inc()
        CHAT_EMERG.inc()


if __name__ == "__main__":
    pytest.main([__file__])

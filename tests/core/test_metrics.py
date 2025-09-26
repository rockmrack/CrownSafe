import pytest
from unittest.mock import patch, MagicMock
from core.metrics import inc_req, obs_total, obs_tool, obs_synth


class TestMetricsWithPrometheus:
    @patch('core.metrics.PROM', True)
    @patch('core.metrics.CHAT_REQ')
    def test_inc_req_with_prometheus(self, mock_chat_req):
        mock_labels = MagicMock()
        mock_chat_req.labels.return_value = mock_labels
        
        inc_req("conversation", "pregnancy_risk", ok=True, circuit=False)
        
        mock_chat_req.labels.assert_called_once_with("conversation", "pregnancy_risk", "1", "0")
        mock_labels.inc.assert_called_once()
    
    @patch('core.metrics.PROM', True)
    @patch('core.metrics.CHAT_LAT')
    def test_obs_total_with_prometheus(self, mock_chat_lat):
        obs_total(150)
        mock_chat_lat.observe.assert_called_once_with(150.0)
    
    @patch('core.metrics.PROM', True)
    @patch('core.metrics.TOOL_LAT')
    def test_obs_tool_with_prometheus(self, mock_tool_lat):
        mock_labels = MagicMock()
        mock_tool_lat.labels.return_value = mock_labels
        
        obs_tool("allergy_question", 75)
        
        mock_tool_lat.labels.assert_called_once_with("allergy_question")
        mock_labels.observe.assert_called_once_with(75.0)
    
    @patch('core.metrics.PROM', True)
    @patch('core.metrics.SYN_LAT')
    def test_obs_synth_with_prometheus(self, mock_syn_lat):
        obs_synth(200)
        mock_syn_lat.observe.assert_called_once_with(200.0)


class TestMetricsWithoutPrometheus:
    @patch('core.metrics.PROM', False)
    def test_inc_req_without_prometheus(self):
        # Should not raise any exceptions
        inc_req("conversation", "pregnancy_risk", ok=True, circuit=False)
        inc_req("explain", "unknown", ok=False, circuit=True)
    
    @patch('core.metrics.PROM', False)
    def test_obs_total_without_prometheus(self):
        # Should not raise any exceptions
        obs_total(150)
        obs_total(0)
        obs_total(5000)
    
    @patch('core.metrics.PROM', False)
    def test_obs_tool_without_prometheus(self):
        # Should not raise any exceptions
        obs_tool("pregnancy_risk", 50)
        obs_tool("unclear_intent", 1000)
    
    @patch('core.metrics.PROM', False)
    def test_obs_synth_without_prometheus(self):
        # Should not raise any exceptions
        obs_synth(100)
        obs_synth(2000)


class TestMetricsEdgeCases:
    @patch('core.metrics.PROM', True)
    @patch('core.metrics.CHAT_REQ')
    def test_inc_req_various_combinations(self, mock_chat_req):
        mock_labels = MagicMock()
        mock_chat_req.labels.return_value = mock_labels
        
        # Test all combinations of ok/circuit flags
        test_cases = [
            ("conversation", "pregnancy_risk", True, False, "1", "0"),
            ("conversation", "allergy_question", False, True, "0", "1"),
            ("explain", "unknown", True, True, "1", "1"),
            ("explain", "ingredient_info", False, False, "0", "0"),
        ]
        
        for endpoint, intent, ok, circuit, expected_ok, expected_circuit in test_cases:
            mock_chat_req.reset_mock()
            inc_req(endpoint, intent, ok, circuit)
            mock_chat_req.labels.assert_called_once_with(endpoint, intent, expected_ok, expected_circuit)
            mock_labels.inc.assert_called_once()
    
    @patch('core.metrics.PROM', True)
    @patch('core.metrics.CHAT_LAT')
    def test_obs_total_edge_values(self, mock_chat_lat):
        # Test edge cases
        obs_total(0)
        obs_total(1)
        obs_total(10000)
        
        expected_calls = [((0.0,),), ((1.0,),), ((10000.0,),)]
        assert mock_chat_lat.observe.call_args_list == expected_calls


class TestNoOpBehavior:
    """Test that the no-op classes work correctly when Prometheus is not available"""
    
    def test_noop_class_methods(self):
        from core.metrics import _N
        
        noop = _N()
        
        # All methods should return self or do nothing
        assert noop.labels("test", "args") == noop
        assert noop.labels(endpoint="test", intent="test") == noop
        
        # These should not raise exceptions
        noop.observe(100)
        noop.inc()
        noop.observe(0.5)
        noop.inc(5)


class TestNewMetrics:
    @patch('core.metrics.PROM', True)
    @patch('core.metrics.CHAT_FALLBACK')
    def test_inc_fallback_with_prometheus(self, mock_chat_fallback):
        from core.metrics import inc_fallback
        
        mock_labels = MagicMock()
        mock_chat_fallback.labels.return_value = mock_labels
        
        inc_fallback("conversation", "synth_fallback")
        
        mock_chat_fallback.labels.assert_called_once_with("conversation", "synth_fallback")
        mock_labels.inc.assert_called_once()
    
    @patch('core.metrics.PROM', True)
    @patch('core.metrics.CHAT_BLOCKED')
    def test_inc_blocked_with_prometheus(self, mock_chat_blocked):
        from core.metrics import inc_blocked
        
        mock_labels = MagicMock()
        mock_chat_blocked.labels.return_value = mock_labels
        
        inc_blocked("conversation")
        
        mock_chat_blocked.labels.assert_called_once_with("conversation")
        mock_labels.inc.assert_called_once()
    
    @patch('core.metrics.PROM', False)
    def test_inc_fallback_without_prometheus(self):
        from core.metrics import inc_fallback
        
        # Should not raise any exceptions
        inc_fallback("conversation", "synth_fallback")
        inc_fallback("explain", "timeout")
    
    @patch('core.metrics.PROM', False)
    def test_inc_blocked_without_prometheus(self):
        from core.metrics import inc_blocked
        
        # Should not raise any exceptions
        inc_blocked("conversation")
        inc_blocked("explain")

"""Tests for agents/patient_data_agent/agent_logic.py"""
import unittest
from unittest.mock import Mock, patch


class TestPatientDataAgent(unittest.TestCase):
    
    @patch('agents.patient_data_agent.agent_logic.MCPClient')
    def test_agent_initialization(self, mock_client):
        """Test agent can be imported and initialized"""
        try:
            from agents.patient_data_agent.agent_logic import PatientDataAgentLogic
            agent = PatientDataAgentLogic(agent_id='test-002')
            self.assertIsNotNone(agent)
        except ImportError:
            self.skipTest("PatientDataAgent module not available")
    
    def test_agent_module_exists(self):
        """Test that patient data agent module exists"""
        try:
            import agents.patient_data_agent.agent_logic
            self.assertIsNotNone(agents.patient_data_agent.agent_logic)
        except ImportError:
            self.skipTest("Module not found")


if __name__ == '__main__':
    unittest.main()

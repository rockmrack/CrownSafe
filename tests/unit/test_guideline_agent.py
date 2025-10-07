"""
Unit tests for agents/guideline_agent/agent_logic.py
Tests guideline agent logic for clinical guidelines ingestion and querying
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock, mock_open
from datetime import datetime
from agents.guideline_agent.agent_logic import (
    CAPABILITIES,
    GuidelineAgentLogic
)


class TestGuidelineAgentLogic:
    """Test GuidelineAgentLogic functionality"""
    
    def test_capabilities_constant(self):
        """Test CAPABILITIES constant"""
        expected_capabilities = [
            "query_guidelines",
            "retrieve_guidelines", 
            "ingest_guidelines",
            "search_guidelines"
        ]
        
        assert CAPABILITIES == expected_capabilities
    
    def test_init_default_logger(self):
        """Test GuidelineAgentLogic initialization with default logger"""
        agent = GuidelineAgentLogic("test_agent")
        
        assert agent.agent_id == "test_agent"
        assert agent.logger is not None
        assert agent.memory_manager is None  # Should be None due to import failure
    
    def test_init_custom_logger(self):
        """Test GuidelineAgentLogic initialization with custom logger"""
        mock_logger = Mock()
        agent = GuidelineAgentLogic("test_agent", logger_instance=mock_logger)
        
        assert agent.agent_id == "test_agent"
        assert agent.logger == mock_logger
    
    @pytest.mark.parametrize(
        "memory_manager_available,expected_is_none",
        [
            (True, False),   # EnhancedMemoryManager import succeeds
            (False, True),  # EnhancedMemoryManager import fails
        ]
    )
    def test_init_with_memory_manager_import(
        self, monkeypatch, memory_manager_available, expected_is_none
    ):
        """Test GuidelineAgentLogic initialization with/without EnhancedMemoryManager available"""
        from agents.guideline_agent import agent_logic
        def import_side_effect(name, globals=None, locals=None, fromlist=(), level=0):
            if name == "agents.guideline_agent.enhanced_memory_manager":
                if memory_manager_available:
                    class MockEnhancedMemoryManager:
                        def __init__(self, *args, **kwargs):
                            pass
                    return type("MockModule", (), {"EnhancedMemoryManager": MockEnhancedMemoryManager})()
                else:
                    raise ImportError("No module named 'enhanced_memory_manager'")
            return __import__(name, globals, locals, fromlist, level)
        monkeypatch.setattr("builtins.__import__", import_side_effect)
        agent = agent_logic.GuidelineAgentLogic("test_agent")
        if expected_is_none:
            assert agent.memory_manager is None
        else:
            assert agent.memory_manager is not None
    def test_init_guidelines_config(self):
        """Test guidelines configuration"""
        agent = GuidelineAgentLogic("test_agent")
        
        assert "AHA_HF_2022" in agent.guidelines_config
        assert "ADA_DIABETES_2023" in agent.guidelines_config
        
        # Check structure of a guideline config
        aha_config = agent.guidelines_config["AHA_HF_2022"]
        assert "url" in aha_config
        assert "local_path" in aha_config
        assert "name" in aha_config
        assert "focus" in aha_config
        assert isinstance(aha_config["focus"], list)
    
    def test_get_capabilities(self):
        """Test get_capabilities method"""
        agent = GuidelineAgentLogic("test_agent")
        
        capabilities = agent.get_capabilities()
        
        assert capabilities == CAPABILITIES
    
    def test_get_agent_info(self):
        """Test get_agent_info method"""
        agent = GuidelineAgentLogic("test_agent")
        
        info = agent.get_agent_info()
        
        assert info["agent_id"] == "test_agent"
        assert info["capabilities"] == CAPABILITIES
        assert "guidelines_config" in info
        assert len(info["guidelines_config"]) > 0
    
    @patch('agents.guideline_agent.agent_logic.requests.get')
    def test_fetch_guideline_from_url_success(self, mock_get):
        """Test fetch_guideline_from_url with success"""
        agent = GuidelineAgentLogic("test_agent")
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"PDF content"
        mock_get.return_value = mock_response
        
        url = "https://example.com/guideline.pdf"
        content = agent.fetch_guideline_from_url(url)
        
        assert content == b"PDF content"
        mock_get.assert_called_once_with(url, timeout=30)
    
    @patch('agents.guideline_agent.agent_logic.requests.get')
    def test_fetch_guideline_from_url_failure(self, mock_get):
        """Test fetch_guideline_from_url with failure"""
        agent = GuidelineAgentLogic("test_agent")
        
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        url = "https://example.com/notfound.pdf"
        content = agent.fetch_guideline_from_url(url)
        
        assert content is None
        mock_get.assert_called_once_with(url, timeout=30)
    
    @patch('agents.guideline_agent.agent_logic.requests.get')
    def test_fetch_guideline_from_url_exception(self, mock_get):
        """Test fetch_guideline_from_url with exception"""
        agent = GuidelineAgentLogic("test_agent")
        
        mock_get.side_effect = Exception("Network error")
        
        url = "https://example.com/guideline.pdf"
        content = agent.fetch_guideline_from_url(url)
        
        assert content is None
    
    @patch('builtins.open', new_callable=mock_open, read_data=b"PDF content")
    def test_fetch_guideline_from_file_success(self, mock_file):
        """Test fetch_guideline_from_file with success"""
        agent = GuidelineAgentLogic("test_agent")
        
        file_path = "data/guidelines/test.pdf"
        content = agent.fetch_guideline_from_file(file_path)
        
        assert content == b"PDF content"
        mock_file.assert_called_once_with(file_path, 'rb')
    
    @patch('builtins.open', side_effect=FileNotFoundError)
    def test_fetch_guideline_from_file_not_found(self, mock_file):
        """Test fetch_guideline_from_file with file not found"""
        agent = GuidelineAgentLogic("test_agent")
        
        file_path = "data/guidelines/nonexistent.pdf"
        content = agent.fetch_guideline_from_file(file_path)
        
        assert content is None
    
    @patch('builtins.open', side_effect=PermissionError)
    def test_fetch_guideline_from_file_permission_error(self, mock_file):
        """Test fetch_guideline_from_file with permission error"""
        agent = GuidelineAgentLogic("test_agent")
        
        file_path = "data/guidelines/restricted.pdf"
        content = agent.fetch_guideline_from_file(file_path)
        
        assert content is None
    
    @patch('agents.guideline_agent.agent_logic.fitz')
    def test_extract_text_from_pdf_success(self, mock_fitz):
        """Test extract_text_from_pdf with success"""
        agent = GuidelineAgentLogic("test_agent")
        
        # Mock PDF document
        mock_doc = Mock()
        mock_page = Mock()
        mock_page.get_text.return_value = "Sample PDF text content"
        mock_doc.__iter__.return_value = [mock_page]
        mock_doc.__len__.return_value = 1
        mock_fitz.open.return_value = mock_doc
        
        pdf_content = b"PDF bytes"
        text = agent.extract_text_from_pdf(pdf_content)
        
        assert text == "Sample PDF text content"
        mock_fitz.open.assert_called_once()
        mock_doc.close.assert_called_once()
    
    @patch('agents.guideline_agent.agent_logic.fitz')
    def test_extract_text_from_pdf_exception(self, mock_fitz):
        """Test extract_text_from_pdf with exception"""
        agent = GuidelineAgentLogic("test_agent")
        
        mock_fitz.open.side_effect = Exception("PDF parsing error")
        
        pdf_content = b"Invalid PDF bytes"
        text = agent.extract_text_from_pdf(pdf_content)
        
        assert text is None
    
    def test_search_guidelines_by_keywords(self):
        """Test search_guidelines_by_keywords method"""
        agent = GuidelineAgentLogic("test_agent")
        
        # Mock guidelines data
        agent.guidelines_data = {
            "guideline1": {
                "text": "This guideline discusses heart failure treatment with SGLT2 inhibitors",
                "metadata": {"title": "Heart Failure Guidelines"}
            },
            "guideline2": {
                "text": "Diabetes management recommendations for type 2 diabetes",
                "metadata": {"title": "Diabetes Guidelines"}
            }
        }
        
        keywords = ["heart failure", "SGLT2"]
        results = agent.search_guidelines_by_keywords(keywords)
        
        assert len(results) > 0
        # Should find guideline1 but not guideline2
        assert any("heart failure" in result["text"].lower() for result in results)
    
    def test_search_guidelines_by_keywords_no_data(self):
        """Test search_guidelines_by_keywords with no guidelines data"""
        agent = GuidelineAgentLogic("test_agent")
        agent.guidelines_data = {}
        
        keywords = ["test"]
        results = agent.search_guidelines_by_keywords(keywords)
        
        assert results == []
    
    def test_search_guidelines_by_keywords_empty_keywords(self):
        """Test search_guidelines_by_keywords with empty keywords"""
        agent = GuidelineAgentLogic("test_agent")
        
        keywords = []
        results = agent.search_guidelines_by_keywords(keywords)
        
        assert results == []
    
    def test_process_message_query_guidelines(self):
        """Test process_message with query_guidelines task"""
        agent = GuidelineAgentLogic("test_agent")
        
        # Mock guidelines data
        agent.guidelines_data = {
            "test_guideline": {
                "text": "Test guideline content",
                "metadata": {"title": "Test Guideline"}
            }
        }
        
        message_data = {
            "mcp_header": {
                "message_type": "TASK_ASSIGN",
                "sender_id": "test_sender"
            },
            "payload": {
                "task_id": "task_123",
                "workflow_id": "workflow_456",
                "parameters": {
                    "task_type": "query_guidelines",
                    "keywords": ["test"]
                }
            }
        }
        
        result = agent.process_message(message_data, None)
        
        assert result is not None
        assert result["message_type"] == "TASK_COMPLETE"
        assert result["payload"]["task_id"] == "task_123"
        assert result["payload"]["workflow_id"] == "workflow_456"
    
    def test_process_message_ingest_guidelines(self):
        """Test process_message with ingest_guidelines task"""
        agent = GuidelineAgentLogic("test_agent")
        
        message_data = {
            "mcp_header": {
                "message_type": "TASK_ASSIGN",
                "sender_id": "test_sender"
            },
            "payload": {
                "task_id": "task_123",
                "workflow_id": "workflow_456",
                "parameters": {
                    "task_type": "ingest_guidelines",
                    "guideline_id": "AHA_HF_2022"
                }
            }
        }
        
        with patch.object(agent, 'ingest_guideline') as mock_ingest:
            mock_ingest.return_value = {"status": "success"}
            
            result = agent.process_message(message_data, None)
            
            assert result is not None
            assert result["message_type"] == "TASK_COMPLETE"
            mock_ingest.assert_called_once_with("AHA_HF_2022")
    
    def test_process_message_unknown_task(self):
        """Test process_message with unknown task type"""
        agent = GuidelineAgentLogic("test_agent")
        
        message_data = {
            "mcp_header": {
                "message_type": "TASK_ASSIGN",
                "sender_id": "test_sender"
            },
            "payload": {
                "task_id": "task_123",
                "workflow_id": "workflow_456",
                "parameters": {
                    "task_type": "unknown_task"
                }
            }
        }
        
        result = agent.process_message(message_data, None)
        
        assert result is not None
        assert result["message_type"] == "TASK_FAIL"
        assert "Unknown task type" in result["payload"]["error_message"]
    
    def test_process_message_invalid_message(self):
        """Test process_message with invalid message structure"""
        agent = GuidelineAgentLogic("test_agent")
        
        message_data = {
            "invalid": "structure"
        }
        
        result = agent.process_message(message_data, None)
        
        assert result is None
    
    def test_process_message_pong(self):
        """Test process_message with PONG message"""
        agent = GuidelineAgentLogic("test_agent")
        
        message_data = {
            "mcp_header": {
                "message_type": "PONG",
                "sender_id": "test_sender"
            },
            "payload": {}
        }
        
        result = agent.process_message(message_data, None)
        
        assert result is None
    
    def test_process_message_discovery_ack(self):
        """Test process_message with DISCOVERY_ACK message"""
        agent = GuidelineAgentLogic("test_agent")
        
        message_data = {
            "mcp_header": {
                "message_type": "DISCOVERY_ACK",
                "sender_id": "test_sender"
            },
            "payload": {}
        }
        
        result = agent.process_message(message_data, None)
        
        assert result is None
    
    def test_process_message_unknown_message_type(self):
        """Test process_message with unknown message type"""
        agent = GuidelineAgentLogic("test_agent")
        
        message_data = {
            "mcp_header": {
                "message_type": "UNKNOWN_TYPE",
                "sender_id": "test_sender"
            },
            "payload": {}
        }
        
        result = agent.process_message(message_data, None)
        
        assert result is None
    
    @patch.object(GuidelineAgentLogic, 'fetch_guideline_from_url')
    @patch.object(GuidelineAgentLogic, 'fetch_guideline_from_file')
    @patch.object(GuidelineAgentLogic, 'extract_text_from_pdf')
    def test_ingest_guideline_success(self, mock_extract, mock_fetch_file, mock_fetch_url):
        """Test ingest_guideline with success"""
        agent = GuidelineAgentLogic("test_agent")
        
        # Mock successful URL fetch
        mock_fetch_url.return_value = b"PDF content"
        mock_extract.return_value = "Extracted text content"
        
        guideline_id = "AHA_HF_2022"
        result = agent.ingest_guideline(guideline_id)
        
        assert result["status"] == "success"
        assert result["guideline_id"] == guideline_id
        assert "text" in result
        assert "metadata" in result
        assert "ingestion_time" in result
        
        mock_fetch_url.assert_called_once()
        mock_extract.assert_called_once_with(b"PDF content")
    
    @patch.object(GuidelineAgentLogic, 'fetch_guideline_from_url')
    @patch.object(GuidelineAgentLogic, 'fetch_guideline_from_file')
    def test_ingest_guideline_file_fallback(self, mock_fetch_file, mock_fetch_url):
        """Test ingest_guideline with file fallback"""
        agent = GuidelineAgentLogic("test_agent")
        
        # Mock URL fetch failure, file fetch success
        mock_fetch_url.return_value = None
        mock_fetch_file.return_value = b"PDF content from file"
        
        with patch.object(agent, 'extract_text_from_pdf') as mock_extract:
            mock_extract.return_value = "Extracted text content"
            
            guideline_id = "AHA_HF_2022"
            result = agent.ingest_guideline(guideline_id)
            
            assert result["status"] == "success"
            mock_fetch_url.assert_called_once()
            mock_fetch_file.assert_called_once()
    
    def test_ingest_guideline_not_found(self):
        """Test ingest_guideline with guideline not found"""
        agent = GuidelineAgentLogic("test_agent")
        
        guideline_id = "NONEXISTENT_GUIDELINE"
        result = agent.ingest_guideline(guideline_id)
        
        assert result["status"] == "error"
        assert "not found" in result["error"].lower()
    
    @patch.object(GuidelineAgentLogic, 'fetch_guideline_from_url')
    @patch.object(GuidelineAgentLogic, 'fetch_guideline_from_file')
    def test_ingest_guideline_fetch_failure(self, mock_fetch_file, mock_fetch_url):
        """Test ingest_guideline with fetch failure"""
        agent = GuidelineAgentLogic("test_agent")
        
        # Mock both URL and file fetch failure
        mock_fetch_url.return_value = None
        mock_fetch_file.return_value = None
        
        guideline_id = "AHA_HF_2022"
        result = agent.ingest_guideline(guideline_id)
        
        assert result["status"] == "error"
        assert "Could not fetch" in result["error"]
    
    @patch.object(GuidelineAgentLogic, 'fetch_guideline_from_url')
    @patch.object(GuidelineAgentLogic, 'extract_text_from_pdf')
    def test_ingest_guideline_extraction_failure(self, mock_extract, mock_fetch_url):
        """Test ingest_guideline with text extraction failure"""
        agent = GuidelineAgentLogic("test_agent")
        
        mock_fetch_url.return_value = b"PDF content"
        mock_extract.return_value = None
        
        guideline_id = "AHA_HF_2022"
        result = agent.ingest_guideline(guideline_id)
        
        assert result["status"] == "error"
        assert "Could not extract text" in result["error"]
    
    def test_get_guideline_summary(self):
        """Test get_guideline_summary method"""
        agent = GuidelineAgentLogic("test_agent")
        
        # Mock guidelines data
        agent.guidelines_data = {
            "test_guideline": {
                "text": "This is a test guideline with important information about treatment protocols.",
                "metadata": {
                    "title": "Test Treatment Guideline",
                    "source": "Test Agency",
                    "date": "2023-01-01"
                }
            }
        }
        
        guideline_id = "test_guideline"
        summary = agent.get_guideline_summary(guideline_id)
        
        assert summary["guideline_id"] == guideline_id
        assert "summary" in summary
        assert "key_points" in summary
        assert "metadata" in summary
        assert summary["metadata"]["title"] == "Test Treatment Guideline"
    
    def test_get_guideline_summary_not_found(self):
        """Test get_guideline_summary with guideline not found"""
        agent = GuidelineAgentLogic("test_agent")
        agent.guidelines_data = {}
        
        guideline_id = "nonexistent_guideline"
        summary = agent.get_guideline_summary(guideline_id)
        
        assert summary["guideline_id"] == guideline_id
        assert summary["status"] == "error"
        assert "not found" in summary["error"].lower()
    
    def test_list_available_guidelines(self):
        """Test list_available_guidelines method"""
        agent = GuidelineAgentLogic("test_agent")
        
        # Mock guidelines data
        agent.guidelines_data = {
            "guideline1": {
                "metadata": {"title": "Guideline 1", "source": "Agency 1"}
            },
            "guideline2": {
                "metadata": {"title": "Guideline 2", "source": "Agency 2"}
            }
        }
        
        guidelines = agent.list_available_guidelines()
        
        assert len(guidelines) == 2
        assert guidelines[0]["guideline_id"] == "guideline1"
        assert guidelines[0]["title"] == "Guideline 1"
        assert guidelines[1]["guideline_id"] == "guideline2"
        assert guidelines[1]["title"] == "Guideline 2"
    
    def test_list_available_guidelines_empty(self):
        """Test list_available_guidelines with no guidelines"""
        agent = GuidelineAgentLogic("test_agent")
        agent.guidelines_data = {}
        
        guidelines = agent.list_available_guidelines()
        
        assert guidelines == []
    
    def test_validate_message_structure_valid(self):
        """Test _validate_message_structure with valid message"""
        agent = GuidelineAgentLogic("test_agent")
        
        message_data = {
            "mcp_header": {
                "message_type": "TASK_ASSIGN",
                "sender_id": "test_sender"
            },
            "payload": {
                "task_id": "task_123",
                "parameters": {}
            }
        }
        
        is_valid, error = agent._validate_message_structure(message_data)
        
        assert is_valid is True
        assert error is None
    
    def test_validate_message_structure_missing_header(self):
        """Test _validate_message_structure with missing header"""
        agent = GuidelineAgentLogic("test_agent")
        
        message_data = {
            "payload": {
                "task_id": "task_123"
            }
        }
        
        is_valid, error = agent._validate_message_structure(message_data)
        
        assert is_valid is False
        assert "mcp_header" in error
    
    def test_validate_message_structure_missing_payload(self):
        """Test _validate_message_structure with missing payload"""
        agent = GuidelineAgentLogic("test_agent")
        
        message_data = {
            "mcp_header": {
                "message_type": "TASK_ASSIGN"
            }
        }
        
        is_valid, error = agent._validate_message_structure(message_data)
        
        assert is_valid is False
        assert "payload" in error
    
    def test_validate_message_structure_missing_task_id(self):
        """Test _validate_message_structure with missing task_id"""
        agent = GuidelineAgentLogic("test_agent")
        
        message_data = {
            "mcp_header": {
                "message_type": "TASK_ASSIGN"
            },
            "payload": {
                "parameters": {}
            }
        }
        
        is_valid, error = agent._validate_message_structure(message_data)
        
        assert is_valid is False
        assert "task_id" in error


if __name__ == "__main__":
    pytest.main([__file__])

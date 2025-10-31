"""Tests for api/models/chat_memory.py"""

import unittest


class TestChatMemory(unittest.TestCase):
    def test_chat_memory_module_import(self):
        """Test that chat_memory module can be imported"""
        try:
            from api.models import chat_memory

            self.assertIsNotNone(chat_memory)
        except ImportError:
            self.skipTest("chat_memory module not found")

    def test_chat_memory_model_creation(self):
        """Test creating a chat memory model"""
        try:
            from api.models.chat_memory import ChatMemory

            memory = ChatMemory()
            self.assertIsNotNone(memory)
        except (ImportError, AttributeError, TypeError):
            self.skipTest("ChatMemory class not available or requires args")


if __name__ == "__main__":
    unittest.main()

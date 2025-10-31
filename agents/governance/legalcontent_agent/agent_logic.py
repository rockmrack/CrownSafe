# agents/governance/legalcontent_agent/agent_logic.py
"""LegalContentAgentLogic v1.1

Reads full text of legal documents (e.g., TOS, Privacy Policy) from disk
and returns them as part of the agent result payload.
"""

import asyncio
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# Path to directory containing legal documents (data/legal)
LEGAL_DOCS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "legal"))


class LegalContentAgentLogic:
    def __init__(self, agent_id: str, logger_instance: logging.Logger | None = None):
        self.agent_id = agent_id
        self.logger = logger_instance or logger
        self.logger.info(f"LegalContentAgentLogic initialized. Document path: {LEGAL_DOCS_PATH}")

    async def get_document(self, document_name: str) -> str | None:
        # Sanitize filename to prevent path traversal
        safe_name = os.path.basename(document_name)
        file_path = os.path.join(LEGAL_DOCS_PATH, safe_name)

        self.logger.info(f"Attempting to read legal document from: {file_path}")
        if not os.path.exists(file_path):
            self.logger.error(f"Legal document not found: {file_path}")
            return None

        try:
            # Simulate a small I/O delay
            await asyncio.sleep(0.01)
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.logger.info(f"Successfully read document: {safe_name}")
            return content

        except Exception as e:
            self.logger.error(f"Failed to read document {safe_name}: {e}", exc_info=True)
            return None

    async def process_task(self, inputs: dict[str, Any]) -> dict[str, Any]:
        self.logger.info(f"Received task with inputs: {inputs}")

        document_name = inputs.get("document_name")
        if not document_name:
            return {"status": "FAILED", "error": "document_name is required."}

        content = await self.get_document(document_name)
        if content is None:
            return {
                "status": "FAILED",
                "error": f"Could not retrieve document: {document_name}",
            }

        if not content.strip():
            return {"status": "FAILED", "error": f"Document {document_name} is empty."}

        return {
            "status": "COMPLETED",
            "result": {"document_name": document_name, "content": content},
        }

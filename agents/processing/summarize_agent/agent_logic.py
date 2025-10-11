# C:\Users\rossd\Downloads\RossNetAgents\agents\processing\summarize_agent\agent_logic.py
# Step 109: Implement Real Summarization Logic using Langchain and OpenAI.

import logging
import os
import json  # For potentially handling complex input structures if needed
from typing import Dict, Any, List, Optional

from dotenv import load_dotenv

# Langchain and OpenAI imports
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain.chains.summarize import load_summarize_chain  # For summarization
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import (
    Document,
)  # For creating Document objects for Langchain chains

# Load environment variables from .env file at the project root
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
dotenv_path = os.path.join(project_root, ".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    if os.path.exists(".env"):  # Fallback
        load_dotenv(".env")
    else:
        print("WARNING (SummarizeLogic): .env file not found. OPENAI_API_KEY might be missing.")


class SummarizeAgentLogic:
    def __init__(self, agent_id: str, version: str, logger: logging.Logger):
        self.agent_id = agent_id
        self.version = version
        self.logger = logger
        self.llm = None
        self.summarize_chain = None

        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            self.logger.error("OPENAI_API_KEY not found. Real summarization will fail.")
        else:
            try:
                self.llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.0, api_key=openai_api_key)
                self.logger.info("ChatOpenAI LLM initialized successfully (gpt-3.5-turbo) for SummarizeAgent.")

                # Using Langchain's load_summarize_chain (map_reduce is good for multiple documents)
                # You can also try "stuff" or "refine" chain types.
                self.summarize_chain = load_summarize_chain(self.llm, chain_type="map_reduce")
                self.logger.info("Langchain summarization chain (map_reduce) initialized.")

            except Exception as e:
                self.logger.error(
                    f"Error initializing Langchain/OpenAI components for SummarizeAgent: {e}",
                    exc_info=True,
                )
                self.llm = None
                self.summarize_chain = None

        self.logger.info(
            f"SummarizeAgentLogic initialized. Agent ID: {self.agent_id}, Version: {self.version}. "
            f"LLM Ready: {'Yes' if self.llm and self.summarize_chain else 'No'}. (Step 109)"
        )

    def get_capabilities(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "summarize_text",
                "description": "Summarizes provided text, typically research articles.",
                "parameters": {
                    "text_to_summarize": "object | string (Expected: {'articles': [{'title': '...', 'abstract': '...'}, ...]} or a single string)",
                    "max_length": "int (optional, desired summary length - currently not strictly enforced by this stub)",
                },
            }
        ]

    async def _generate_summary_with_llm(self, text_content: str) -> Optional[str]:
        if not self.summarize_chain:
            self.logger.error("Summarization chain not initialized. Cannot generate summary.")
            return "Error: Summarization service not available."

        try:
            self.logger.info(f"Generating summary for text content (length: {len(text_content)} chars) using LLM.")

            # Split the text into manageable documents for the map_reduce chain
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=10000, chunk_overlap=200
            )  # Adjust chunk_size as needed
            docs = [Document(page_content=chunk) for chunk in text_splitter.split_text(text_content)]

            if not docs:
                self.logger.warning("Text content resulted in no documents after splitting. Returning empty summary.")
                return "No content provided to summarize."

            self.logger.debug(f"Split text into {len(docs)} documents for summarization.")

            # Invoke the summarization chain
            # For map_reduce, the input_documents parameter is typically used.
            summary_result = await self.summarize_chain.arun(docs)  # Using arun for async
            # If using invoke/ainvoke directly with some chains:
            # summary_result = await self.summarize_chain.ainvoke({"input_documents": docs})
            # The output format depends on the chain; for load_summarize_chain, it's usually a string.

            self.logger.info("Successfully generated summary from LLM.")
            self.logger.debug(f"LLM Summary: {summary_result}")
            return summary_result

        except Exception as e:
            self.logger.error(f"Error during LLM summarization: {e}", exc_info=True)
            return f"Error during summarization: {str(e)}"

    async def process_message(self, message_data: Dict[str, Any], client: Any) -> Optional[Dict[str, Any]]:
        header = message_data.get("mcp_header", {})
        payload = message_data.get("payload", {})
        message_type = header.get("message_type", "UNKNOWN")

        self.logger.info(f"SummarizeLogic process_message. Type='{message_type}'.")
        self.logger.debug(f"SummarizeLogic received payload: {str(payload)[:500]}...")

        if message_type == "TASK_ASSIGN":
            incoming_task_corr_id = header.get("correlation_id")
            _ = header.get("sender_id")  # original_router_id (reserved for future routing logic)

            task_parameters = payload.get("parameters", {})
            input_data_for_summary = task_parameters.get("text_to_summarize")  # This comes from RouterAgent

            self.logger.info(f"Received TASK_ASSIGN for summarization. Input data type: {type(input_data_for_summary)}")

            if not input_data_for_summary:
                self.logger.error("No 'text_to_summarize' provided in parameters.")
                return {
                    "message_type": "TASK_FAIL",
                    "payload": {
                        "workflow_id": payload.get("workflow_id"),
                        "task_id": payload.get("task_id"),
                        "agent_id": self.agent_id,
                        "correlation_id": incoming_task_corr_id,
                        "error_message": "No text provided for summarization.",
                    },
                }

            # Prepare the text content for summarization
            text_content_to_process = ""
            if isinstance(input_data_for_summary, dict) and "articles" in input_data_for_summary:
                self.logger.info(f"Extracting text from {len(input_data_for_summary.get('articles', []))} articles.")
                full_text_parts = []
                for article in input_data_for_summary.get("articles", []):
                    title = article.get("title", "")
                    abstract = article.get("abstract", "")
                    full_text_parts.append(f"Title: {title}\nAbstract: {abstract}\n\n")
                text_content_to_process = "".join(full_text_parts)
            elif isinstance(input_data_for_summary, str):
                text_content_to_process = input_data_for_summary
            else:
                self.logger.error(f"Unsupported type for 'text_to_summarize': {type(input_data_for_summary)}")
                return {
                    "message_type": "TASK_FAIL",
                    "payload": {
                        "workflow_id": payload.get("workflow_id"),
                        "task_id": payload.get("task_id"),
                        "agent_id": self.agent_id,
                        "correlation_id": incoming_task_corr_id,
                        "error_message": "Invalid format for text_to_summarize.",
                    },
                }

            if not text_content_to_process.strip():
                self.logger.warning("Extracted text_content_to_process is empty. Returning 'no content' message.")
                summary_text = "No content provided to summarize after extraction."
            else:
                summary_text = await self._generate_summary_with_llm(text_content_to_process)

            if "Error:" in summary_text:  # Check if LLM call failed
                return {
                    "message_type": "TASK_FAIL",
                    "payload": {
                        "workflow_id": payload.get("workflow_id"),
                        "task_id": payload.get("task_id"),
                        "agent_id": self.agent_id,
                        "correlation_id": incoming_task_corr_id,
                        "error_message": summary_text,
                    },
                }

            response_payload = {
                "workflow_id": payload.get("workflow_id"),
                "task_id": payload.get("task_id"),
                "agent_id": self.agent_id,
                "status": "COMPLETED",
                "result": {  # The actual result of the summarization task
                    "summary": summary_text,
                    "original_text_length": len(text_content_to_process),
                    "summary_length": len(summary_text),
                },
            }
            return {"message_type": "TASK_COMPLETE", "payload": response_payload}
        else:
            self.logger.warning(f"SummarizeLogic received unhandled message type: {message_type}")
            return None

    async def shutdown(self):
        self.logger.info(f"SummarizeAgentLogic shutting down for agent {self.agent_id}.")

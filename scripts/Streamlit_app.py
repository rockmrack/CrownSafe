# cureviax_builder_console_v6_final.py
# CureViaX™ Builder Console - FINAL FIXED VERSION
# Version: 6.0-FINAL

import asyncio
import base64
import io
import json
import os
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import anthropic
import chromadb
import google.generativeai as genai
import openai
import redis
import streamlit as st
import tiktoken
from PIL import Image

# Optional PDF support
try:
    import PyPDF2

    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

# Optional PDF to Image conversion
try:
    import pdf2image  # noqa: F401
    from pdf2image import convert_from_bytes  # noqa: F401

    PDF_TO_IMAGE_SUPPORT = True
except ImportError:
    PDF_TO_IMAGE_SUPPORT = False

# Optional PDF export
try:
    from reportlab.lib.enums import TA_JUSTIFY  # noqa: F401
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch  # noqa: F401
    from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer  # noqa: F401

    PDF_EXPORT_SUPPORT = True
except ImportError:
    PDF_EXPORT_SUPPORT = False

# Configure page
st.set_page_config(
    page_title="CureViaX Builder Console",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CSS - Enhanced for better code display
st.markdown(
    """
<style>
    .stApp {
        background-color: #f8f9fa;
    }
    
    .conversation-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 0.75rem;
        border-left: 4px solid transparent;
    }
    
    .user-message {
        background-color: #e3f2fd;
        border-left-color: #2196f3;
        margin-left: 2rem;
    }
    
    .assistant-message {
        background-color: #f5f5f5;
        margin-right: 2rem;
    }
    
    .claude-message {
        border-left-color: #8b5cf6;
    }
    
    .gemini-message {
        border-left-color: #3b82f6;
    }
    
    .gpt-message {
        border-left-color: #10b981;
    }
    
    .model-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 1rem;
        font-size: 0.8rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }
    
    .claude-badge {
        background-color: #8b5cf6;
        color: white;
    }
    
    .gemini-badge {
        background-color: #3b82f6;
        color: white;
    }
    
    .gpt-badge {
        background-color: #10b981;
        color: white;
    }
    
    .code-container {
        background-color: #1e1e1e;
        border: 2px solid #4a4a4a;
        border-radius: 8px;
        margin: 1rem 0;
        overflow: hidden;
    }
    
    .code-header {
        background-color: #2d2d2d;
        padding: 0.5rem 1rem;
        border-bottom: 1px solid #4a4a4a;
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 0.9rem;
        color: #ffffff;
    }
    
    .code-language {
        font-weight: bold;
        color: #61dafb;
    }
    
    .file-preview {
        background-color: #f0f0f0;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    
    .status-indicator {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-right: 5px;
    }
    
    .status-online {
        background-color: #10b981;
    }
    
    .status-offline {
        background-color: #ef4444;
    }
    
    .active-model {
        background-color: #e8f4f8;
        border: 2px solid #667eea;
        border-radius: 0.5rem;
        padding: 1rem;
        margin-bottom: 1rem;
    }
</style>
""",
    unsafe_allow_html=True,
)


# Data Classes
class ModelType(Enum):
    CLAUDE = "Claude 4 Opus"
    GEMINI = "Gemini 1.5 Pro"
    GPT = "GPT-4o"


@dataclass
class Message:
    id: str
    role: str  # 'user' or 'assistant'
    content: str
    model: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    tokens: int = 0
    attachments: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


# Fixed Memory Manager with Proper Redis Key Structure
class UnifiedMemoryManager:
    def __init__(self, redis_client: redis.Redis = None, chroma_client: chromadb.Client = None):
        self.redis_client = redis_client
        self.chroma_client = chroma_client
        self.collection = None
        self.session_id = self._get_or_create_session_id()

        # Token counter
        try:
            self.encoder = tiktoken.encoding_for_model("gpt-4")
        except Exception:
            self.encoder = tiktoken.get_encoding("cl100k_base")  # Fallback encoder

        # Token limits for different models
        self.token_limits = {
            "claude": 200000,  # Claude 4 Opus
            "gemini": 1000000,  # Gemini 1.5 Pro
            "gpt": 128000,  # GPT-4o
        }

    def _get_or_create_session_id(self):
        """Get persistent session ID - FIXED"""
        # First check if we have a session ID in query params
        query_params = st.query_params
        session_from_url = (
            query_params.get("session", [None])[0]
            if isinstance(query_params.get("session", None), list)
            else query_params.get("session", None)
        )

        if session_from_url:
            st.session_state.persistent_session_id = session_from_url
            return session_from_url

        # Check session state
        if "persistent_session_id" not in st.session_state:
            # Try to get from Redis
            if self.redis_client:
                try:
                    # Get the most recent session
                    sessions = self.redis_client.keys("session:*")
                    if sessions:
                        # Use the most recent session
                        session_data = []
                        for sess in sessions:
                            last_activity = self.redis_client.hget(sess, "last_activity")
                            if last_activity:
                                session_data.append((sess, float(last_activity)))

                        if session_data:
                            session_data.sort(key=lambda x: x[1], reverse=True)
                            most_recent = session_data[0][0].replace("session:", "")
                            st.session_state.persistent_session_id = most_recent
                        else:
                            st.session_state.persistent_session_id = str(uuid.uuid4())
                    else:
                        st.session_state.persistent_session_id = str(uuid.uuid4())
                except Exception:
                    st.session_state.persistent_session_id = str(uuid.uuid4())
            else:
                st.session_state.persistent_session_id = str(uuid.uuid4())

        # Update query params to persist session ID
        st.query_params["session"] = st.session_state.persistent_session_id

        # Update session activity
        if self.redis_client:
            try:
                self.redis_client.hset(
                    f"session:{st.session_state.persistent_session_id}",
                    "last_activity",
                    datetime.now().timestamp(),
                )
            except (redis.RedisError, redis.ConnectionError):
                pass  # Redis not available

        return st.session_state.persistent_session_id

    def initialize_chromadb_collection(self):
        """Initialize ChromaDB collection"""
        if not self.chroma_client:
            return False

        try:
            self.collection = self.chroma_client.get_or_create_collection(
                name="cureviax_unified_memory", metadata={"hnsw:space": "cosine"}
            )
            return True
        except Exception as e:
            st.error(f"ChromaDB init error: {e}")
            return False

    def store_message(self, message: Message):
        """Store message in both Redis and ChromaDB"""
        if not message.id:
            message.id = str(uuid.uuid4())

        # Count tokens
        message.tokens = len(self.encoder.encode(message.content))

        # Store in Redis with proper key structure
        if self.redis_client:
            try:
                # Store message data with ID-based key
                message_key = f"message:{self.session_id}:{message.id}"
                redis_data = {
                    "id": message.id,
                    "role": message.role,
                    "content": message.content,
                    "model": message.model or "user",
                    "timestamp": message.timestamp.isoformat(),
                    "tokens": str(message.tokens),
                    "session_id": self.session_id,
                }

                # Add attachments metadata
                if message.attachments:
                    attachments_metadata = []
                    for att in message.attachments:
                        att_meta = {
                            "name": att.get("name"),
                            "type": att.get("type"),
                            "size": att.get("size", 0),
                        }
                        if att.get("type") in ["text", "pdf"]:
                            att_meta["content"] = att.get("content", "")[:1000]
                        attachments_metadata.append(att_meta)
                    redis_data["attachments"] = json.dumps(attachments_metadata)

                # Store message
                self.redis_client.hset(message_key, mapping=redis_data)
                self.redis_client.expire(message_key, 86400 * 90)  # 90 days

                # Add to conversation timeline with score as timestamp
                self.redis_client.zadd(
                    f"timeline:{self.session_id}",
                    {message.id: message.timestamp.timestamp()},
                )

                # Update session info
                self.redis_client.hset(
                    f"session:{self.session_id}",
                    mapping={
                        "last_activity": str(datetime.now().timestamp()),
                        "message_count": str(self.redis_client.zcard(f"timeline:{self.session_id}")),
                    },
                )

                # Update conversation summary periodically
                message_count = self.redis_client.zcard(f"timeline:{self.session_id}")
                if message_count % 5 == 0:
                    self._update_conversation_summary()

            except Exception as e:
                st.error(f"Redis storage error: {e}")

        # Store in ChromaDB for semantic search
        if self.collection:
            try:
                doc_content = f"{message.role}: {message.content}"
                if message.attachments:
                    for att in message.attachments:
                        doc_content += f"\n[Attached {att['type']}: {att['name']}]"
                        if att.get("type") in ["text", "pdf"] and "content" in att:
                            doc_content += f"\n{att['content'][:500]}..."

                self.collection.add(
                    documents=[doc_content],
                    metadatas=[
                        {
                            "id": message.id,
                            "role": message.role,
                            "model": message.model or "user",
                            "timestamp": message.timestamp.isoformat(),
                            "session_id": self.session_id,
                            "tokens": message.tokens,
                            "has_attachments": len(message.attachments) > 0,
                        }
                    ],
                    ids=[message.id],
                )
            except Exception as e:
                st.error(f"ChromaDB storage error: {e}")

    def get_full_conversation_context(self, current_query: str, model_type: str = "claude") -> str:
        """Get comprehensive context with proper token management"""
        max_tokens = self.token_limits.get(model_type, 30000)
        # Reserve tokens for response
        response_reserve = {"claude": 4000, "gemini": 8000, "gpt": 4000}

        available_context_tokens = max_tokens - response_reserve.get(model_type, 4000)
        context_parts = []
        current_tokens = 0

        # 1. Add conversation summary
        summary = self._get_conversation_summary()
        if summary:
            summary_tokens = len(self.encoder.encode(summary))
            if current_tokens + summary_tokens < available_context_tokens * 0.05:
                context_parts.append(f"=== PROJECT CONTEXT ===\n{summary}\n")
                current_tokens += summary_tokens

        # 2. Get ALL recent messages from Redis
        all_messages = []

        if self.redis_client:
            try:
                # Get message IDs from timeline
                message_ids = self.redis_client.zrevrange(
                    f"timeline:{self.session_id}",
                    0,
                    99,  # Get last 100 messages
                )

                # Retrieve each message
                for msg_id in message_ids:
                    message_key = f"message:{self.session_id}:{msg_id}"
                    msg_data = self.redis_client.hgetall(message_key)

                    if msg_data and "content" in msg_data:
                        try:
                            timestamp = datetime.fromisoformat(msg_data["timestamp"])
                        except (ValueError, TypeError, KeyError):
                            timestamp = datetime.now()  # Invalid timestamp format

                        all_messages.append(
                            {
                                "id": msg_data.get("id", msg_id),
                                "role": msg_data.get("role", "user"),
                                "content": msg_data.get("content", ""),
                                "model": msg_data.get("model", ""),
                                "timestamp": timestamp,
                                "tokens": int(msg_data.get("tokens", 0)),
                            }
                        )

            except Exception as e:
                st.error(f"Error retrieving messages: {e}")

        # 3. Get semantically relevant messages from ChromaDB
        relevant_docs = []
        if self.collection and current_query:
            try:
                results = self.collection.query(
                    query_texts=[current_query],
                    n_results=20,
                    where={"session_id": self.session_id},
                )

                if results and results["documents"] and results["documents"][0]:
                    for i, doc in enumerate(results["documents"][0]):
                        metadata = results["metadatas"][0][i]
                        relevant_docs.append(
                            {
                                "id": metadata.get("id"),
                                "content": doc,
                                "relevance_score": 1.0 / (i + 1),
                            }
                        )
            except Exception as e:
                st.error(f"ChromaDB search error: {e}")

        # 4. Merge and sort messages
        message_dict = {msg["id"]: msg for msg in all_messages if msg.get("id")}

        # Enhance with relevance scores
        for doc in relevant_docs:
            doc_id = doc.get("id")
            if doc_id and doc_id in message_dict:
                message_dict[doc_id]["relevance_score"] = doc["relevance_score"]

        # Sort by timestamp and relevance
        sorted_messages = sorted(
            message_dict.values(),
            key=lambda x: (
                x.get("relevance_score", 0) * 10 + (datetime.now() - x["timestamp"]).total_seconds() / -3600
            ),
            reverse=True,
        )

        # 5. Build context within token limit
        context_parts.append("=== CONVERSATION HISTORY ===")

        message_count = 0
        for msg in sorted_messages:
            role_name = "User" if msg["role"] == "user" else msg.get("model", "Assistant")
            msg_text = f"\n{role_name}: {msg['content']}"

            msg_tokens = len(self.encoder.encode(msg_text))
            if current_tokens + msg_tokens < available_context_tokens:
                context_parts.append(msg_text)
                current_tokens += msg_tokens
                message_count += 1
            else:
                break

        # 6. Add current query
        context_parts.append(f"\n=== CURRENT QUERY ===\nUser: {current_query}")

        if st.session_state.get("debug_mode", False):
            st.sidebar.write(f"Context: {message_count} messages, {current_tokens} tokens")

        return "\n".join(context_parts)

    def _get_recent_messages(self, limit: int = 50) -> List[Dict]:
        """Get recent messages from Redis"""
        messages = []

        if not self.redis_client:
            return messages

        try:
            message_ids = self.redis_client.zrevrange(f"timeline:{self.session_id}", 0, limit - 1)

            for msg_id in message_ids:
                message_key = f"message:{self.session_id}:{msg_id}"
                msg_data = self.redis_client.hgetall(message_key)

                if msg_data:
                    if "attachments" in msg_data:
                        try:
                            msg_data["attachments"] = json.loads(msg_data["attachments"])
                        except (json.JSONDecodeError, TypeError):
                            msg_data["attachments"] = []  # Invalid JSON format
                    else:
                        msg_data["attachments"] = []

                    messages.append(msg_data)

            return messages

        except Exception as e:
            st.error(f"Error getting recent messages: {e}")
            return []

    def _get_conversation_summary(self) -> str:
        """Get or generate conversation summary"""
        if not self.redis_client:
            return "Building CureViaX: An advanced healthcare AI platform with multi-agent architecture."

        try:
            summary = self.redis_client.get(f"summary:{self.session_id}")
            if summary:
                return summary
            else:
                session_info = self.redis_client.hgetall(f"session:{self.session_id}")
                message_count = session_info.get("message_count", "0")

                recent_messages = self._get_recent_messages(10)
                topics = set()

                for msg in recent_messages:
                    content = msg.get("content", "").lower()
                    if "cureviax" in content:
                        topics.add("CureViaX platform")
                    if "agent" in content:
                        topics.add("multi-agent architecture")
                    if "memory" in content:
                        topics.add("memory systems")
                    if "api" in content:
                        topics.add("API integration")

                topic_str = ", ".join(topics) if topics else "general development"
                return f"CureViaX Development Session: {message_count} messages. Topics: {topic_str}. Building an advanced healthcare AI platform with persistent memory and multi-model support."  # noqa: E501
        except Exception:
            return "Building CureViaX: An advanced healthcare AI platform."

    def _update_conversation_summary(self):
        """Update conversation summary based on recent messages"""
        if not self.redis_client:
            return

        try:
            recent_messages = self._get_recent_messages(20)
            topics = set()
            key_decisions = []

            for msg in recent_messages:
                content = msg.get("content", "").lower()

                topic_keywords = {
                    "multi-agent architecture": [
                        "agent",
                        "multi-agent",
                        "orchestrator",
                    ],
                    "memory implementation": ["memory", "redis", "chromadb", "vector"],
                    "API development": ["api", "endpoint", "fastapi", "rest"],
                    "healthcare features": [
                        "healthcare",
                        "medical",
                        "patient",
                        "diagnosis",
                    ],
                    "code implementation": ["implement", "code", "function", "class"],
                    "database design": ["database", "postgresql", "schema", "model"],
                    "security": ["security", "authentication", "encryption", "hipaa"],
                    "UI/UX": ["ui", "interface", "streamlit", "frontend"],
                }

                for topic, keywords in topic_keywords.items():
                    if any(keyword in content for keyword in keywords):
                        topics.add(topic)

                if any(
                    word in content
                    for word in [
                        "decided",
                        "will use",
                        "architecture is",
                        "implemented",
                    ]
                ):
                    sentences = content.split(".")
                    for sentence in sentences:
                        if len(sentence) > 20 and any(
                            word in sentence
                            for word in [
                                "decided",
                                "will use",
                                "architecture",
                                "implemented",
                            ]
                        ):
                            key_decisions.append(sentence.strip())

            message_count = self.redis_client.zcard(f"timeline:{self.session_id}")

            summary_parts = [
                "CureViaX Development Session",
                f"Total Exchanges: {message_count}",
                f"Active Topics: {', '.join(topics) if topics else 'general development'}",
                "",
            ]

            if key_decisions:
                summary_parts.append("Key Decisions:")
                for decision in key_decisions[:5]:
                    summary_parts.append(f"- {decision}")

            summary_parts.append(
                "\nProject: Building an advanced healthcare AI platform with persistent memory, multi-agent architecture, and multi-model support."  # noqa: E501
            )

            summary = "\n".join(summary_parts)

            self.redis_client.set(f"summary:{self.session_id}", summary, ex=86400 * 90)  # 90 days
        except Exception:
            pass

    def load_conversation_history(self) -> List[Message]:
        """Load all messages from the current session"""
        messages = []

        if not self.redis_client:
            return messages

        try:
            message_ids = self.redis_client.zrange(f"timeline:{self.session_id}", 0, -1)

            for msg_id in message_ids:
                message_key = f"message:{self.session_id}:{msg_id}"
                msg_data = self.redis_client.hgetall(message_key)

                if msg_data and "content" in msg_data:
                    attachments = []
                    if "attachments" in msg_data:
                        try:
                            attachments = json.loads(msg_data["attachments"])
                        except (json.JSONDecodeError, TypeError):
                            pass  # Invalid attachment format

                    message = Message(
                        id=msg_data.get("id", msg_id),
                        role=msg_data.get("role", "user"),
                        content=msg_data.get("content", ""),
                        model=msg_data.get("model") if msg_data.get("role") == "assistant" else None,
                        timestamp=datetime.fromisoformat(msg_data.get("timestamp", datetime.now().isoformat())),
                        tokens=int(msg_data.get("tokens", 0)),
                        attachments=attachments,
                    )
                    messages.append(message)

            return messages

        except Exception as e:
            st.error(f"Error loading conversation history: {e}")
            return []


# Fixed Connection Manager
class ConnectionManager:
    def __init__(self):
        self.redis_client = None
        self.chroma_client = None
        self.anthropic_client = None
        self.gemini_client = None
        self.openai_client = openai
        self.memory_manager = None
        self.status = {
            "redis": False,
            "chromadb": False,
            "claude": False,
            "gemini": False,
            "gpt": False,
        }

    def connect_redis(self, host: str, port: int) -> bool:
        try:
            self.redis_client = redis.StrictRedis(
                host=host,
                port=port,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                socket_keepalive=True,
                socket_keepalive_options={},
            )
            self.redis_client.ping()
            self.status["redis"] = True
            self._init_memory()
            return True
        except Exception as e:
            st.error(f"Redis connection error: {e}")
            self.status["redis"] = False
            return False

    def connect_chromadb(self, path: str) -> bool:
        try:
            os.makedirs(path, exist_ok=True)
            self.chroma_client = chromadb.PersistentClient(path=path)
            self.status["chromadb"] = True
            self._init_memory()
            return True
        except Exception as e:
            st.error(f"ChromaDB connection error: {e}")
            self.status["chromadb"] = False
            return False

    def _init_memory(self):
        """Initialize memory manager when storage is available"""
        if self.redis_client or self.chroma_client:
            self.memory_manager = UnifiedMemoryManager(self.redis_client, self.chroma_client)
            if self.chroma_client:
                self.memory_manager.initialize_chromadb_collection()

    def connect_anthropic(self, api_key: str) -> bool:
        """Connect to Anthropic with ONLY the specified model"""
        try:
            if not api_key:
                return False
            self.anthropic_client = anthropic.Anthropic(api_key=api_key)
            # Test connection with ONLY the specified model
            self.anthropic_client.messages.create(
                model="claude-opus-4-20250514",
                max_tokens=10,  # REQUIRED BY CLAUDE API
                messages=[{"role": "user", "content": "test"}],
            )
            self.status["claude"] = True
            return True
        except Exception as e:
            st.error(f"Claude connection error: {e}")
            self.status["claude"] = False
            return False

    def connect_gemini(self, api_key: str) -> bool:
        """Connect to Gemini"""
        try:
            if not api_key or api_key.strip() == "":
                return False

            genai.configure(api_key=api_key.strip())

            model = genai.GenerativeModel("gemini-1.5-pro-latest")
            _ = model.generate_content("test")

            self.gemini_client = genai
            self.status["gemini"] = True
            return True

        except Exception:
            try:
                model = genai.GenerativeModel("gemini-1.5-pro")
                _ = model.generate_content("test")
                self.gemini_client = genai
                self.status["gemini"] = True
                return True
            except Exception as gemini_error:
                st.error(f"Gemini connection error: {gemini_error}")
                self.status["gemini"] = False
                return False

    def connect_openai(self, api_key: str) -> bool:
        """Connect to OpenAI"""
        try:
            if not api_key:
                return False

            openai.api_key = api_key

            # Try different models
            try:
                _ = openai.ChatCompletion.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": "test"}],
                    max_tokens=10,
                )
                self.status["gpt"] = True
                return True
            except Exception:
                # GPT-4o failed, try GPT-4-turbo-preview
                try:
                    _ = openai.ChatCompletion.create(
                        model="gpt-4-turbo-preview",
                        messages=[{"role": "user", "content": "test"}],
                        max_tokens=10,
                    )
                    self.status["gpt"] = True
                    return True
                except Exception:
                    # GPT-4-turbo-preview failed, try GPT-4
                    _ = openai.ChatCompletion.create(
                        model="gpt-4",
                        messages=[{"role": "user", "content": "test"}],
                        max_tokens=10,
                    )
                    self.status["gpt"] = True
                    return True

        except Exception as e:
            st.error(f"OpenAI connection error: {e}")
            self.status["gpt"] = False
            return False


# Model Executor with FIXED Claude Implementation
class MemoryAwareModelExecutor:
    def __init__(self, connection_manager: ConnectionManager):
        self.cm = connection_manager

    def _is_response_complete(self, response: str) -> bool:
        """Check if response appears complete"""
        code_blocks = re.findall(r"```", response)
        if len(code_blocks) % 2 != 0:
            return False

        truncation_indicators = [
            response.endswith("..."),
            response.endswith("(continued)"),
            response.endswith("[truncated]"),
            len(response) < 50,
        ]

        return not any(truncation_indicators)

    def _request_completion(self, incomplete_response: str, model_name: str) -> str:
        """Request completion of an incomplete response"""
        return f"""The previous response was incomplete. Please continue from where you left off:

{incomplete_response}

Continue the response, completing any unfinished thoughts or code blocks."""

    async def execute_claude(self, prompt: str, attachments: List[Dict] = None) -> str:
        """Execute Claude with REQUIRED max_tokens parameter"""
        if not self.cm.anthropic_client:
            return "Claude not connected. Please add your API key in the sidebar."

        # Get full context from memory
        context = ""
        if self.cm.memory_manager:
            context = self.cm.memory_manager.get_full_conversation_context(prompt, "claude")
            if st.session_state.get("debug_mode", False):
                st.sidebar.info(f"Context loaded: {len(context)} chars")
        else:
            context = prompt

        # Add attachment references
        if attachments:
            context += "\n\n=== ATTACHED FILES ==="
            for att in attachments:
                context += f"\n- {att['type']}: {att['name']}"
                if att["type"] == "text" and "content" in att:
                    context += f"\nContent: {att['content'][:1000]}..."
                elif att["type"] == "pdf" and "content" in att:
                    context += f"\nExtracted text: {att['content'][:1000]}..."

        try:
            max_retries = 3
            full_response = ""

            for attempt in range(max_retries):
                response = self.cm.anthropic_client.messages.create(
                    model="claude-opus-4-20250514",  # ONLY THIS MODEL
                    max_tokens=4000,  # REQUIRED BY CLAUDE API
                    temperature=0.7,
                    system="""You are Claude 4 Opus, an expert software architect building CureViaX. You have access to our entire conversation history through Redis and ChromaDB.  # noqa: E501

CRITICAL: Always complete your responses fully. Never cut off mid-sentence or mid-code block.

Key context about our project:
- Building CureViaX: Advanced healthcare AI platform
- Multi-agent architecture with specialized AI agents  
- Persistent memory using Redis and ChromaDB
- Production-ready code with comprehensive documentation

Reference our previous discussions and maintain continuity.""",
                    messages=[
                        {
                            "role": "user",
                            "content": context if attempt == 0 else self._request_completion(full_response, "Claude"),
                        }
                    ],
                )

                current_response = response.content[0].text

                if attempt == 0:
                    full_response = current_response
                else:
                    full_response += "\n\n" + current_response

                if self._is_response_complete(current_response):
                    break

            return full_response

        except Exception as e:
            return f"Claude error: {str(e)}"

    async def execute_gemini(self, prompt: str, attachments: List[Dict] = None) -> str:
        """Execute Gemini"""
        if not self.cm.gemini_client:
            return "Gemini not connected. Please add your API key in the sidebar."

        # Get full context from memory
        context = ""
        if self.cm.memory_manager:
            context = self.cm.memory_manager.get_full_conversation_context(prompt, "gemini")
            if st.session_state.get("debug_mode", False):
                st.sidebar.info(f"Context loaded: {len(context)} chars")
        else:
            context = prompt

        try:
            model = genai.GenerativeModel("gemini-1.5-pro-latest")

            max_retries = 3
            full_response = ""

            for attempt in range(max_retries):
                if attempt == 0:
                    full_prompt = f"""You are Gemini 1.5 Pro, assisting with CureViaX development. You have access to our conversation history.  # noqa: E501

CRITICAL: Complete all responses fully. Never truncate.

Context about our project:
- Building CureViaX healthcare AI platform
- Using multi-agent architecture
- Persistent memory with Redis/ChromaDB

{context}"""
                else:
                    full_prompt = self._request_completion(full_response, "Gemini")

                if attachments and attempt == 0:
                    full_prompt += "\n\nATTACHED FILES:"
                    for att in attachments:
                        full_prompt += f"\n- {att['type']}: {att['name']}"
                        if att.get("type") in ["text", "pdf"] and "content" in att:
                            full_prompt += f"\nContent: {att['content'][:1000]}..."

                response = model.generate_content(full_prompt)
                current_response = response.text

                if attempt == 0:
                    full_response = current_response
                else:
                    full_response += "\n\n" + current_response

                if self._is_response_complete(current_response):
                    break

            return full_response

        except Exception as e:
            return f"Gemini error: {str(e)}"

    async def execute_gpt(self, prompt: str, attachments: List[Dict] = None) -> str:
        """Execute GPT"""
        if not self.cm.openai_client:
            return "GPT not connected. Please add your API key in the sidebar."

        # Get full context from memory
        context = ""
        if self.cm.memory_manager:
            context = self.cm.memory_manager.get_full_conversation_context(prompt, "gpt")
            if st.session_state.get("debug_mode", False):
                st.sidebar.info(f"Context loaded: {len(context)} chars")
        else:
            context = prompt

        # Add attachments
        if attachments:
            context += "\n\nATTACHED FILES:"
            for att in attachments:
                context += f"\n- {att['type']}: {att['name']}"
                if att.get("type") in ["text", "pdf"] and "content" in att:
                    context += f"\nContent: {att['content'][:1000]}..."

        try:
            max_retries = 3
            full_response = ""

            for attempt in range(max_retries):
                messages = [
                    {
                        "role": "system",
                        "content": """You are GPT-4, helping build CureViaX. You have access to our full conversation history.  # noqa: E501

CRITICAL: Complete all responses fully. Never truncate.

Project context:
- CureViaX: Advanced healthcare AI platform
- Multi-agent architecture
- Persistent memory systems
- Production-ready implementations""",
                    },
                    {
                        "role": "user",
                        "content": context if attempt == 0 else self._request_completion(full_response, "GPT"),
                    },
                ]

                # Try different model names
                model_name = "gpt-4o"
                try:
                    response = openai.ChatCompletion.create(model=model_name, messages=messages, temperature=0.7)
                except Exception as e:
                    if "model" in str(e).lower():
                        for fallback_model in [
                            "gpt-4-turbo-preview",
                            "gpt-4",
                            "gpt-4-0613",
                        ]:
                            try:
                                response = openai.ChatCompletion.create(
                                    model=fallback_model,
                                    messages=messages,
                                    temperature=0.7,
                                )
                                model_name = fallback_model
                                break
                            except Exception:
                                # Model not available, try next fallback
                                continue
                        else:
                            raise Exception("No compatible GPT-4 model found")
                    else:
                        raise e

                current_response = response.choices[0].message.content

                if attempt == 0:
                    full_response = current_response
                else:
                    full_response += "\n\n" + current_response

                if self._is_response_complete(current_response):
                    break

            return full_response

        except Exception as e:
            return f"GPT error: {str(e)}"


# Helper functions
def display_message_with_code(content: str, container):
    """Display message with enhanced code blocks"""
    code_pattern = r"```(\w*)\n(.*?)```"
    parts = re.split(code_pattern, content, flags=re.DOTALL)

    current_text = ""
    i = 0
    code_block_counter = 1

    while i < len(parts):
        if i % 3 == 0:
            current_text += parts[i]
        elif i % 3 == 1:
            if current_text.strip():
                container.markdown(current_text.strip())
                current_text = ""

            language = parts[i] if parts[i] else "text"
            code_content = parts[i + 1] if i + 1 < len(parts) else ""

            with container.container():
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**📄 Code Block {code_block_counter} ({language.upper()})**")
                with col2:
                    if st.button("📋 Copy", key=f"copy_{code_block_counter}_{hash(code_content)}"):
                        st.code(code_content, language=language)
                        st.success("Code ready to copy!")

                st.code(code_content.strip(), language=language, line_numbers=True)
                code_block_counter += 1

            i += 1
        i += 1

    if current_text.strip():
        container.markdown(current_text.strip())


def process_uploaded_file(uploaded_file) -> Dict[str, Any]:
    """Process uploaded file and return metadata"""
    file_details = {
        "name": uploaded_file.name,
        "type": uploaded_file.type,
        "size": uploaded_file.size,
    }

    try:
        if uploaded_file.type == "text/plain":
            content = str(uploaded_file.read(), "utf-8")
            file_details["content"] = content
            file_details["type"] = "text"

        elif uploaded_file.type == "application/pdf":
            if PDF_SUPPORT:
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(uploaded_file.read()))
                content = ""
                for page in pdf_reader.pages:
                    content += page.extract_text() + "\n"
                file_details["content"] = content
                file_details["type"] = "pdf"
                file_details["pages"] = len(pdf_reader.pages)
            else:
                file_details["content"] = "PDF support not available. Install PyPDF2 to read PDFs."
                file_details["type"] = "pdf"

        elif uploaded_file.type.startswith("image/"):
            image = Image.open(uploaded_file)
            buffered = io.BytesIO()
            image.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            file_details["content"] = f"data:image/png;base64,{img_str}"
            file_details["type"] = "image"
            file_details["dimensions"] = f"{image.width}x{image.height}"

        else:
            file_details["content"] = "Binary file - content not extracted"
            file_details["type"] = "binary"

    except Exception as e:
        file_details["error"] = str(e)
        file_details["content"] = f"Error processing file: {str(e)}"

    return file_details


def export_conversation_to_pdf(messages: List[Message]) -> bytes:
    """Export conversation to PDF format"""
    if not PDF_EXPORT_SUPPORT:
        return None

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=24,
        textColor="#667eea",
        spaceAfter=30,
    )
    story.append(Paragraph("CureViaX Development Conversation", title_style))
    story.append(Spacer(1, 12))

    story.append(Paragraph(f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles["Normal"]))
    story.append(Spacer(1, 12))

    for msg in messages:
        if msg.role == "user":
            role_style = ParagraphStyle(
                "UserStyle",
                parent=styles["Normal"],
                textColor="#2196f3",
                fontSize=12,
                spaceAfter=6,
            )
            story.append(Paragraph(f"<b>You</b> - {msg.timestamp.strftime('%H:%M')}", role_style))
        else:
            role_style = ParagraphStyle(
                "AssistantStyle",
                parent=styles["Normal"],
                textColor="#667eea",
                fontSize=12,
                spaceAfter=6,
            )
            model_name = msg.model or "Assistant"
            story.append(
                Paragraph(
                    f"<b>{model_name}</b> - {msg.timestamp.strftime('%H:%M')}",
                    role_style,
                )
            )

        content_style = ParagraphStyle(
            "ContentStyle",
            parent=styles["Normal"],
            fontSize=11,
            spaceAfter=20,
            leftIndent=20,
        )
        content = msg.content.replace("```", "\n[CODE]\n")
        story.append(Paragraph(content[:10000], content_style))

        if msg.attachments:
            att_style = ParagraphStyle(
                "AttachmentStyle",
                parent=styles["Normal"],
                fontSize=10,
                textColor="#666",
                italic=True,
                leftIndent=20,
            )
            story.append(Paragraph(f"📎 {len(msg.attachments)} file(s) attached", att_style))

        story.append(Spacer(1, 12))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()


# Initialize session state
if "connection_manager" not in st.session_state:
    st.session_state.connection_manager = ConnectionManager()

if "executor" not in st.session_state:
    st.session_state.executor = MemoryAwareModelExecutor(st.session_state.connection_manager)

if "messages" not in st.session_state:
    st.session_state.messages = []

if "messages_loaded" not in st.session_state:
    st.session_state.messages_loaded = False

# Load conversation history on first run
if not st.session_state.messages_loaded and st.session_state.connection_manager.memory_manager:
    with st.spinner("Loading conversation history..."):
        loaded_messages = st.session_state.connection_manager.memory_manager.load_conversation_history()
        if loaded_messages:
            st.session_state.messages = loaded_messages
            st.success(f"Loaded {len(loaded_messages)} messages from memory")
        st.session_state.messages_loaded = True

if "current_model" not in st.session_state:
    st.session_state.current_model = ModelType.CLAUDE

if "pending_attachments" not in st.session_state:
    st.session_state.pending_attachments = []

# Sidebar
with st.sidebar:
    st.title("CureViaX Builder")
    st.caption("Unified Memory System v6.0 FINAL")

    # Debug mode toggle
    debug_mode = st.checkbox("Debug Mode", value=st.session_state.get("debug_mode", False))
    st.session_state.debug_mode = debug_mode

    # Session Info
    if st.session_state.connection_manager.memory_manager:
        st.info(f"Session: {st.session_state.connection_manager.memory_manager.session_id[:8]}...")

    # File Upload Section
    st.header("Upload Files")

    uploaded_files = st.file_uploader(
        "Choose files",
        type=["txt", "pdf", "png", "jpg", "jpeg", "gif", "bmp"],
        accept_multiple_files=True,
        help="Upload text files, PDFs, or images.",
    )

    if uploaded_files:
        for uploaded_file in uploaded_files:
            file_data = process_uploaded_file(uploaded_file)
            st.session_state.pending_attachments.append(file_data)

            with st.expander(f"📎 {file_data['name']}", expanded=False):
                st.write(f"Type: {file_data['type']}")
                st.write(f"Size: {file_data['size']} bytes")

                if file_data["type"] == "image":
                    st.image(file_data["content"], width=200)
                elif file_data["type"] in ["text", "pdf"]:
                    content_preview = file_data.get("content", "")[:500] + "..."
                    st.text(content_preview)

    if st.session_state.pending_attachments:
        st.info(f"{len(st.session_state.pending_attachments)} files ready")
        if st.button("Clear Attachments"):
            st.session_state.pending_attachments = []
            st.rerun()

    st.markdown("---")

    # AI Models section
    st.header("AI Models")

    # Active Model Selector
    st.markdown("### 🤖 Active Model")
    st.session_state.current_model = st.selectbox(
        "Select AI Model:",
        options=[ModelType.CLAUDE, ModelType.GEMINI, ModelType.GPT],
        format_func=lambda x: x.value,
        key="model_selector",
    )

    # Show current model status
    model_key_map = {
        ModelType.CLAUDE: "claude",
        ModelType.GEMINI: "gemini",
        ModelType.GPT: "gpt",
    }

    current_model_key = model_key_map[st.session_state.current_model]
    if st.session_state.connection_manager.status.get(current_model_key, False):
        st.success(f"✅ {st.session_state.current_model.value} Connected")
    else:
        st.error(f"❌ {st.session_state.current_model.value} Not Connected")

    st.markdown("---")

    # Model connections
    st.markdown("### Connect Models")

    # Claude
    with st.expander("Claude 4 Opus", expanded=False):
        claude_key = st.text_input(
            "API Key",
            type="password",
            key="claude_key",
            help="Enter your Anthropic API key",
        )
        if st.button("Connect", key="connect_claude"):
            if st.session_state.connection_manager.connect_anthropic(claude_key):
                st.success("Connected!")
                st.rerun()
            else:
                st.error("Failed to connect - check API key")

    # Gemini
    with st.expander("Gemini 1.5 Pro", expanded=False):
        gemini_key = st.text_input(
            "API Key",
            type="password",
            key="gemini_key",
            help="Enter your Google AI API key",
        )
        if st.button("Connect", key="connect_gemini"):
            if st.session_state.connection_manager.connect_gemini(gemini_key):
                st.success("Connected!")
                st.rerun()
            else:
                st.error("Failed to connect - check API key")

    # GPT
    with st.expander("GPT-4", expanded=False):
        gpt_key = st.text_input("API Key", type="password", key="gpt_key", help="Enter your OpenAI API key")
        if st.button("Connect", key="connect_gpt"):
            if st.session_state.connection_manager.connect_openai(gpt_key):
                st.success("Connected!")
                st.rerun()
            else:
                st.error("Failed to connect - check API key")

    # Memory System
    st.header("Memory System")

    with st.expander("Redis", expanded=False):
        redis_host = st.text_input("Host", value="localhost")
        redis_port = st.number_input("Port", value=6379)
        if st.button("Connect Redis"):
            if st.session_state.connection_manager.connect_redis(redis_host, redis_port):
                st.success("Connected!")
                if st.session_state.connection_manager.memory_manager:
                    loaded_messages = st.session_state.connection_manager.memory_manager.load_conversation_history()
                    if loaded_messages:
                        st.session_state.messages = loaded_messages
                st.rerun()

    with st.expander("ChromaDB", expanded=False):
        chroma_path = st.text_input("Path", value="./chroma_db")
        if st.button("Connect ChromaDB"):
            if st.session_state.connection_manager.connect_chromadb(chroma_path):
                st.success("Connected!")
                st.rerun()

    # Status
    st.header("Status")
    for key, name in {
        "claude": "Claude 4",
        "gemini": "Gemini 1.5",
        "gpt": "GPT-4",
        "redis": "Redis",
        "chromadb": "ChromaDB",
    }.items():
        if st.session_state.connection_manager.status.get(key, False):
            st.markdown(
                f"<span class='status-indicator status-online'></span>{name}",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"<span class='status-indicator status-offline'></span>{name}",
                unsafe_allow_html=True,
            )

# Main interface
st.title("CureViaX Builder Console")

# Header
memory_status = (
    "Memory Active"
    if (st.session_state.connection_manager.status["redis"] or st.session_state.connection_manager.status["chromadb"])
    else "Memory Inactive"
)

st.markdown(
    f"""
<div class="conversation-header">
    <h3 style="margin: 0;">Continuous Conversation Mode</h3>
    <p style="margin: 0.5rem 0 0 0;">Model: {st.session_state.current_model.value} | {memory_status} | Messages: {len(st.session_state.messages)}</p>  # noqa: E501
</div>
""",
    unsafe_allow_html=True,
)

# Display conversation
chat_container = st.container()
with chat_container:
    for message in st.session_state.messages:
        if message.role == "user":
            content = message.content
            if message.attachments:
                content = f"{content}\n\n📎 Attachments: {len(message.attachments)} file(s)"

            st.markdown(
                f"""
            <div class="chat-message user-message">
                <strong>You:</strong><br/>
                {content}
            </div>
            """,
                unsafe_allow_html=True,
            )

            if message.attachments:
                for att in message.attachments:
                    if att["type"] == "image":
                        st.image(att["content"], caption=att["name"], width=300)
        else:
            model_class = ""
            model_badge = ""

            if message.model == "Claude":
                model_class = "claude-message"
                model_badge = "<span class='model-badge claude-badge'>Claude 4</span>"
            elif message.model == "Gemini":
                model_class = "gemini-message"
                model_badge = "<span class='model-badge gemini-badge'>Gemini 1.5</span>"
            elif message.model == "GPT":
                model_class = "gpt-message"
                model_badge = "<span class='model-badge gpt-badge'>GPT-4</span>"

            with st.container():
                st.markdown(
                    f"""
                <div class="chat-message assistant-message {model_class}">
                    {model_badge}
                </div>
                """,
                    unsafe_allow_html=True,
                )

                message_container = st.container()
                display_message_with_code(message.content, message_container)

# Input form
with st.form("chat_form", clear_on_submit=True):
    user_input = st.text_area(
        "Continue the conversation:",
        height=200,
        placeholder="Ask anything about CureViaX...",
    )

    col1, col2 = st.columns([4, 1])
    with col1:
        if st.session_state.pending_attachments:
            st.info(f"📎 {len(st.session_state.pending_attachments)} file(s) will be sent")

    with col2:
        submit = st.form_submit_button("Send", type="primary", use_container_width=True)

if submit and user_input:
    # Create user message
    user_message = Message(
        id=str(uuid.uuid4()),
        role="user",
        content=user_input,
        attachments=st.session_state.pending_attachments.copy(),
    )
    st.session_state.messages.append(user_message)

    # Store in memory
    if st.session_state.connection_manager.memory_manager:
        st.session_state.connection_manager.memory_manager.store_message(user_message)

    # Clear pending attachments
    attachments_to_send = st.session_state.pending_attachments.copy()
    st.session_state.pending_attachments = []

    # Execute on selected model
    with st.spinner(f"🤖 {st.session_state.current_model.value} is thinking..."):
        if st.session_state.current_model == ModelType.CLAUDE:
            response = asyncio.run(st.session_state.executor.execute_claude(user_input, attachments_to_send))
            model_name = "Claude"
        elif st.session_state.current_model == ModelType.GEMINI:
            response = asyncio.run(st.session_state.executor.execute_gemini(user_input, attachments_to_send))
            model_name = "Gemini"
        else:
            response = asyncio.run(st.session_state.executor.execute_gpt(user_input, attachments_to_send))
            model_name = "GPT"

        # Add assistant message
        assistant_message = Message(id=str(uuid.uuid4()), role="assistant", content=response, model=model_name)
        st.session_state.messages.append(assistant_message)

        # Store in memory
        if st.session_state.connection_manager.memory_manager:
            st.session_state.connection_manager.memory_manager.store_message(assistant_message)

    st.rerun()

# Footer
st.markdown("---")
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("Export Conversation"):
        if PDF_EXPORT_SUPPORT and st.session_state.messages:
            pdf_data = export_conversation_to_pdf(st.session_state.messages)
            if pdf_data:
                st.download_button(
                    "Download PDF",
                    pdf_data,
                    f"cureviax_conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                    "application/pdf",
                )
        else:
            export_data = []
            for msg in st.session_state.messages:
                export_data.append(
                    {
                        "role": msg.role,
                        "content": msg.content,
                        "model": msg.model,
                        "timestamp": msg.timestamp.isoformat(),
                        "attachments": len(msg.attachments),
                    }
                )

            st.download_button(
                "Download JSON",
                json.dumps(export_data, indent=2),
                f"cureviax_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                "application/json",
            )

with col2:
    status_text = "Memory: Active" if st.session_state.connection_manager.memory_manager else "Memory: Inactive"
    if st.session_state.connection_manager.memory_manager and st.session_state.connection_manager.status["redis"]:
        status_text += " (Redis)"
    if st.session_state.connection_manager.memory_manager and st.session_state.connection_manager.status["chromadb"]:
        status_text += " (ChromaDB)"
    st.info(status_text)

with col3:
    with st.expander("🚀 Features & Tips"):
        st.write(
            """
        **✅ FINAL FIXED VERSION:**
        - Claude API requires max_tokens (set to 4000)
        - Uses ONLY claude-opus-4-20250514
        - Memory system working
        - Full conversation history
        
        **🔧 Available Models:**
        - Claude 4 Opus (200K context)
        - Gemini 1.5 Pro (1M context)
        - GPT-4 variants (128K context)
        
        **💾 Memory Features:**
        - Persistent conversation history
        - Session ID in URL
        - Smart context management
        - Semantic search via ChromaDB
        """
        )

# Optional dependency info
if not PDF_SUPPORT:
    with st.expander("Enable PDF Text Extraction"):
        st.code("pip install PyPDF2", language="bash")

if not PDF_EXPORT_SUPPORT:
    with st.expander("Enable PDF Export"):
        st.code("pip install reportlab", language="bash")

# Debug information
if st.session_state.get("debug_mode", False):
    with st.expander("Debug Information", expanded=True):
        st.write("**Session Info:**")
        st.write(f"- Session ID: {st.session_state.get('persistent_session_id', 'None')}")
        st.write(f"- Messages in memory: {len(st.session_state.messages)}")
        st.write(f"- Current model: {st.session_state.current_model.value}")

        st.write("\n**Connection Status:**")
        for service, status in st.session_state.connection_manager.status.items():
            st.write(f"- {service}: {'✅ Connected' if status else '❌ Disconnected'}")

        if st.session_state.connection_manager.redis_client:
            try:
                session_id = st.session_state.connection_manager.memory_manager.session_id
                message_count = st.session_state.connection_manager.redis_client.zcard(f"timeline:{session_id}")
                st.write("\n**Redis Stats:**")
                st.write(f"- Messages in timeline: {message_count}")
                st.write(f"- Session key: session:{session_id}")
            except (redis.RedisError, AttributeError, KeyError):
                # Redis connection issue or missing session data
                pass

# Add this to avoid reconnecting every time:
if "auto_reconnect" not in st.session_state:
    st.session_state.auto_reconnect = True
    # Auto-reconnect logic here

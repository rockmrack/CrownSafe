# C:\Users\rossd\Downloads\RossNetAgents\core_infra\memory_manager.py
# Version: MVP-1.4 (Production-Ready with Advanced Retrieval & Analytics)
# FIXED: Logger initialization issue - ensures proper logger object handling

import logging
import os
import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Set, Union, Tuple
from collections import defaultdict, Counter
import statistics

import chromadb
from chromadb.utils import embedding_functions

try:
    from dotenv import load_dotenv

    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

    def load_dotenv(
        dotenv_path=None,
        verbose=False,
        override=False,
        interpolate=True,
        encoding="utf-8",
    ):
        pass


# Default logger
logger_mm_default = logging.getLogger(__name__)

# Default paths and settings
DEFAULT_CHROMA_PATH = os.path.join(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..")), "chroma_db_data_v2"
)
DEFAULT_COLLECTION_NAME = "cureviax_knowledge_base_v1"

# Load environment variables
if DOTENV_AVAILABLE:
    try:
        project_root_for_env = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..")
        )
        dotenv_path_for_env = os.path.join(project_root_for_env, ".env")
        if os.path.exists(dotenv_path_for_env):
            load_dotenv(dotenv_path_for_env)
            logger_mm_default.debug(
                f"MemoryManager: Loaded .env from {dotenv_path_for_env}"
            )
    except Exception as e_env:
        logger_mm_default.warning(f"MemoryManager: Error loading .env file: {e_env}")


class MemoryManager:
    def __init__(
        self,
        logger_instance: Optional[logging.Logger] = None,
        chroma_db_path: Optional[str] = None,
        collection_name: Optional[str] = None,
    ):
        """
        Initialize MemoryManager with ChromaDB and OpenAI embeddings.
        FIXED: Proper logger initialization to prevent 'str' object attribute errors.
        """

        # FIXED: Robust logger initialization
        if logger_instance is not None:
            # Verify it's actually a logger object with required methods
            if (
                hasattr(logger_instance, "info")
                and hasattr(logger_instance, "error")
                and hasattr(logger_instance, "warning")
            ):
                self.logger = logger_instance
            else:
                # If it's not a proper logger (e.g., string), create a new one
                print(
                    f"WARNING: Invalid logger_instance provided (type: {type(logger_instance)}). Creating new logger."
                )
                self.logger = logging.getLogger(__name__)
        else:
            self.logger = logging.getLogger(__name__)

        # Ensure logger has proper configuration
        if not self.logger.handlers:
            # Add basic handler if none exists
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

        # Verify logger is working by testing it
        try:
            self.logger.info("MemoryManager initialization starting...")
        except Exception as logger_test_error:
            # Last resort: create a completely new logger
            print(f"Logger test failed: {logger_test_error}. Creating fallback logger.")
            self.logger = logging.getLogger(f"{__name__}_{id(self)}")
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

        # Initialize paths and settings
        self.db_path = (
            chroma_db_path
            if chroma_db_path
            else os.getenv("CHROMA_DB_PATH", DEFAULT_CHROMA_PATH)
        )
        self.collection_name = (
            collection_name if collection_name else DEFAULT_COLLECTION_NAME
        )

        # Initialize components
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.embedding_function = None
        self.chroma_client = None
        self.collection = None

        # Check for OpenAI API key
        if not self.openai_api_key:
            self.logger.warning(
                "OPENAI_API_KEY not found. Will use default embedding function."
            )

        # Initialize OpenAI embedding function
        try:
            if self.openai_api_key:
                self.embedding_function = (
                    chromadb.utils.embedding_functions.OpenAIEmbeddingFunction(
                        api_key=self.openai_api_key, model_name="text-embedding-ada-002"
                    )
                )
                self.logger.info(
                    "OpenAI EmbeddingFunction initialized with text-embedding-ada-002."
                )
            else:
                self.logger.info("Using default ChromaDB embedding function.")
        except Exception as e_embed:
            self.logger.error(
                f"Failed to initialize OpenAIEmbeddingFunction: {e_embed}"
            )
            self.logger.warning("Falling back to default embedding function")
            self.embedding_function = None

        # Initialize ChromaDB regardless of embedding function
        self._initialize_chromadb()

    def _initialize_chromadb(self):
        """Initialize ChromaDB client and collection."""

        # Create directory if it doesn't exist
        if not os.path.exists(self.db_path):
            try:
                os.makedirs(self.db_path, exist_ok=True)
                self.logger.info(f"Created ChromaDB directory: {self.db_path}")
            except Exception as e:
                self.logger.error(
                    f"Failed to create ChromaDB directory {self.db_path}: {e}"
                )
                return

        self.logger.info(
            f"Initializing MemoryManager with ChromaDB path: {self.db_path}"
        )

        try:
            # Initialize ChromaDB client
            self.chroma_client = chromadb.PersistentClient(path=self.db_path)

            # Create collection with or without custom embedding function
            if self.embedding_function:
                self.collection = self.chroma_client.get_or_create_collection(
                    name=self.collection_name,
                    embedding_function=self.embedding_function,
                    metadata={"hnsw:space": "cosine"},
                )
                self.logger.info(
                    f"ChromaDB collection '{self.collection_name}' created with OpenAI embeddings."
                )
            else:
                # Use default embedding function
                self.collection = self.chroma_client.get_or_create_collection(
                    name=self.collection_name, metadata={"hnsw:space": "cosine"}
                )
                self.logger.info(
                    f"ChromaDB collection '{self.collection_name}' created with default embeddings."
                )

            # Get current document count
            current_count = self.collection.count()
            self.logger.info(
                f"ChromaDB collection loaded successfully. Current document count: {current_count}"
            )

        except Exception as e:
            self.logger.error(f"Failed to initialize ChromaDB client/collection: {e}")
            self.chroma_client = None
            self.collection = None

    def _generate_canonical_id(self, document_type: str, identifier: str) -> str:
        """Generate canonical IDs for deduplication."""
        clean_identifier = (
            str(identifier)
            .lower()
            .replace(" ", "_")
            .replace("/", "_")
            .replace("-", "_")
        )
        return f"{document_type}_{clean_identifier}"

    def _safe_json_loads(
        self, json_string: Union[str, List, None], default_value: Optional[List] = None
    ) -> List:
        """Safely parse JSON string to list."""
        if default_value is None:
            default_value = []

        if json_string is None:
            return default_value
        if isinstance(json_string, list):
            return json_string
        if isinstance(json_string, str):
            try:
                parsed = json.loads(json_string)
                return parsed if isinstance(parsed, list) else [parsed]
            except (json.JSONDecodeError, TypeError):
                return [json_string] if json_string else default_value
        return default_value

    def _safe_json_dumps(self, data: Union[List, Set, str, None]) -> str:
        """Safely convert data to JSON string."""
        if data is None:
            return "[]"
        if isinstance(data, str):
            try:
                json.loads(data)  # Test if valid JSON
                return data
            except (json.JSONDecodeError, TypeError):
                return json.dumps([data])
        if isinstance(data, (list, set)):
            return json.dumps(list(data))
        return json.dumps([str(data)])

    def _merge_metadata_for_existing_document(
        self,
        existing_metadata: Dict[str, Any],
        new_context_metadata: Dict[str, Any],
        current_timestamp: str,
    ) -> Dict[str, Any]:
        """Intelligently merge metadata for existing documents."""
        merged = existing_metadata.copy()

        # Track workflows
        existing_workflows = self._safe_json_loads(
            merged.get("referenced_in_workflows")
        )
        new_workflow_id = new_context_metadata.get("workflow_id_source")
        if new_workflow_id and new_workflow_id not in existing_workflows:
            existing_workflows.append(new_workflow_id)

        merged["referenced_in_workflows"] = self._safe_json_dumps(existing_workflows)
        merged["reference_count"] = len(existing_workflows)

        # Update timestamps
        merged["last_seen_timestamp"] = current_timestamp
        if "first_seen_timestamp" not in merged:
            merged["first_seen_timestamp"] = new_context_metadata.get(
                "timestamp_added_or_updated", current_timestamp
            )

        # Aggregate context lists
        def _aggregate_context_list(field_key: str, new_value: Any) -> str:
            current_list = self._safe_json_loads(merged.get(field_key))
            if new_value and str(new_value) not in [str(item) for item in current_list]:
                current_list.append(str(new_value))
            return self._safe_json_dumps(current_list)

        merged["user_goals_context"] = _aggregate_context_list(
            "user_goals_context", new_context_metadata.get("user_goal_context")
        )
        merged["drug_names_context"] = _aggregate_context_list(
            "drug_names_context", new_context_metadata.get("drug_name_context")
        )
        merged["disease_names_context"] = _aggregate_context_list(
            "disease_names_context", new_context_metadata.get("disease_name_context")
        )

        # Update other fields with better data
        for key, value in new_context_metadata.items():
            if (
                key
                not in [
                    "workflow_id_source",
                    "user_goal_context",
                    "drug_name_context",
                    "disease_name_context",
                    "timestamp_added_or_updated",
                ]
                and value is not None
            ):
                if key not in merged or merged[key] is None:
                    merged[key] = (
                        value
                        if not isinstance(value, (list, dict))
                        else json.dumps(value)
                    )

        return {k: v for k, v in merged.items() if v is not None}

    def _get_existing_metadatas(
        self, ids_to_check: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """Check which documents already exist and return their metadata."""
        if not self.collection or not ids_to_check:
            return {}

        try:
            existing_docs = self.collection.get(ids=ids_to_check, include=["metadatas"])
            found_metadatas = {}

            if existing_docs and existing_docs.get("ids"):
                for i, doc_id in enumerate(existing_docs["ids"]):
                    if (
                        doc_id
                        and existing_docs.get("metadatas")
                        and i < len(existing_docs["metadatas"])
                        and existing_docs["metadatas"][i] is not None
                    ):
                        found_metadatas[doc_id] = existing_docs["metadatas"][i]

            self.logger.debug(
                f"Checked {len(ids_to_check)} IDs, found {len(found_metadatas)} existing documents."
            )
            return found_metadatas

        except Exception as e:
            self.logger.error(f"Error getting existing metadata: {e}")
            return {}

    def _prepare_safe_metadata(
        self,
        base_metadata: Dict[str, Any],
        workflow_id: str,
        user_goal: str,
        drug_name: Optional[str],
        disease_name: Optional[str],
        timestamp: str,
    ) -> Dict[str, Any]:
        """Prepare metadata with ChromaDB-safe values."""
        safe_metadata = base_metadata.copy()

        # Add tracking fields
        safe_metadata["first_seen_timestamp"] = timestamp
        safe_metadata["last_seen_timestamp"] = timestamp
        safe_metadata["referenced_in_workflows"] = self._safe_json_dumps([workflow_id])
        safe_metadata["reference_count"] = 1

        # Initialize context lists
        safe_metadata["user_goals_context"] = self._safe_json_dumps(
            [user_goal] if user_goal else []
        )
        safe_metadata["drug_names_context"] = self._safe_json_dumps(
            [drug_name] if drug_name else []
        )
        safe_metadata["disease_names_context"] = self._safe_json_dumps(
            [disease_name] if disease_name else []
        )

        # Ensure all values are ChromaDB-safe
        final_metadata = {}
        for key, value in safe_metadata.items():
            if value is None:
                continue
            if isinstance(value, (list, dict)):
                final_metadata[key] = json.dumps(value)
            else:
                final_metadata[key] = value

        return final_metadata

    def store_workflow_outputs(
        self,
        workflow_id: str,
        user_goal: str,
        extracted_entities: Dict[str, Optional[str]],
        pubmed_results_payload: Optional[Dict[str, Any]],
        pdf_path: Optional[str] = None,
        completion_timestamp: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Store workflow outputs with intelligent deduplication and metadata merging."""
        if not self.collection:
            self.logger.error(
                "Cannot store workflow outputs: ChromaDB collection not available."
            )
            return {"status": "error", "message": "ChromaDB collection not available"}

        if completion_timestamp is None:
            completion_timestamp = datetime.now(timezone.utc).isoformat()

        self.logger.info(f"Storing outputs for workflow_id: {workflow_id}")

        docs_for_upsert: List[str] = []
        metadatas_to_prepare: List[Dict[str, Any]] = []
        ids_for_upsert: List[str] = []

        current_utc_timestamp = datetime.now(timezone.utc).isoformat()
        drug_name = extracted_entities.get("drug_name")
        disease_name = extracted_entities.get("disease_name")

        context_meta = {
            "workflow_id_source": workflow_id,
            "user_goal_context": user_goal,
            "drug_name_context": drug_name,
            "disease_name_context": disease_name,
            "timestamp_added_or_updated": current_utc_timestamp,
        }

        # 1. Workflow Summary
        summary_parts = [f"Workflow Summary for Goal: {user_goal}"]
        if drug_name:
            summary_parts.append(f"Drug: {drug_name}")
        if disease_name:
            summary_parts.append(f"Disease: {disease_name}")
        if pdf_path:
            summary_parts.append(f"Report: {os.path.basename(pdf_path)}")

        workflow_doc_id = self._generate_canonical_id("workflow", workflow_id)
        docs_for_upsert.append(". ".join(summary_parts))
        ids_for_upsert.append(workflow_doc_id)

        workflow_metadata = {
            "document_type": "workflow_summary",
            "workflow_id": workflow_id,
            "user_goal": user_goal,
            "drug_name": drug_name,
            "disease_name": disease_name,
            "pdf_path": pdf_path,
            "timestamp": completion_timestamp,
            "source": "commander_agent",
            **context_meta,
        }
        metadatas_to_prepare.append(workflow_metadata)

        # 2. PubMed Articles
        if pubmed_results_payload and isinstance(
            pubmed_results_payload.get("articles"), list
        ):
            for article in pubmed_results_payload.get("articles", []):
                if not isinstance(article, dict) or not article.get("pmid"):
                    continue

                pmid = str(article["pmid"])
                doc_id = self._generate_canonical_id("pubmed", pmid)
                ids_for_upsert.append(doc_id)

                title = article.get("title", "N/A")
                abstract = article.get("abstract", "N/A")
                docs_for_upsert.append(f"Title: {title}\nAbstract: {abstract}")

                article_metadata = {
                    "document_type": "pubmed_article",
                    "pmid": pmid,
                    "title": title,
                    "authors": json.dumps(article.get("authors"))
                    if article.get("authors")
                    else None,
                    "journal": article.get("journal"),
                    "publication_date": article.get("publication_date"),
                    "abstract": abstract[:1000] if len(abstract) > 1000 else abstract,
                    "source_agent_id": "web_research_agent",
                    "is_mock_data": pubmed_results_payload.get("source") == "mock_data",
                    **context_meta,
                }
                metadatas_to_prepare.append(article_metadata)

        # Clinical trial and drug safety data are no longer collected; legacy payloads are ignored.

        # Process for upsert with intelligent merging
        if not ids_for_upsert:
            self.logger.warning(f"No documents prepared for workflow {workflow_id}.")
            return {"status": "warning", "message": "No documents to store"}

        existing_metadatas = self._get_existing_metadatas(ids_for_upsert)
        final_metadatas_for_upsert = []

        for i, doc_id in enumerate(ids_for_upsert):
            if doc_id in existing_metadatas:
                merged_metadata = self._merge_metadata_for_existing_document(
                    existing_metadatas[doc_id],
                    metadatas_to_prepare[i],
                    current_utc_timestamp,
                )
                final_metadatas_for_upsert.append(merged_metadata)
            else:
                new_metadata = self._prepare_safe_metadata(
                    metadatas_to_prepare[i],
                    workflow_id,
                    user_goal,
                    drug_name,
                    disease_name,
                    current_utc_timestamp,
                )
                final_metadatas_for_upsert.append(new_metadata)

        # Perform upsert
        try:
            num_new = len(ids_for_upsert) - len(existing_metadatas)
            num_updated = len(existing_metadatas)

            self.logger.info(
                f"Upserting {len(docs_for_upsert)} documents. New: {num_new}, Updated: {num_updated}"
            )

            self.collection.upsert(
                ids=ids_for_upsert,
                documents=docs_for_upsert,
                metadatas=final_metadatas_for_upsert,
            )

            total_count = self.collection.count()
            self.logger.info(
                f"Successfully upserted documents. Collection total: {total_count}"
            )

            return {
                "status": "success",
                "documents_processed": len(docs_for_upsert),
                "new_documents": num_new,
                "updated_documents": num_updated,
                "total_collection_size": total_count,
            }

        except Exception as e:
            self.logger.error(
                f"Failed to upsert documents for workflow {workflow_id}: {e}"
            )
            return {"status": "error", "message": str(e)}

    def find_similar_documents(
        self,
        query_text: str,
        n_results: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Find similar documents (synchronous version for compatibility)."""
        if not self.collection:
            self.logger.error("Cannot retrieve: ChromaDB collection not available.")
            return []

        try:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results,
                where=filter_metadata,
                include=["metadatas", "documents", "distances"],
            )

            if not results or not results.get("ids") or not results["ids"][0]:
                return []

            processed_results = []
            for i in range(len(results["ids"][0])):
                result_item = {
                    "id": results["ids"][0][i],
                    "document": results["documents"][0][i]
                    if results.get("documents") and results["documents"][0]
                    else None,
                    "metadata": results["metadatas"][0][i]
                    if results.get("metadatas") and results["metadatas"][0]
                    else {},
                    "distance": results["distances"][0][i]
                    if results.get("distances") and results["distances"][0]
                    else 1.0,
                }
                processed_results.append(result_item)

            return processed_results

        except Exception as e:
            self.logger.error(f"Failed to find similar documents: {e}")
            return []

    def get_document_usage_analytics(self) -> Dict[str, Any]:
        """Get comprehensive analytics about document usage and patterns."""
        if not self.collection:
            return {"error": "Collection unavailable"}

        try:
            all_docs = self.collection.get(include=["metadatas"])
            if not all_docs or not all_docs.get("metadatas"):
                return {"error": "No documents found"}

            analytics = {
                "total_documents": len(all_docs["metadatas"]),
                "most_referenced": [],
                "workflow_coverage": {},
                "content_type_distribution": {},
                "drug_class_patterns": {},
                "quality_metrics": {},
                "cross_workflow_evidence": 0,
            }

            # Process all documents
            reference_counts = []
            workflow_docs = defaultdict(int)
            content_types = defaultdict(int)
            drug_patterns = defaultdict(
                lambda: {"documents": 0, "workflows": set(), "types": set()}
            )
            cross_workflow_count = 0

            for metadata in all_docs["metadatas"]:
                if not metadata:
                    continue

                # Parse JSON fields
                workflows = self._safe_json_loads(
                    metadata.get("referenced_in_workflows")
                )
                drugs = self._safe_json_loads(metadata.get("drug_names_context"))

                ref_count = len(workflows)
                reference_counts.append(ref_count)

                if ref_count > 1:
                    cross_workflow_count += 1

                # Content type distribution
                doc_type = metadata.get("document_type", "unknown")
                content_types[doc_type] += 1

                # Drug pattern analysis
                for drug in drugs:
                    drug_patterns[drug]["documents"] += 1
                    drug_patterns[drug]["workflows"].update(workflows)
                    drug_patterns[drug]["types"].add(doc_type)

                # Workflow coverage
                for wf in workflows:
                    workflow_docs[wf] += 1

            # Calculate metrics
            analytics["workflow_coverage"] = dict(workflow_docs)
            analytics["content_type_distribution"] = dict(content_types)
            analytics["cross_workflow_evidence"] = cross_workflow_count

            # Quality metrics
            if reference_counts:
                analytics["quality_metrics"] = {
                    "average_references": statistics.mean(reference_counts),
                    "high_quality_documents": sum(
                        1 for rc in reference_counts if rc >= 2
                    ),
                }

            # Drug class patterns
            analytics["drug_class_patterns"] = {
                drug: {
                    "document_count": data["documents"],
                    "workflow_count": len(data["workflows"]),
                    "document_types": list(data["types"]),
                }
                for drug, data in drug_patterns.items()
            }

            self.logger.info(
                f"Generated analytics for {analytics['total_documents']} documents"
            )
            return analytics

        except Exception as e:
            self.logger.error(f"Error generating analytics: {e}")
            return {"error": str(e)}

    def dump_collection_sample(
        self,
        document_type: Optional[str] = None,
        limit: int = 5,
        parse_json: bool = True,
    ) -> None:
        """Print a sample of documents for debugging."""
        if not self.collection:
            print("Collection unavailable.")
            return

        print(
            f"\n--- Sample Dump: {self.collection_name} (Limit: {limit}, Type: {document_type or 'Any'}) ---"
        )

        try:
            filter_dict = {"document_type": document_type} if document_type else None
            results = self.collection.get(
                limit=limit, where=filter_dict, include=["metadatas", "documents"]
            )

            if not results or not results.get("ids"):
                print("No documents found.")
                return

            for i, doc_id in enumerate(results["ids"]):
                print(f"\nDocument {i + 1}: {doc_id}")

                if results.get("metadatas") and i < len(results["metadatas"]):
                    metadata = results["metadatas"][i]
                    if metadata:
                        print("  Metadata:")
                        for key, value in metadata.items():
                            if parse_json and key in [
                                "referenced_in_workflows",
                                "user_goals_context",
                                "drug_names_context",
                                "disease_names_context",
                            ]:
                                parsed = self._safe_json_loads(value)
                                print(f"    {key}: {parsed}")
                            elif isinstance(value, str) and len(value) > 100:
                                print(f"    {key}: {value[:100]}...")
                            else:
                                print(f"    {key}: {value}")

                if results.get("documents") and i < len(results["documents"]):
                    doc_text = results["documents"][i]
                    if doc_text:
                        print(f"  Document: {doc_text[:200]}...")

            print(f"\n--- End Dump (Total: {self.collection.count()}) ---")

        except Exception as e:
            self.logger.error(f"Failed to dump sample: {e}")
            print(f"Error: {e}")

    def shutdown(self):
        """Gracefully shutdown the MemoryManager."""
        self.logger.info("MemoryManager shutting down...")
        # ChromaDB clients clean up automatically
        self.logger.info("MemoryManager shutdown complete.")

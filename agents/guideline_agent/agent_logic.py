import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import fitz  # PyMuPDF
import requests
import re
from pathlib import Path
import tempfile

logger = logging.getLogger(__name__)

# P0: Capability constants for discovery registration
CAPABILITIES = [
    "query_guidelines",
    "retrieve_guidelines",
    "ingest_guidelines",
    "search_guidelines",
]


class GuidelineAgentLogic:
    """
    Specialized agent for ingesting and querying clinical guidelines.
    Focuses on Prior Authorization criteria extraction.
    """

    def __init__(self, agent_id: str, logger_instance: Optional[logging.Logger] = None):
        self.agent_id = agent_id
        self.logger = logger_instance or logger

        # Initialize memory manager if available
        self.memory_manager = None
        try:
            from core_infra.enhanced_memory_manager import EnhancedMemoryManager

            self.memory_manager = EnhancedMemoryManager()
            self.logger.info("EnhancedMemoryManager initialized for GuidelineAgent")
        except Exception as e:
            self.logger.warning(f"Could not initialize EnhancedMemoryManager: {e}")

        # Guidelines configuration - supporting both URLs and local files
        self.guidelines_config = {
            "AHA_HF_2022": {
                "url": "https://www.ahajournals.org/doi/pdf/10.1161/CIR.0000000000001063",
                "local_path": "data/guidelines/AHA_HF_2022.pdf",
                "name": "2022 AHA/ACC/HFSA Heart Failure Guideline",
                "focus": [
                    "SGLT2 inhibitors",
                    "heart failure",
                    "dapagliflozin",
                    "empagliflozin",
                    "canagliflozin",
                    "ertugliflozin",
                ],
            },
            "ADA_DIABETES_2023": {
                "url": "https://diabetesjournals.org/care/article-pdf/46/Supplement_1/S1/696834/dc23sint.pdf",
                "local_path": "data/guidelines/ADA_2023.pdf",
                "name": "ADA Standards of Medical Care in Diabetes 2023",
                "focus": [
                    "GLP-1 agonists",
                    "diabetes",
                    "semaglutide",
                    "liraglutide",
                    "dulaglutide",
                ],
            },
            "TEST_GUIDELINE": {
                "local_path": "data/guidelines/test_guideline.pdf",
                "name": "Test Clinical Guideline",
                "focus": ["SGLT2 inhibitors", "heart failure", "test"],
            },
        }

        self.logger.info(f"GuidelineAgentLogic initialized for {agent_id}")
        self.logger.info(f"Advertising capabilities: {CAPABILITIES}")

    def get_capabilities(self) -> List[str]:
        """Return agent capabilities for discovery"""
        return CAPABILITIES

    def _reset_collection_if_needed(self):
        """Reset collection if there's a dimension mismatch"""
        if not self.memory_manager:
            return

        try:
            # Try to get collection info
            test_embedding = [0.1] * 384  # Current embedding size

            # Try to add a test document
            try:
                self.memory_manager.collection.add(
                    ids=["test_dimension_check"],
                    embeddings=[test_embedding],
                    documents=["test"],
                    metadatas=[{"test": True}],
                )
                # If successful, delete the test
                self.memory_manager.collection.delete(ids=["test_dimension_check"])
                self.logger.debug("Collection dimension check passed")
            except Exception as e:
                error_str = str(e).lower()
                if "dimension" in error_str or "dimensionality" in error_str:
                    self.logger.warning(f"Dimension mismatch detected: {e}")
                    self.logger.warning("Recreating collection with correct dimensions...")

                    # Get ChromaDB client and collection name
                    client = self.memory_manager.chroma_client
                    collection_name = self.memory_manager.collection_name

                    # Delete existing collection
                    try:
                        client.delete_collection(name=collection_name)
                        self.logger.info(f"Deleted existing collection: {collection_name}")
                    except Exception as del_e:
                        self.logger.warning(f"Could not delete collection: {del_e}")

                    # Recreate collection
                    self.memory_manager.collection = client.create_collection(
                        name=collection_name, metadata={"hnsw:space": "cosine"}
                    )
                    self.logger.info(f"Collection '{collection_name}' recreated successfully with correct dimensions")
                else:
                    # Some other error, re-raise
                    raise

        except Exception as e:
            self.logger.error(f"Error in collection reset check: {e}")
            # Continue anyway, might work

    def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Main entry point for task processing"""
        try:
            task_type = task_data.get("task_name", "").lower()

            # ADDED: Handle "retrieve" task type for prior authorization workflows
            if "retrieve" in task_type and "guideline" in task_type:
                # Treat "retrieve guidelines" the same as "query guidelines"
                return self._handle_guideline_query(task_data)

            if "ingest" in task_type:
                return self._handle_guideline_ingestion(task_data)
            elif "query" in task_type or "search" in task_type:
                return self._handle_guideline_query(task_data)
            else:
                return {
                    "status": "FAILED",
                    "error": f"Unknown task type: {task_type}",
                    "supported_tasks": CAPABILITIES,
                    "agent_id": self.agent_id,
                }

        except Exception as e:
            self.logger.error(f"Error processing task: {e}", exc_info=True)
            return {"status": "FAILED", "error": str(e), "agent_id": self.agent_id}

    def _handle_guideline_ingestion(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Ingest a clinical guideline into memory"""
        guideline_id = task_data.get("guideline_id", "AHA_HF_2022")

        if guideline_id not in self.guidelines_config:
            return {
                "status": "FAILED",
                "error": f"Unknown guideline ID: {guideline_id}",
                "agent_id": self.agent_id,
            }

        config = self.guidelines_config[guideline_id]

        # Check if already ingested
        if self._is_guideline_ingested(guideline_id):
            return {
                "status": "COMPLETED",
                "message": f"Guideline {guideline_id} already ingested",
                "agent_id": self.agent_id,
            }

        # Load and process PDF
        try:
            pdf_content = None

            # First, check if local file exists
            local_path = Path(config["local_path"])
            if local_path.exists():
                self.logger.info(f"Using existing local file: {local_path}")
                pdf_content = self._load_local_pdf(str(local_path))
            elif "url" in config:
                # Try to download the PDF
                self.logger.info(f"Attempting to download PDF from URL: {config['url']}")
                try:
                    pdf_content = self._download_pdf(config["url"])
                    # Save for future use
                    self._save_pdf_locally(pdf_content, str(local_path))
                except Exception as download_error:
                    self.logger.warning(f"Failed to download PDF: {download_error}")
                    return {
                        "status": "FAILED",
                        "error": f"Could not download PDF from {config['url']}. Please download manually and save to: {local_path}",
                        "agent_id": self.agent_id,
                    }
            else:
                return {
                    "status": "FAILED",
                    "error": f"No local file found at {local_path} and no URL configured",
                    "agent_id": self.agent_id,
                }

            if not pdf_content:
                return {
                    "status": "FAILED",
                    "error": "Failed to load PDF content",
                    "agent_id": self.agent_id,
                }

            # Extract and chunk text
            chunks = self._extract_and_chunk_pdf(pdf_content, guideline_id)

            if not chunks:
                return {
                    "status": "FAILED",
                    "error": "No text could be extracted from the PDF",
                    "agent_id": self.agent_id,
                }

            # Store in memory
            self._store_chunks(chunks, guideline_id, config["name"])

            return {
                "status": "COMPLETED",
                "message": f"Successfully ingested {len(chunks)} chunks from {guideline_id}",
                "chunks_count": len(chunks),
                "guideline_name": config["name"],
                "agent_id": self.agent_id,
            }

        except Exception as e:
            self.logger.error(f"Failed to ingest guideline {guideline_id}: {e}")
            return {"status": "FAILED", "error": str(e), "agent_id": self.agent_id}

    def _handle_guideline_query(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Query guidelines for specific information"""
        # ENHANCED: Support multiple parameter formats
        query = task_data.get("query", "")
        drug_name = task_data.get("drug_name", "")
        condition = task_data.get("condition", "") or task_data.get("disease_name", "")

        # ADDED: Also check for 'topic' parameter (from the PA template)
        topic = task_data.get("topic", "")

        # If we have a topic but no query, use the topic as the query
        if topic and not query:
            query = topic

            # Try to extract drug and condition from topic if not provided
            if not drug_name and not condition:
                # Pattern: "Guidelines for DRUG in treating CONDITION"
                match = re.match(r"Guidelines for (.+?) in treating (.+)", topic, re.IGNORECASE)
                if match:
                    drug_name = drug_name or match.group(1).strip()
                    condition = condition or match.group(2).strip()

        # Build enhanced query
        if drug_name and condition:
            enhanced_query = f"{drug_name} for {condition} clinical guidelines recommendations"
        elif drug_name:
            enhanced_query = f"{drug_name} clinical use guidelines"
        elif condition:
            enhanced_query = f"{condition} treatment guidelines"
        else:
            enhanced_query = query

        # P0: Return RETRY if no query provided
        if not enhanced_query:
            # Check which fields are missing for better error message
            missing_fields = []
            if not topic and not query:
                missing_fields.append("topic or query")
            if not drug_name:
                missing_fields.append("drug_name")
            if not condition:
                missing_fields.append("condition/disease_name")

            return {
                "status": "RETRY",
                "missing": missing_fields,
                "message": "Missing required fields for guideline query",
                "agent_id": self.agent_id,
            }

        try:
            # P1: Auto-ingest if collection is empty
            if self.memory_manager and not self._has_any_guidelines():
                self.logger.info("No guidelines in collection, auto-ingesting default guideline...")
                ingest_result = self._handle_guideline_ingestion(
                    {"guideline_id": "AHA_HF_2022"}  # Default guideline
                )
                if ingest_result.get("status") != "COMPLETED":
                    self.logger.warning(f"Auto-ingestion failed: {ingest_result.get('error')}")

            # Search across all guidelines
            results = self._search_guidelines(enhanced_query)

            # Extract PA-relevant information
            pa_criteria = self._extract_pa_criteria(results, drug_name, condition)

            return {
                "status": "COMPLETED",
                "query": enhanced_query,
                "results": results[:5],  # Top 5 matches
                "pa_criteria": pa_criteria,
                "total_matches": len(results),
                "agent_id": self.agent_id,
            }

        except Exception as e:
            self.logger.error(f"Failed to query guidelines: {e}")
            return {"status": "FAILED", "error": str(e), "agent_id": self.agent_id}

    def _has_any_guidelines(self) -> bool:
        """Check if any guidelines are stored in the collection"""
        if not self.memory_manager:
            return False

        try:
            # Try to get any document
            results = self.memory_manager.collection.get(limit=1)
            return bool(results and results["ids"])
        except Exception as e:
            self.logger.debug(f"Error checking for guidelines: {e}")
            return False

    def _download_pdf(self, url: str) -> bytes:
        """
        Download PDF from URL using Playwright for robust browser automation
        to bypass anti-bot measures.
        """
        self.logger.info(f"Downloading PDF from {url} using Playwright...")

        # P0: Move Playwright import inside function to avoid cold-start failures
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            self.logger.warning("Playwright not installed, falling back to requests")
            return self._download_pdf_requests(url)

        try:
            with sync_playwright() as p:
                # Launch browser in headless mode
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                )
                page = context.new_page()

                # Set up download handling
                with tempfile.TemporaryDirectory() as temp_dir:
                    # Configure download directory
                    page.context.set_default_timeout(60000)  # 60 seconds timeout

                    # Navigate to the URL
                    response = page.goto(url, wait_until="networkidle")

                    # Check if it's a direct PDF download
                    content_type = response.headers.get("content-type", "")
                    if "application/pdf" in content_type:
                        # Direct PDF response
                        pdf_content = response.body()
                    else:
                        # Page might have a download button or require interaction
                        # Wait a moment for any JavaScript to execute
                        page.wait_for_timeout(3000)

                        # Try to trigger download by clicking download button if present
                        download_triggered = False
                        for selector in [
                            'a[href$=".pdf"]',
                            'button:has-text("Download")',
                            'a:has-text("PDF")',
                        ]:
                            try:
                                if page.locator(selector).count() > 0:
                                    with page.expect_download() as download_info:
                                        page.locator(selector).first.click()
                                        download = download_info.value
                                        download_path = Path(temp_dir) / download.suggested_filename
                                        download.save_as(download_path)
                                        pdf_content = download_path.read_bytes()
                                        download_triggered = True
                                        break
                            except:
                                continue

                        if not download_triggered:
                            # If no download button found, the page itself might be the PDF
                            # Try to get the page content
                            pdf_content = page.pdf()

                browser.close()

                self.logger.info(f"Successfully downloaded PDF via Playwright ({len(pdf_content)} bytes)")
                return pdf_content

        except Exception as e:
            self.logger.error(f"Playwright download failed: {e}")
            # Fallback to simple requests as last resort
            return self._download_pdf_requests(url)

    def _download_pdf_requests(self, url: str) -> bytes:
        """Download PDF using requests library as fallback"""
        self.logger.info("Downloading PDF using requests library...")
        try:
            response = requests.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                timeout=30,
            )
            response.raise_for_status()
            self.logger.info(f"Successfully downloaded PDF via requests ({len(response.content)} bytes)")
            return response.content
        except Exception as e:
            self.logger.error(f"Requests download failed: {e}")
            raise Exception(f"Failed to download PDF: {str(e)}")

    def _load_local_pdf(self, path: str) -> bytes:
        """Load PDF from local filesystem"""
        self.logger.info(f"Loading PDF from local file: {path}")
        with open(path, "rb") as f:
            return f.read()

    def _save_pdf_locally(self, pdf_content: bytes, path: str):
        """Save PDF content to local file for future use"""
        try:
            local_path = Path(path)
            local_path.parent.mkdir(parents=True, exist_ok=True)
            with open(local_path, "wb") as f:
                f.write(pdf_content)
            self.logger.info(f"Saved PDF to {local_path}")
        except Exception as e:
            self.logger.warning(f"Could not save PDF locally: {e}")

    def _extract_and_chunk_pdf(self, pdf_content: bytes, guideline_id: str) -> List[Dict[str, Any]]:
        """Extract text from PDF and create overlapping chunks"""
        chunks = []

        try:
            with fitz.open(stream=pdf_content, filetype="pdf") as doc:
                # First pass: extract all text with page numbers
                full_text = ""
                page_boundaries = []

                self.logger.info(f"Processing {len(doc)} pages from PDF")

                for page_num, page in enumerate(doc):
                    page_text = page.get_text()
                    if page_text:
                        page_boundaries.append(len(full_text))
                        full_text += f"\n[Page {page_num + 1}]\n{page_text}"

                if not full_text.strip():
                    self.logger.error("No text extracted from PDF")
                    return []

                self.logger.info(f"Extracted {len(full_text)} characters from PDF")

                # Smart chunking with overlap
                chunks = self._smart_chunk_text(full_text, page_boundaries)

                # Add metadata to each chunk
                for i, chunk in enumerate(chunks):
                    chunk["id"] = f"{guideline_id}_chunk_{i}"
                    chunk["guideline_id"] = guideline_id
                    chunk["chunk_index"] = i
                    chunk["total_chunks"] = len(chunks)

                    # Extract key concepts
                    chunk["extracted_drugs"] = self._extract_drug_names(chunk["text"])
                    chunk["extracted_conditions"] = self._extract_conditions(chunk["text"])

                self.logger.info(f"Created {len(chunks)} chunks from PDF")

        except Exception as e:
            self.logger.error(f"Error processing PDF: {e}")
            raise

        return chunks

    def _smart_chunk_text(
        self,
        text: str,
        page_boundaries: List[int],
        chunk_size: int = 500,
        overlap: int = 100,
    ) -> List[Dict[str, Any]]:
        """Create overlapping chunks with smart boundaries"""
        chunks = []

        # Split by major sections first
        section_pattern = r"\n(?:[A-Z][A-Z\s]+:|(?:^\d+\.?\s+[A-Z][A-Za-z\s]+))"
        sections = re.split(section_pattern, text)

        current_chunk = ""
        current_words = 0

        for section in sections:
            section_words = len(section.split())

            if current_words + section_words > chunk_size and current_chunk:
                # Save current chunk
                chunks.append({"text": current_chunk.strip(), "word_count": current_words})

                # Start new chunk with overlap
                overlap_text = " ".join(current_chunk.split()[-overlap:])
                current_chunk = overlap_text + " " + section
                current_words = len(current_chunk.split())
            else:
                current_chunk += "\n" + section
                current_words += section_words

        # Don't forget the last chunk
        if current_chunk.strip():
            chunks.append({"text": current_chunk.strip(), "word_count": current_words})

        return chunks

    def _extract_drug_names(self, text: str) -> List[str]:
        """Extract drug names from text"""
        drugs = []

        # Common drug patterns
        drug_patterns = [
            r"\b(empagliflozin|dapagliflozin|canagliflozin|ertugliflozin|sotagliflozin)\b",  # SGLT2
            r"\b(semaglutide|liraglutide|dulaglutide|exenatide|lixisenatide|tirzepatide)\b",  # GLP-1
            r"\b(metformin|insulin|glipizide|glyburide|pioglitazone)\b",  # Other diabetes drugs
            r"\b([A-Za-z]+(?:flozin|glutide|tide))\b",  # Generic patterns
        ]

        for pattern in drug_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            drugs.extend([m.lower() for m in matches])

        return list(set(drugs))

    def _extract_conditions(self, text: str) -> List[str]:
        """Extract medical conditions from text"""
        conditions = []

        condition_patterns = [
            r"\b(heart failure|HFrEF|HFpEF|HFmrEF)\b",
            r"\b(type [12] diabetes|T[12]DM|diabetes mellitus)\b",
            r"\b(chronic kidney disease|CKD|renal impairment)\b",
            r"\b(cardiovascular disease|CVD|ASCVD)\b",
            r"\b(hypertension|HTN|high blood pressure)\b",
        ]

        for pattern in condition_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            conditions.extend([m.lower() for m in matches])

        return list(set(conditions))

    def _is_guideline_ingested(self, guideline_id: str) -> bool:
        """Check if guideline is already in memory"""
        if not self.memory_manager:
            return False

        try:
            results = self.memory_manager.collection.get(where={"guideline_id": guideline_id}, limit=1)
            return bool(results and results["ids"])
        except:
            return False

    def _store_chunks(self, chunks: List[Dict[str, Any]], guideline_id: str, guideline_name: str):
        """Store chunks in memory"""
        if not self.memory_manager:
            self.logger.warning("Memory manager not available, skipping storage")
            return

        # Check and reset collection if there's a dimension mismatch
        self._reset_collection_if_needed()

        try:
            ids = [chunk["id"] for chunk in chunks]
            documents = [chunk["text"] for chunk in chunks]
            metadatas = [
                {
                    "guideline_id": guideline_id,
                    "guideline_name": guideline_name,
                    "chunk_index": chunk["chunk_index"],
                    "total_chunks": chunk["total_chunks"],
                    "drugs": json.dumps(chunk["extracted_drugs"]),
                    "conditions": json.dumps(chunk["extracted_conditions"]),
                    "word_count": chunk["word_count"],
                }
                for chunk in chunks
            ]

            self.memory_manager.collection.upsert(ids=ids, documents=documents, metadatas=metadatas)

            self.logger.info(f"Stored {len(chunks)} chunks for {guideline_id}")

        except Exception as e:
            self.logger.error(f"Failed to store chunks: {e}")
            raise

    def _search_guidelines(self, query: str, n_results: int = 10) -> List[Dict[str, Any]]:
        """Search across all guidelines"""
        if not self.memory_manager:
            return []

        try:
            results = self.memory_manager.collection.query(
                query_texts=[query],
                n_results=n_results,
                include=["documents", "metadatas", "distances"],
            )

            if not results or not results["ids"][0]:
                return []

            formatted_results = []
            for i in range(len(results["ids"][0])):
                formatted_results.append(
                    {
                        "id": results["ids"][0][i],
                        "text": results["documents"][0][i],
                        "guideline_id": results["metadatas"][0][i].get("guideline_id"),
                        "guideline_name": results["metadatas"][0][i].get("guideline_name"),
                        "relevance_score": 1 - results["distances"][0][i],
                        "metadata": results["metadatas"][0][i],
                    }
                )

            return formatted_results

        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            return []

    def _extract_pa_criteria(
        self, search_results: List[Dict[str, Any]], drug_name: str, condition: str
    ) -> Dict[str, Any]:
        """Extract PA-relevant criteria from search results"""
        criteria = {
            "drug": drug_name,
            "condition": condition,
            "recommendations": [],
            "contraindications": [],
            "prerequisites": [],
            "dosing_guidance": [],
            "monitoring_requirements": [],
        }

        for result in search_results[:5]:  # Increased to top 5 results for better coverage
            text = result["text"].lower()
            original_text = result["text"]

            # Look for recommendation patterns
            if any(
                keyword in text
                for keyword in [
                    "recommended",
                    "should be used",
                    "indicated for",
                    "first-line",
                    "preferred",
                ]
            ):
                if not drug_name or drug_name.lower() in text:
                    criteria["recommendations"].append(
                        {
                            "text": self._extract_sentence(original_text, drug_name),
                            "source": result["guideline_name"],
                            "relevance": result["relevance_score"],
                        }
                    )

            # Look for prerequisites
            if any(
                keyword in text
                for keyword in [
                    "prior to",
                    "before initiating",
                    "must have",
                    "requires",
                    "prerequisite",
                ]
            ):
                criteria["prerequisites"].append(
                    {
                        "text": self._extract_sentence(original_text, drug_name),
                        "source": result["guideline_name"],
                    }
                )

            # Look for contraindications
            if any(keyword in text for keyword in ["contraindicated", "should not", "avoid", "do not use"]):
                criteria["contraindications"].append(
                    {
                        "text": self._extract_sentence(original_text, drug_name),
                        "source": result["guideline_name"],
                    }
                )

            # Look for dosing guidance
            if any(
                keyword in text
                for keyword in [
                    "dose",
                    "dosing",
                    "mg",
                    "daily",
                    "twice daily",
                    "once daily",
                ]
            ):
                if not drug_name or drug_name.lower() in text:
                    criteria["dosing_guidance"].append(
                        {
                            "text": self._extract_sentence(original_text, drug_name or "dose"),
                            "source": result["guideline_name"],
                        }
                    )

            # Look for monitoring requirements
            if any(keyword in text for keyword in ["monitor", "monitoring", "assess", "follow-up", "check"]):
                criteria["monitoring_requirements"].append(
                    {
                        "text": self._extract_sentence(original_text, "monitor"),
                        "source": result["guideline_name"],
                    }
                )

        # Remove duplicates from each category
        for key in criteria:
            if isinstance(criteria[key], list) and criteria[key]:
                # Remove duplicates based on text content
                seen_texts = set()
                unique_items = []
                for item in criteria[key]:
                    if isinstance(item, dict) and "text" in item:
                        if item["text"] not in seen_texts:
                            seen_texts.add(item["text"])
                            unique_items.append(item)
                criteria[key] = unique_items

        return criteria

    def _extract_sentence(self, text: str, keyword: str) -> str:
        """Extract the most relevant sentence containing the keyword"""
        # Split by sentence endings
        sentences = re.split(r"(?<=[.!?])\s+", text)
        keyword_lower = keyword.lower() if keyword else ""

        # First, try to find sentences containing the keyword
        if keyword_lower:
            for sentence in sentences:
                if keyword_lower in sentence.lower():
                    # Clean up the sentence
                    sentence = sentence.strip()
                    # Ensure it ends with punctuation
                    if sentence and sentence[-1] not in ".!?":
                        sentence += "."
                    return sentence

        # If no keyword match, return the most substantial sentence
        for sentence in sentences:
            cleaned = sentence.strip()
            if len(cleaned) > 30:  # At least 30 characters
                if cleaned and cleaned[-1] not in ".!?":
                    cleaned += "."
                return cleaned

        # Fallback to first 200 chars
        truncated = text[:200].strip()
        if truncated and truncated[-1] not in ".!?":
            truncated += "..."
        return truncated

    def is_healthy(self) -> bool:
        """P2: Health check method - test query for metformin"""
        try:
            # Check if we have memory manager
            if not self.memory_manager:
                return False

            # Try a simple search
            test_query = "metformin"
            _ = self._search_guidelines(test_query, n_results=1)

            # We're healthy if we can search (even if no results)
            return True
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False

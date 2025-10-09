# C:\Users\rossd\Downloads\RossNetAgents\agents\research\web_research_agent\agent_logic.py
# Version: 2.0.0
# Change:
# - Modified query construction in _fetch_pubmed_data to prioritize drug_name & disease_name.
# - Expects structured inputs (drug_name, disease_name, or search_terms) from Planner.
# - Enhanced logging for the constructed PubMed query term.
# - Retains aiohttp client and existing retry/error handling.

import logging
import os
import json
import asyncio
import time
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import aiohttp

# import re # Not currently used, can be removed if not needed later

# Check for optional dependencies
try:
    from dotenv import load_dotenv

    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

    def load_dotenv(dotenv_path=None, verbose=False, override=False, interpolate=True, encoding="utf-8"):  # type: ignore
        pass


logger_wra_logic_default = logging.getLogger(__name__)


class MessageType(Enum):
    TASK_ASSIGN = "TASK_ASSIGN"
    TASK_COMPLETE = "TASK_COMPLETE"
    TASK_FAIL = "TASK_FAIL"
    DISCOVERY_ACK = "DISCOVERY_ACK"
    PONG = "PONG"


@dataclass
class PubMedArticle:
    title: str
    pmid: str
    abstract: str
    authors: Optional[List[str]] = None
    journal: Optional[str] = None
    publication_date: Optional[str] = None  # Format YYYY, YYYY Mmm, YYYY Mmm DD
    doi: Optional[str] = None


@dataclass
class SearchResult:
    query_used_for_api: str  # The actual term sent to NCBI ESearch
    articles: List[PubMedArticle]
    total_found_by_esearch: int = 0  # Count from ESearch
    search_time_ms: int = 0
    error: Optional[str] = None
    source: str = "pubmed_api"
    original_input_query: Optional[str] = None  # To store the high-level query if different


class WebResearchLogic:
    def __init__(
        self,
        agent_id: str,
        version: str,
        logger_instance: Optional[logging.Logger] = None,
    ):
        self.agent_id = agent_id
        self.version = version
        self.logger = logger_instance if logger_instance else logger_wra_logic_default
        self._load_environment()
        self.ncbi_api_key = os.getenv("NCBI_API_KEY")
        self.pubmed_use_mock = os.getenv("PUBMED_USE_MOCK", "false").lower() == "true"
        self.user_agent = f"CureViaX/{self.version} (WebResearchAgent; mailto:contact@example.com)"
        self.base_url_esearch = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        self.base_url_efetch = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

        self.max_retries = 2  # Total 3 attempts (initial + 2 retries)
        self.retry_delay_base = 3  # seconds, for exponential backoff
        self.request_timeout = 40  # Total timeout for aiohttp session calls
        self.connection_timeout = 15  # Timeout for establishing connection
        self.socket_timeout = 25  # Timeout for socket read operations
        self.asyncio_task_timeout_buffer = 5  # Buffer for asyncio.timeout wrapper

        self.rate_limit_delay = (
            0.4  # NCBI allows 3/sec without key, 10/sec with. Being conservative.
        )

        self._session: Optional[aiohttp.ClientSession] = None
        self._last_request_time = 0.0
        self.session_headers = {  # Define session headers once
            "User-Agent": self.user_agent,
            "Accept": "application/xml, text/xml, */*",  # PubMed API often returns XML
        }

        api_key_status = "Yes" if self.ncbi_api_key else "No (Rate limits apply: ~3 req/sec)"
        self.logger.info(
            f"WebResearchLogic initialized for agent {agent_id} (Version 2.0.0 - Targeted Query). "
            f"API Key Loaded: {api_key_status}, Mock Mode: {self.pubmed_use_mock}, User-Agent: {self.user_agent}"
        )

    def _load_environment(self):
        if not DOTENV_AVAILABLE:
            self.logger.warning("python-dotenv not available.")
            return
        try:
            project_root = Path(__file__).resolve().parents[3]
            dotenv_path = project_root / ".env"
            if dotenv_path.exists():
                load_dotenv(dotenv_path)
                self.logger.debug(f"Loaded .env from {dotenv_path}")
            else:
                self.logger.info("No .env found by logic.")
        except Exception as e:
            self.logger.warning(f"Error loading .env in logic: {e}")

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(
                total=self.request_timeout,
                connect=self.connection_timeout,
                sock_connect=self.connection_timeout,
                sock_read=self.socket_timeout,
            )
            connector = aiohttp.TCPConnector(
                limit=10,
                limit_per_host=5,
                ttl_dns_cache=300,
                use_dns_cache=True,
                enable_cleanup_closed=True,
                keepalive_timeout=30,
                timeout_ceil_threshold=5,
            )
            self._session = aiohttp.ClientSession(
                timeout=timeout, headers=self.session_headers, connector=connector
            )
            self.logger.debug(
                f"Created new aiohttp session for NCBI API with headers: {self.session_headers}"
            )
        return self._session

    async def _rate_limit(self):
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        if time_since_last < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - time_since_last)
        self._last_request_time = time.time()

    def _validate_search_parameters(
        self, params: Dict[str, Any]
    ) -> tuple[bool, Optional[str], str, int]:
        """Validates input parameters and constructs the PubMed query term."""
        drug_name = params.get("drug_name")
        disease_name = params.get("disease_name")
        search_terms = params.get("search_terms")  # For general keywords
        raw_query = params.get("query")  # Fallback, might be the long goal
        max_results = params.get("max_results", 10)

        pubmed_query_term = ""

        if drug_name and isinstance(drug_name, str) and drug_name.strip():
            drug_name = drug_name.strip()
            if len(drug_name) > 200:
                return False, "drug_name too long (max 200 chars).", "", 0
            pubmed_query_term += f"({drug_name}[Title/Abstract] OR {drug_name}[MeSH Terms])"

        if disease_name and isinstance(disease_name, str) and disease_name.strip():
            disease_name = disease_name.strip()
            if len(disease_name) > 200:
                return False, "disease_name too long (max 200 chars).", "", 0
            if pubmed_query_term:
                pubmed_query_term += " AND "
            # Quote disease name if it contains spaces for exact phrase matching
            disease_query_part = f'"{disease_name}"' if " " in disease_name else disease_name
            pubmed_query_term += (
                f"({disease_query_part}[Title/Abstract] OR {disease_query_part}[MeSH Terms])"
            )

        if search_terms and isinstance(search_terms, str) and search_terms.strip():
            search_terms = search_terms.strip()
            if len(search_terms) > 500:
                return False, "search_terms too long (max 500 chars).", "", 0
            if pubmed_query_term:
                pubmed_query_term += " AND "
            pubmed_query_term += (
                f"({search_terms})"  # Assume search_terms might already be structured
            )

        if not pubmed_query_term:  # Fallback to raw_query if no structured terms provided
            if raw_query and isinstance(raw_query, str) and raw_query.strip():
                raw_query = raw_query.strip()
                if len(raw_query) > 1000:
                    return False, "Fallback query too long (max 1000 chars).", "", 0
                pubmed_query_term = raw_query
                self.logger.warning(
                    f"Using raw 'query' parameter for PubMed search: '{raw_query[:100]}...'"
                )
            else:
                return (
                    False,
                    "No valid search parameters (drug_name, disease_name, search_terms, or query) provided.",
                    "",
                    0,
                )

        try:
            max_results_int = int(max_results) if max_results is not None else 3
        except (ValueError, TypeError):
            return (
                False,
                f"max_results must be int, got: {type(max_results).__name__}",
                "",
                0,
            )
        if not 1 <= max_results_int <= 50:
            return False, "max_results must be between 1 and 50", "", 0

        self.logger.info(f"Constructed PubMed API query term: '{pubmed_query_term}'")
        return True, None, pubmed_query_term, max_results_int

    def _validate_message_structure(self, message_data: Any) -> tuple[bool, Optional[str]]:
        if not isinstance(message_data, dict):
            return False, f"Message must be dict, got {type(message_data)}"
        if not isinstance(message_data.get("mcp_header"), dict):
            return False, "Missing or invalid mcp_header"
        if not isinstance(message_data.get("payload"), dict):
            return False, "Missing or invalid payload"
        return True, None

    def get_capabilities(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "perform_web_search",
                "description": "Performs PubMed searches using structured terms or a general query.",
                "parameters": {
                    "drug_name": "string (optional, drug name for targeted search)",
                    "disease_name": "string (optional, disease name for targeted search)",
                    "search_terms": "string (optional, additional keywords or structured query part)",
                    "query": "string (optional, fallback general query if other terms not provided, max 1000 chars)",
                    "max_results": "integer (optional, default 3, range 1-50)",
                },
                "features": [
                    "structured_output",
                    "retry_logic",
                    "rate_limiting",
                    "mock_data_support",
                ],
                "data_sources": ["PubMed/NCBI E-utils"],
            }
        ]

    def _create_mock_data(
        self, api_query_term: str, max_results: int, original_input_query: Optional[str]
    ) -> SearchResult:
        self.logger.warning(
            f"PUBMED_MOCK: Returning mock data for API query term: '{api_query_term[:50]}...' (Original input: '{original_input_query[:50] if original_input_query else 'N/A'}')"
        )
        mock_articles = [
            PubMedArticle(
                title=f"Mock Study 1 for {api_query_term}",
                pmid="MOCKPMID1",
                abstract=f"This is mock abstract 1 for the query: {api_query_term}.",
            ),
            PubMedArticle(
                title=f"Mock Review 2 on {api_query_term}",
                pmid="MOCKPMID2",
                abstract=f"A mock review article discussing various aspects of {api_query_term}.",
            ),
        ]
        return SearchResult(
            query_used_for_api=api_query_term,
            articles=mock_articles[:max_results],
            total_found_by_esearch=len(mock_articles),
            search_time_ms=150,
            source="mock_data",
            original_input_query=original_input_query,
        )

    async def _make_ncbi_request(self, url: str, params: Dict[str, str], description: str) -> str:
        # ... (This method remains the same robust version from "Enhanced-Timeouts-V2" / V2.4.x ClinicalTrialsAgent) ...
        # ... It should correctly handle aiohttp exceptions and re-raise standard ones ...
        session = await self._get_session()
        # Add API key if available and not already in params (though usually passed by calling function)
        if self.ncbi_api_key and "api_key" not in params:
            params_to_send = {**params, "api_key": self.ncbi_api_key}
        else:
            params_to_send = params

        last_exception: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                await self._rate_limit()
                self.logger.info(
                    f"NCBI API request (attempt {attempt + 1}/{self.max_retries + 1}): {description}"
                )
                self.logger.debug(f"  URL: {url}, Params: {params_to_send}")

                overall_attempt_timeout = self.request_timeout + self.asyncio_task_timeout_buffer
                async with asyncio.timeout(overall_attempt_timeout):
                    async with session.get(url, params=params_to_send) as response:
                        self.logger.info(f"  Response Status: {response.status} for {description}")
                        self.logger.debug(f"  Response Headers: {dict(response.headers)}")

                        if response.status >= 400:
                            error_body = "N/A"
                            try:
                                error_body = await response.text(errors="replace")
                            except Exception:
                                pass
                            err_msg_detail = f"HTTP {response.status} {response.reason}. URL: {response.request_info.url}. Body: {error_body[:500]}"
                            self.logger.error(err_msg_detail)
                            if response.status == 400:
                                current_exception = ValueError(err_msg_detail)
                            elif response.status == 401 or response.status == 403:
                                current_exception = PermissionError(err_msg_detail)
                            elif response.status == 404:
                                current_exception = FileNotFoundError(err_msg_detail)
                            elif response.status == 429 or response.status >= 500:
                                current_exception = ConnectionError(err_msg_detail)
                            else:
                                current_exception = ConnectionError(err_msg_detail)
                            last_exception = current_exception
                            if not (response.status == 429 or response.status >= 500):
                                raise current_exception
                        else:
                            content = await response.text()
                            if not content or not content.strip():
                                raise ValueError(f"Empty response from NCBI API for {description}")
                            self.logger.info(f"NCBI API request successful: {description}")
                            return content

            except asyncio.TimeoutError as e:
                last_exception = TimeoutError(
                    f"Overall task timeout on attempt {attempt + 1}: {description} - {e}"
                )
            except aiohttp.ClientTimeout as e:
                last_exception = TimeoutError(
                    f"AIOHTTP ClientTimeout on attempt {attempt + 1}: {description} - {e}"
                )
            except aiohttp.ClientConnectionError as e:
                if "Connection refused" in str(e):
                    last_exception = ConnectionRefusedError(
                        f"Connection refused by NCBI: {description} - {e}"
                    )
                else:
                    last_exception = ConnectionError(
                        f"AIOHTTP ClientConnectionError on attempt {attempt + 1}: {description} - {e}"
                    )
            except aiohttp.ContentTypeError as e:
                last_exception = ValueError(
                    f"AIOHTTP ContentTypeError on attempt {attempt + 1}: {description} - {e}"
                )
                raise last_exception  # Non-retryable
            except Exception as e:
                last_exception = RuntimeError(
                    f"Unexpected error on attempt {attempt + 1}: {description} - {type(e).__name__} - {e}"
                )

            self.logger.error(str(last_exception))
            if attempt < self.max_retries:
                if not isinstance(
                    last_exception,
                    (ConnectionError, TimeoutError, ConnectionRefusedError),
                ):
                    self.logger.error(f"Non-retryable error for {description}. Failing early.")
                    raise last_exception
                delay = self.retry_delay_base * (2**attempt)
                self.logger.warning(
                    f"Attempt {attempt+1} for {description} failed. Retrying in {delay}s..."
                )
                await asyncio.sleep(delay)
            else:
                self.logger.error(f"All {self.max_retries + 1} attempts failed for {description}.")
                if last_exception:
                    raise last_exception
                raise RuntimeError(f"All attempts failed for {description} with unspecified error.")
        # Fallback
        raise RuntimeError(f"All API request attempts failed for {description} (fallback).")

    def _parse_article_xml_details(self, pubmed_article_element: ET.Element) -> PubMedArticle:
        title_elem = pubmed_article_element.find(".//ArticleTitle")
        title = title_elem.text.strip() if title_elem is not None and title_elem.text else "N/A"

        pmid_elem = pubmed_article_element.find(".//MedlineCitation/PMID")
        pmid = pmid_elem.text.strip() if pmid_elem is not None and pmid_elem.text else "N/A"

        abstract_parts = []
        for abstract_text_node in pubmed_article_element.findall(".//Abstract/AbstractText"):
            text_content = "".join(
                abstract_text_node.itertext()
            ).strip()  # Handles mixed content like <i>
            if text_content:
                label = abstract_text_node.get("Label")
                abstract_parts.append(
                    f"**{label.strip()}:** {text_content}" if label else text_content
                )
        abstract = "\n".join(abstract_parts) if abstract_parts else "N/A"

        # Basic author parsing (can be more complex)
        authors_list = []
        author_list_node = pubmed_article_element.find(".//AuthorList")
        if author_list_node is not None:
            for author_node in author_list_node.findall(".//Author"):
                lastname_node = author_node.find("LastName")
                forename_node = author_node.find("ForeName")  # NCBI uses ForeName
                initials_node = author_node.find("Initials")
                name_parts = []
                if lastname_node is not None and lastname_node.text:
                    name_parts.append(lastname_node.text.strip())
                if forename_node is not None and forename_node.text:
                    name_parts.append(forename_node.text.strip())
                elif initials_node is not None and initials_node.text:
                    name_parts.append(initials_node.text.strip())
                if name_parts:
                    authors_list.append(" ".join(name_parts))

        journal_title_node = pubmed_article_element.find(".//Journal/Title")
        journal = (
            journal_title_node.text.strip()
            if journal_title_node is not None and journal_title_node.text
            else None
        )

        pub_date_node = pubmed_article_element.find(".//Journal/JournalIssue/PubDate")
        pub_date_str = None
        if pub_date_node is not None:
            year = pub_date_node.find("Year")
            month = pub_date_node.find("Month")
            day = pub_date_node.find("Day")
            if year is not None and year.text:
                pub_date_str = year.text.strip()
                if month is not None and month.text:
                    pub_date_str += f" {month.text.strip()}"
                    if day is not None and day.text:
                        pub_date_str += f" {day.text.strip()}"

        doi_node = pubmed_article_element.find(".//ArticleId[@IdType='doi']")
        doi = doi_node.text.strip() if doi_node is not None and doi_node.text else None

        return PubMedArticle(
            title=title,
            pmid=pmid,
            abstract=abstract,
            authors=authors_list if authors_list else None,
            journal=journal,
            publication_date=pub_date_str,
            doi=doi,
        )

    async def _fetch_pubmed_data(
        self,
        constructed_api_query_term: str,
        max_results: int,
        original_input_query_for_result: Optional[str],
    ) -> SearchResult:
        start_time_ns = time.perf_counter_ns()
        try:
            if self.pubmed_use_mock:
                return self._create_mock_data(
                    constructed_api_query_term,
                    max_results,
                    original_input_query_for_result,
                )

            self.logger.info(
                f"Searching PubMed with API term: '{constructed_api_query_term[:100]}...', max_results: {max_results}"
            )

            esearch_params = {
                "db": "pubmed",
                "term": constructed_api_query_term,
                "retmax": str(max_results),
                "usehistory": "y",
                "retmode": "xml",
            }
            search_response_xml_str = await self._make_ncbi_request(
                self.base_url_esearch,
                esearch_params,
                f"ESearch for '{constructed_api_query_term[:50]}'",
            )

            search_xml_root = ET.fromstring(search_response_xml_str)
            id_list_node = search_xml_root.find("IdList")
            article_ids = (
                [id_node.text for id_node in id_list_node.findall("Id") if id_node.text]
                if id_list_node is not None
                else []
            )

            count_node = search_xml_root.find("Count")
            total_found = int(count_node.text) if count_node is not None and count_node.text else 0

            if not article_ids:
                self.logger.info(
                    f"No PubMed article IDs found for API term: '{constructed_api_query_term}'. Total reported by ESearch: {total_found}"
                )
                articles_data = []
            else:
                self.logger.info(
                    f"Found {len(article_ids)} PubMed IDs (ESearch total: {total_found}). Fetching details..."
                )
                # Ensure we only fetch details for the number of IDs up to max_results,
                # as ESearch might return more IDs in IdList than retmax if usehistory=y is very effective.
                ids_to_fetch = article_ids[:max_results]
                efetch_params = {
                    "db": "pubmed",
                    "id": ",".join(ids_to_fetch),
                    "rettype": "abstract",
                    "retmode": "xml",
                }
                fetch_response_xml_str = await self._make_ncbi_request(
                    self.base_url_efetch,
                    efetch_params,
                    f"EFetch for {len(ids_to_fetch)} IDs",
                )
                fetch_xml_root = ET.fromstring(fetch_response_xml_str)
                articles_data = [
                    self._parse_article_xml_details(article_element)
                    for article_element in fetch_xml_root.findall(".//PubmedArticle")
                ]
                articles_data = [
                    article for article in articles_data if article is not None
                ]  # Filter out None if parsing failed for an article

            search_time_ms = (time.perf_counter_ns() - start_time_ns) // 1_000_000
            self.logger.info(
                f"Fetched {len(articles_data)} articles in {search_time_ms}ms for API term '{constructed_api_query_term[:50]}...'."
            )
            return SearchResult(
                query_used_for_api=constructed_api_query_term,
                articles=articles_data,
                total_found_by_esearch=total_found,
                search_time_ms=search_time_ms,
                original_input_query=original_input_query_for_result,
            )

        except (
            TimeoutError,
            ConnectionError,
            ConnectionRefusedError,
            RuntimeError,
            ValueError,
            PermissionError,
            FileNotFoundError,
        ) as e:
            error_msg = f"API Error in _fetch_pubmed_data for '{constructed_api_query_term[:50]}...': {type(e).__name__} - {str(e)}"
            self.logger.error(
                error_msg
            )  # No exc_info as _make_ncbi_request should have logged details
            return SearchResult(
                query_used_for_api=constructed_api_query_term,
                articles=[],
                error=error_msg,
                search_time_ms=(time.perf_counter_ns() - start_time_ns) // 1_000_000,
                original_input_query=original_input_query_for_result,
            )
        except Exception as e_unhandled:
            error_msg = f"Unexpected error in _fetch_pubmed_data for '{constructed_api_query_term[:50]}...': {type(e_unhandled).__name__} - {str(e_unhandled)}"
            self.logger.error(error_msg, exc_info=True)
            return SearchResult(
                query_used_for_api=constructed_api_query_term,
                articles=[],
                error=error_msg,
                search_time_ms=(time.perf_counter_ns() - start_time_ns) // 1_000_000,
                original_input_query=original_input_query_for_result,
            )

    async def process_message(
        self, message_data: Dict[str, Any], client: Any
    ) -> Optional[Dict[str, Any]]:
        is_valid_msg, msg_err = self._validate_message_structure(message_data)
        if not is_valid_msg:
            self.logger.error(f"Invalid message structure: {msg_err}")
            return None

        header = message_data["mcp_header"]
        payload = message_data["payload"]
        message_type_str = header.get("message_type", "UNKNOWN")
        sender_id = header.get("sender_id", "UnknownSender")
        correlation_id = header.get("correlation_id")

        try:
            message_type = MessageType(message_type_str)
        except ValueError:
            self.logger.warning(
                f"Unknown msg type '{message_type_str}' from {sender_id}. Ignoring."
            )
            return None

        if message_type == MessageType.PONG:
            self.logger.debug(f"PONG from {sender_id}")
            return None
        if message_type == MessageType.DISCOVERY_ACK:
            self.logger.info(f"Registration confirmed by {sender_id}")
            return None

        self.logger.info(
            f"Processing {message_type.value} from {sender_id} (CorrID: {correlation_id})"
        )
        if message_type == MessageType.TASK_ASSIGN:
            return await self._handle_task_assign(payload, correlation_id)
        else:
            self.logger.warning(f"Unhandled message type: {message_type.value}")
            return None

    async def _handle_task_assign(
        self, payload: Dict[str, Any], correlation_id: Optional[str]
    ) -> Dict[str, Any]:
        task_id = payload.get("task_id", "unknown_task")
        workflow_id = payload.get("workflow_id", "unknown_workflow")
        response_payload_base = {
            "workflow_id": workflow_id,
            "task_id": task_id,
            "agent_id": self.agent_id,
        }

        try:
            parameters = payload.get("parameters", {})
            if not isinstance(parameters, dict):
                error_msg = "Invalid parameters: must be a dictionary"
                self.logger.error(f"{error_msg} for task {task_id}")
                return {
                    "message_type": MessageType.TASK_FAIL.value,
                    "payload": {**response_payload_base, "error_message": error_msg},
                }

            # Pass the whole parameters dict to _validate_search_parameters
            (
                is_valid_params,
                param_err_msg,
                constructed_api_query,
                max_results_validated,
            ) = self._validate_search_parameters(parameters)

            if not is_valid_params:
                self.logger.error(f"Invalid search parameters for task {task_id}: {param_err_msg}")
                return {
                    "message_type": MessageType.TASK_FAIL.value,
                    "payload": {
                        **response_payload_base,
                        "error_message": param_err_msg,
                    },
                }

            # Store the original high-level query if it was different from the constructed one
            original_input_query = (
                parameters.get("query")
                if parameters.get("query") != constructed_api_query
                else None
            )
            if not original_input_query and (
                parameters.get("drug_name")
                or parameters.get("disease_name")
                or parameters.get("search_terms")
            ):
                # If structured terms were used, reconstruct a semblance of the original intent for logging/SearchResult
                original_input_query_parts = []
                if parameters.get("drug_name"):
                    original_input_query_parts.append(f"Drug: {parameters.get('drug_name')}")
                if parameters.get("disease_name"):
                    original_input_query_parts.append(f"Disease: {parameters.get('disease_name')}")
                if parameters.get("search_terms"):
                    original_input_query_parts.append(f"Terms: {parameters.get('search_terms')}")
                original_input_query = "; ".join(original_input_query_parts)

            self.logger.info(
                f"Performing PubMed search for task {task_id} with API term: '{constructed_api_query[:100]}...', max_results: {max_results_validated}"
            )
            search_result_obj = await self._fetch_pubmed_data(
                constructed_api_query, max_results_validated, original_input_query
            )

            if search_result_obj.error:
                self.logger.error(
                    f"PubMed search failed for task {task_id}: {search_result_obj.error}"
                )
                return {
                    "message_type": MessageType.TASK_FAIL.value,
                    "payload": {
                        **response_payload_base,
                        "error_message": search_result_obj.error,
                    },
                }

            result_data_dict = asdict(search_result_obj)  # Convert SearchResult dataclass to dict

            final_payload = {
                **response_payload_base,
                "status": "COMPLETED",
                "result": result_data_dict,
            }
            self.logger.info(
                f"PubMed search completed for task {task_id}: {len(search_result_obj.articles)} articles found (ESearch total: {search_result_obj.total_found_by_esearch})."
            )
            return {
                "message_type": MessageType.TASK_COMPLETE.value,
                "payload": final_payload,
            }

        except Exception as e:
            error_msg = f"Unexpected error in _handle_task_assign for task {task_id}: {type(e).__name__} - {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return {
                "message_type": MessageType.TASK_FAIL.value,
                "payload": {**response_payload_base, "error_message": error_msg},
            }

    async def shutdown(self):
        self.logger.info(f"WebResearchLogic shutting down for agent {self.agent_id}")
        if self._session and not self._session.closed:
            await self._session.close()
            self.logger.debug("aiohttp ClientSession closed during shutdown.")
        self.logger.info(f"WebResearchLogic shutdown complete for agent {self.agent_id}")

    def get_status(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "version": self.version,
            "mock_mode": self.pubmed_use_mock,
            "session_active": self._session is not None and not self._session.closed,
            "last_request_timestamp": self._last_request_time,
        }

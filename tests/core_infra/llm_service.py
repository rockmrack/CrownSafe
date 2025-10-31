import asyncio
import concurrent.futures
import hashlib
import json
import logging
import os
import re
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Try to import various LLM libraries with proper error handling
AVAILABLE_PROVIDERS = {}

try:
    from openai import AsyncOpenAI, OpenAI

    AVAILABLE_PROVIDERS["openai"] = "new"
    logger.info("OpenAI library (v1.0+) available")
except ImportError:
    try:
        import openai

        AVAILABLE_PROVIDERS["openai"] = "old"
        logger.info("OpenAI library (legacy) available")
    except ImportError:
        logger.warning("OpenAI library not installed. Install with: pip install openai")

try:
    import anthropic

    AVAILABLE_PROVIDERS["anthropic"] = True
    logger.info("Anthropic library available")
except ImportError:
    logger.warning("Anthropic library not installed. Install with: pip install anthropic")

try:
    import google.generativeai as genai

    AVAILABLE_PROVIDERS["google"] = True
    logger.info("Google AI library available")
except ImportError:
    logger.warning("Google AI library not installed. Install with: pip install google-generativeai")


class LLMProvider(Enum):
    """Supported LLM providers"""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE = "azure"
    GOOGLE = "google"
    COHERE = "cohere"
    LOCAL = "local"
    MOCK = "mock"


@dataclass
class LLMConfig:
    """Comprehensive configuration for LLM client"""

    provider: Union[LLMProvider, str] = "mock"  # Default to mock for testing
    model: str = "gpt-4-turbo"
    temperature: float = 0.1
    max_tokens: int = 2000
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    api_version: Optional[str] = None
    organization: Optional[str] = None

    # Advanced settings
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stop_sequences: List[str] = field(default_factory=list)

    # Rate limiting
    requests_per_minute: int = 60
    tokens_per_minute: int = 90000

    # Caching
    enable_caching: bool = True
    cache_ttl_seconds: int = 3600

    # Monitoring
    enable_monitoring: bool = True
    log_requests: bool = False
    log_responses: bool = False

    def __post_init__(self):
        # Convert string to enum if needed
        if isinstance(self.provider, str):
            try:
                self.provider = LLMProvider(self.provider.lower())
            except ValueError:
                logger.warning(f"Unknown provider '{self.provider}', defaulting to MOCK")
                self.provider = LLMProvider.MOCK


@dataclass
class LLMResponse:
    """Structured LLM response"""

    content: str
    model: str
    provider: str
    usage: Dict[str, int]
    latency_ms: float
    cached: bool = False
    finish_reason: str = "stop"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMMetrics:
    """Metrics tracking for LLM usage"""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_tokens: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_cost: float = 0.0
    total_latency_ms: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    errors_by_type: Dict[str, int] = field(default_factory=dict)
    requests_by_model: Dict[str, int] = field(default_factory=dict)


class LLMRateLimiter:
    """Advanced rate limiter with token tracking"""

    def __init__(self, requests_per_minute: int = 60, tokens_per_minute: int = 90000):
        self.requests_per_minute = requests_per_minute
        self.tokens_per_minute = tokens_per_minute
        self.request_times = deque()
        self.token_usage = deque()
        self.lock = threading.Lock()

    def check_limits(self, estimated_tokens: int = 1000) -> tuple[bool, float]:
        """Check if request can proceed, return (can_proceed, wait_time)"""
        with self.lock:
            now = time.time()

            # Clean old entries
            self.request_times = deque(t for t in self.request_times if now - t < 60)
            self.token_usage = deque((t, tokens) for t, tokens in self.token_usage if now - t < 60)

            # Check request limit
            if len(self.request_times) >= self.requests_per_minute:
                wait_time = 60 - (now - self.request_times[0])
                return False, wait_time

            # Check token limit
            current_tokens = sum(tokens for _, tokens in self.token_usage)
            if current_tokens + estimated_tokens > self.tokens_per_minute:
                # Find when we'll have enough token budget
                tokens_to_free = (current_tokens + estimated_tokens) - self.tokens_per_minute
                accumulated = 0
                for t, tokens in self.token_usage:
                    accumulated += tokens
                    if accumulated >= tokens_to_free:
                        wait_time = 60 - (now - t)
                        return False, wait_time

            return True, 0

    def record_usage(self, tokens_used: int):
        """Record actual token usage"""
        with self.lock:
            now = time.time()
            self.request_times.append(now)
            self.token_usage.append((now, tokens_used))


class LLMCache:
    """Response cache with TTL and size limits"""

    def __init__(self, ttl_seconds: int = 3600, max_size: int = 1000):
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self.cache = {}
        self.access_times = {}
        self.lock = threading.Lock()

    def _generate_key(
        self,
        provider: str,
        model: str,
        messages: List[Dict],
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Generate cache key from request parameters"""
        key_data = {
            "provider": provider,
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """Get cached response if valid"""
        with self.lock:
            if key not in self.cache:
                return None

            # Check TTL
            if time.time() - self.access_times[key] > self.ttl_seconds:
                del self.cache[key]
                del self.access_times[key]
                return None

            # Update access time
            self.access_times[key] = time.time()
            return self.cache[key]

    def set(self, key: str, value: Any):
        """Set cache entry with TTL"""
        with self.lock:
            # Implement LRU if at capacity
            if len(self.cache) >= self.max_size:
                # Remove oldest entry
                oldest_key = min(self.access_times, key=self.access_times.get)
                del self.cache[oldest_key]
                del self.access_times[oldest_key]

            self.cache[key] = value
            self.access_times[key] = time.time()


class MockLLMProvider:
    """Sophisticated mock provider for testing"""

    def __init__(self, config: LLMConfig):
        self.config = config
        self.call_count = 0

    def generate_response(self, messages: List[Dict], **kwargs) -> LLMResponse:
        """Generate mock response based on context"""
        self.call_count += 1

        # Analyze the messages to determine response type
        message_text = " ".join(msg.get("content", "") for msg in messages)

        # Default template
        template = {
            "approval_likelihood_percent": 50,
            "decision_prediction": "Pend for More Info",
            "confidence_score": 0.5,
            "clinical_rationale": "Insufficient data for determination",
            "key_supporting_factors": [],
            "key_opposing_factors": [],
            "identified_gaps": ["Complete clinical documentation needed"],
            "recommended_next_steps": ["Gather additional information"],
        }

        # Check for patient IDs more robustly
        message_lower = message_text.lower()

        # Debug logging
        logger.debug("MockLLMProvider analyzing message for patient detection...")

        # Detect patient IDs with multiple patterns
        is_patient_001 = any(
            [
                "patient-001" in message_lower,
                "patient_001" in message_lower,
                '"patient_id": "patient-001"' in message_text,
                '"patient_id":"patient-001"' in message_text,
                "PA_patient-001" in message_text,
            ]
        )

        is_patient_002 = any(
            [
                "patient-002" in message_lower,
                "patient_002" in message_lower,
                '"patient_id": "patient-002"' in message_text,
                '"patient_id":"patient-002"' in message_text,
                "PA_patient-002" in message_text,
            ]
        )

        is_patient_003 = any(
            [
                "patient-003" in message_lower,
                "patient_003" in message_lower,
                '"patient_id": "patient-003"' in message_text,
                '"patient_id":"patient-003"' in message_text,
                "PA_patient-003" in message_text,
            ]
        )

        # Extract score if present
        score_patterns = [
            r"[Ss]core\s*[=:]\s*([\d.]+)%",
            r"[Pp]reliminary\s+[Ss]core\s*[=:]\s*([\d.]+)%",
            r"[Ss]core\s*[=:]\s*([\d.]+)",
            r"[Aa]ssessment.*?[Ss]core\s*[=:]\s*([\d.]+)%",
            r"[Cc]onfidence\s*[=:]\s*([\d.]+)%",
        ]

        score_found = None
        for pattern in score_patterns:
            score_match = re.search(pattern, message_text, re.IGNORECASE)
            if score_match:
                score_value = float(score_match.group(1))
                if score_value > 1:
                    score_found = score_value / 100
                else:
                    score_found = score_value
                break

        # Apply patient-specific logic
        if is_patient_001:
            logger.debug("Detected patient-001 - should be approved")
            template = {
                "approval_likelihood_percent": 92,
                "decision_prediction": "Approve",
                "confidence_score": 0.88,
                "clinical_rationale": "Patient demonstrates clear medical necessity: documented metformin failure with persistent hyperglycemia (HbA1c 9.2%) despite maximum therapy. Endocrinologist management supports appropriate escalation to SGLT2 inhibitor therapy per ADA guidelines.",
                "key_supporting_factors": [
                    "Failed metformin at maximum dose",
                    "HbA1c 9.2% significantly above target",
                    "Specialist (endocrinologist) oversight",
                    "Good medication adherence (92%)",
                    "Preserved renal function (eGFR 85)",
                ],
                "key_opposing_factors": [],
                "identified_gaps": [],
                "recommended_next_steps": [
                    "Initiate empagliflozin 10mg daily",
                    "Monitor renal function in 3 months",
                ],
            }

        elif is_patient_002:
            logger.debug("Detected patient-002 - should be denied")
            # Patient-002 ALWAYS gets denied - no medication history
            template = {
                "approval_likelihood_percent": 8,
                "decision_prediction": "Deny",
                "confidence_score": 0.95,
                "clinical_rationale": "Patient has not satisfied step therapy requirements. As newly diagnosed T2DM with HbA1c 7.8%, patient should first trial metformin as first-line therapy per clinical guidelines and insurance policy requirements.",
                "key_supporting_factors": [],
                "key_opposing_factors": [
                    "No prior medication trials documented",
                    "Step therapy requirements not met",
                    "HbA1c 7.8% may respond to metformin alone",
                    "Primary care management appropriate at this stage",
                ],
                "identified_gaps": ["Metformin trial required"],
                "recommended_next_steps": [
                    "Initiate metformin 500mg BID, titrate to effect",
                    "Recheck HbA1c in 3 months",
                    "Consider SGLT2 inhibitor if HbA1c remains >7.5% on metformin",
                ],
            }

        elif is_patient_003:
            logger.debug("Detected patient-003 - should be denied (wrong diagnosis)")
            template = {
                "approval_likelihood_percent": 0,
                "decision_prediction": "Deny",
                "confidence_score": 0.99,
                "clinical_rationale": "Empagliflozin is not indicated for patient's diagnosed conditions (GERD, GI bleeding). This SGLT2 inhibitor is FDA-approved only for T2DM, heart failure, and CKD. No diabetes diagnosis present.",
                "key_supporting_factors": [],
                "key_opposing_factors": [
                    "No diabetes diagnosis (ICD-10 E11)",
                    "Drug not indicated for GERD",
                    "Potential safety concern with GI bleeding history",
                ],
                "identified_gaps": [],
                "recommended_next_steps": [
                    "Discontinue PA request",
                    "Continue current GERD management",
                ],
            }

        # If no specific patient but we have a score, use score-based logic
        elif score_found is not None:
            logger.debug(f"No specific patient detected, using score-based logic: {score_found:.2f}")
            if score_found > 0.75:
                template["approval_likelihood_percent"] = int(score_found * 100)
                template["decision_prediction"] = "Approve"
                template["confidence_score"] = min(0.9, score_found)
                template["clinical_rationale"] = (
                    f"High evidence score ({score_found:.0%}) strongly supports approval based on clinical criteria."
                )
            elif score_found < 0.25:
                template["approval_likelihood_percent"] = int(score_found * 100)
                template["decision_prediction"] = "Deny"
                template["confidence_score"] = min(0.9, 1 - score_found)
                template["clinical_rationale"] = (
                    f"Low evidence score ({score_found:.0%}) indicates multiple unmet criteria. Step therapy or other requirements not satisfied."
                )
            else:
                template["approval_likelihood_percent"] = int(score_found * 100)
                template["confidence_score"] = 0.5 + abs(score_found - 0.5) * 0.5

        # Log what we're returning
        logger.debug(
            f"MockLLMProvider returning: {template['decision_prediction']} with {template['approval_likelihood_percent']}% likelihood"
        )

        # Simulate processing time
        time.sleep(0.05)  # 50ms

        # Format response based on requested format
        if kwargs.get("response_format", {}).get("type") == "json_object":
            content = json.dumps(template)
        else:
            content = str(template)

        return LLMResponse(
            content=content,
            model=self.config.model,
            provider="mock",
            usage={
                "prompt_tokens": len(message_text.split()),
                "completion_tokens": len(content.split()),
                "total_tokens": len(message_text.split()) + len(content.split()),
            },
            latency_ms=50,
            cached=False,
            metadata={"mock": True, "call_count": self.call_count},
        )


class LLMClient:
    """Unified LLM client with comprehensive features"""

    def __init__(self, config: LLMConfig):
        self.config = config
        self.metrics = LLMMetrics()
        self.rate_limiter = LLMRateLimiter(config.requests_per_minute, config.tokens_per_minute)
        self.cache = LLMCache(config.cache_ttl_seconds) if config.enable_caching else None

        # Initialize provider
        self._provider = None
        self._async_provider = None
        self._mock_provider = MockLLMProvider(config)

        # Initialize based on provider
        self._initialize_provider()

        # Monitoring
        self._request_id = 0
        self._lock = threading.Lock()

        logger.info(f"LLMClient initialized with provider: {config.provider.value}, model: {config.model}")

    def _initialize_provider(self):
        """Initialize the appropriate provider client"""
        load_dotenv()

        if self.config.provider == LLMProvider.MOCK:
            logger.info("Using mock LLM provider")
            return

        api_key = self.config.api_key or os.getenv(f"{self.config.provider.value.upper()}_API_KEY")

        if not api_key and self.config.provider != LLMProvider.MOCK:
            logger.warning(f"No API key found for {self.config.provider.value}, falling back to mock provider")
            self.config.provider = LLMProvider.MOCK
            return

        try:
            if self.config.provider == LLMProvider.OPENAI:
                self._initialize_openai(api_key)
            elif self.config.provider == LLMProvider.ANTHROPIC:
                self._initialize_anthropic(api_key)
            elif self.config.provider == LLMProvider.AZURE:
                self._initialize_azure(api_key)
            elif self.config.provider == LLMProvider.GOOGLE:
                self._initialize_google(api_key)
            else:
                raise ValueError(f"Unsupported provider: {self.config.provider}")

        except Exception as e:
            logger.error(f"Failed to initialize {self.config.provider.value}: {e}")
            logger.warning("Falling back to mock provider")
            self.config.provider = LLMProvider.MOCK

    def _initialize_openai(self, api_key: str):
        """Initialize OpenAI provider"""
        if "openai" not in AVAILABLE_PROVIDERS:
            raise ImportError("OpenAI library not available")

        if AVAILABLE_PROVIDERS["openai"] == "new":
            # New OpenAI client (v1.0+)
            self._provider = OpenAI(
                api_key=api_key,
                organization=self.config.organization,
                base_url=self.config.api_base,
                timeout=self.config.timeout,
                max_retries=self.config.max_retries,
            )
            self._async_provider = AsyncOpenAI(
                api_key=api_key,
                organization=self.config.organization,
                base_url=self.config.api_base,
                timeout=self.config.timeout,
                max_retries=self.config.max_retries,
            )
        else:
            # Legacy OpenAI
            import openai

            openai.api_key = api_key
            if self.config.organization:
                openai.organization = self.config.organization
            if self.config.api_base:
                openai.api_base = self.config.api_base
            self._provider = openai

    def _initialize_anthropic(self, api_key: str):
        """Initialize Anthropic provider"""
        if "anthropic" not in AVAILABLE_PROVIDERS:
            raise ImportError("Anthropic library not available")

        import anthropic

        self._provider = anthropic.Anthropic(api_key=api_key)
        self._async_provider = anthropic.AsyncAnthropic(api_key=api_key)

    def _initialize_azure(self, api_key: str):
        """Initialize Azure OpenAI provider"""
        if "openai" not in AVAILABLE_PROVIDERS:
            raise ImportError("OpenAI library not available (required for Azure)")

        api_base = self.config.api_base or os.getenv("AZURE_OPENAI_ENDPOINT")
        api_version = self.config.api_version or "2024-02-15-preview"

        if not api_base:
            raise ValueError("Azure OpenAI endpoint not provided")

        if AVAILABLE_PROVIDERS["openai"] == "new":
            from openai import AzureOpenAI

            self._provider = AzureOpenAI(api_key=api_key, api_version=api_version, azure_endpoint=api_base)
        else:
            import openai

            openai.api_type = "azure"
            openai.api_key = api_key
            openai.api_base = api_base
            openai.api_version = api_version
            self._provider = openai

    def _initialize_google(self, api_key: str):
        """Initialize Google AI provider"""
        if "google" not in AVAILABLE_PROVIDERS:
            raise ImportError("Google AI library not available")

        import google.generativeai as genai

        genai.configure(api_key=api_key)
        self._provider = genai

    @property
    def chat(self):
        """Get chat interface"""
        return self

    @property
    def completions(self):
        """Get completions interface"""
        return self

    def create(self, **kwargs) -> Any:
        """Sync chat completion with proper event loop handling"""
        # Try to get the current event loop
        try:
            loop = asyncio.get_running_loop()
            # We're in an async context with a running loop
            # Need to run in a thread to avoid conflict

            def run_in_thread():
                # Create a new event loop for this thread
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(self.acreate(**kwargs))
                finally:
                    new_loop.close()
                    asyncio.set_event_loop(None)

            # Run in a thread pool
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(run_in_thread)
                return future.result(timeout=self.config.timeout)

        except RuntimeError:
            # No running loop - we can create one normally
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self.acreate(**kwargs))
            finally:
                loop.close()
                asyncio.set_event_loop(None)

    async def acreate(self, **kwargs) -> Any:
        """Async chat completion with all features"""
        request_id = self._get_request_id()
        start_time = time.time()

        try:
            # Check rate limits
            estimated_tokens = self._estimate_tokens(kwargs.get("messages", []))
            can_proceed, wait_time = self.rate_limiter.check_limits(estimated_tokens)

            if not can_proceed:
                logger.warning(f"Rate limit reached, waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)

            # Check cache
            cache_key = None
            if self.cache and self.config.enable_caching:
                cache_key = self.cache._generate_key(
                    self.config.provider.value,
                    kwargs.get("model", self.config.model),
                    kwargs.get("messages", []),
                    kwargs.get("temperature", self.config.temperature),
                    kwargs.get("max_tokens", self.config.max_tokens),
                )

                cached_response = self.cache.get(cache_key)
                if cached_response:
                    self.metrics.cache_hits += 1
                    logger.debug(f"Cache hit for request {request_id}")
                    return cached_response

                self.metrics.cache_misses += 1

            # Log request if enabled
            if self.config.log_requests:
                logger.info(f"LLM Request {request_id}: {json.dumps(kwargs, indent=2)}")

            # Make actual request
            response = await self._make_async_request(**kwargs)

            # Record metrics
            latency_ms = (time.time() - start_time) * 1000
            self._record_metrics(response, latency_ms, kwargs.get("model", self.config.model))

            # Cache response
            if self.cache and self.config.enable_caching and cache_key:
                self.cache.set(cache_key, response)

            # Log response if enabled
            if self.config.log_responses:
                logger.info(f"LLM Response {request_id}: {response}")

            return response

        except Exception as e:
            self.metrics.failed_requests += 1
            error_type = type(e).__name__
            self.metrics.errors_by_type[error_type] = self.metrics.errors_by_type.get(error_type, 0) + 1
            logger.error(f"LLM request {request_id} failed: {e}")
            raise

    async def _make_async_request(self, **kwargs) -> Any:
        """Make actual API request based on provider"""
        if self.config.provider == LLMProvider.MOCK:
            # Extract messages from kwargs to avoid duplicate argument error
            messages = kwargs.pop("messages", [])
            mock_response = self._mock_provider.generate_response(messages, **kwargs)
            return self._wrap_response(mock_response)

        # Set default parameters
        params = {
            "model": kwargs.get("model", self.config.model),
            "messages": kwargs.get("messages", []),
            "temperature": kwargs.get("temperature", self.config.temperature),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "top_p": kwargs.get("top_p", self.config.top_p),
            "frequency_penalty": kwargs.get("frequency_penalty", self.config.frequency_penalty),
            "presence_penalty": kwargs.get("presence_penalty", self.config.presence_penalty),
        }

        if self.config.stop_sequences:
            params["stop"] = self.config.stop_sequences

        if "response_format" in kwargs:
            params["response_format"] = kwargs["response_format"]

        # Provider-specific request handling
        if self.config.provider == LLMProvider.OPENAI and self._async_provider:
            response = await self._async_provider.chat.completions.create(**params)
            return response
        elif self.config.provider == LLMProvider.ANTHROPIC and self._async_provider:
            # Convert to Anthropic format
            anthropic_params = self._convert_to_anthropic_format(params)
            response = await self._async_provider.messages.create(**anthropic_params)
            return self._convert_from_anthropic_format(response)
        else:
            # Fallback to sync call in thread
            return await asyncio.to_thread(self._make_sync_request, **params)

    def _make_sync_request(self, **params) -> Any:
        """Make synchronous API request"""
        if self.config.provider == LLMProvider.OPENAI:
            if AVAILABLE_PROVIDERS.get("openai") == "new":
                return self._provider.chat.completions.create(**params)
            else:
                # Legacy OpenAI
                response = self._provider.ChatCompletion.create(**params)
                return self._convert_legacy_openai_response(response)

        elif self.config.provider == LLMProvider.ANTHROPIC:
            anthropic_params = self._convert_to_anthropic_format(params)
            response = self._provider.messages.create(**anthropic_params)
            return self._convert_from_anthropic_format(response)

        else:
            raise ValueError(f"Sync request not implemented for {self.config.provider}")

    def _wrap_response(self, llm_response: LLMResponse) -> Any:
        """Wrap LLMResponse in OpenAI-compatible format"""

        class WrappedResponse:
            class Choice:
                class Message:
                    def __init__(self, content):
                        self.content = content

                def __init__(self, content):
                    self.message = self.Message(content)
                    self.finish_reason = "stop"

            class Usage:
                def __init__(self, usage_dict):
                    self.prompt_tokens = usage_dict.get("prompt_tokens", 0)
                    self.completion_tokens = usage_dict.get("completion_tokens", 0)
                    self.total_tokens = usage_dict.get("total_tokens", 0)

            def __init__(self, llm_response):
                self.choices = [self.Choice(llm_response.content)]
                self.usage = self.Usage(llm_response.usage)
                self.model = llm_response.model
                self.id = f"mock-{int(time.time())}"

        return WrappedResponse(llm_response)

    def _convert_to_anthropic_format(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Convert OpenAI format to Anthropic format"""
        messages = params["messages"]
        system_message = ""
        user_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                user_messages.append({"role": msg["role"], "content": msg["content"]})

        anthropic_params = {
            "model": params["model"],
            "messages": user_messages,
            "max_tokens": params["max_tokens"],
            "temperature": params["temperature"],
            "top_p": params["top_p"],
        }

        if system_message:
            anthropic_params["system"] = system_message

        return anthropic_params

    def _convert_from_anthropic_format(self, response) -> Any:
        """Convert Anthropic response to OpenAI format"""

        class ConvertedResponse:
            class Choice:
                class Message:
                    def __init__(self, content):
                        self.content = content

                def __init__(self, content):
                    self.message = self.Message(content)
                    self.finish_reason = "stop"

            class Usage:
                def __init__(self, input_tokens, output_tokens):
                    self.prompt_tokens = input_tokens
                    self.completion_tokens = output_tokens
                    self.total_tokens = input_tokens + output_tokens

            def __init__(self, anthropic_response):
                content = anthropic_response.content[0].text if anthropic_response.content else ""
                self.choices = [self.Choice(content)]
                self.usage = self.Usage(
                    anthropic_response.usage.input_tokens,
                    anthropic_response.usage.output_tokens,
                )
                self.model = anthropic_response.model
                self.id = anthropic_response.id

        return ConvertedResponse(response)

    def _convert_legacy_openai_response(self, response: Dict) -> Any:
        """Convert legacy OpenAI response to new format"""

        class ConvertedResponse:
            class Choice:
                class Message:
                    def __init__(self, content):
                        self.content = content

                def __init__(self, choice_data):
                    self.message = self.Message(choice_data["message"]["content"])
                    self.finish_reason = choice_data.get("finish_reason", "stop")

            class Usage:
                def __init__(self, usage_data):
                    self.prompt_tokens = usage_data.get("prompt_tokens", 0)
                    self.completion_tokens = usage_data.get("completion_tokens", 0)
                    self.total_tokens = usage_data.get("total_tokens", 0)

            def __init__(self, response_data):
                self.choices = [self.Choice(choice) for choice in response_data["choices"]]
                self.usage = self.Usage(response_data.get("usage", {}))
                self.model = response_data.get("model", "unknown")
                self.id = response_data.get("id", f"legacy-{int(time.time())}")

        return ConvertedResponse(response)

    def _estimate_tokens(self, messages: List[Dict[str, Any]]) -> int:
        """Estimate token count for messages"""
        # Simple estimation: ~4 characters per token
        total_chars = sum(len(msg.get("content", "")) for msg in messages)
        return max(int(total_chars / 4), 100)

    def _record_metrics(self, response: Any, latency_ms: float, model: str):
        """Record metrics from response"""
        self.metrics.total_requests += 1
        self.metrics.successful_requests += 1
        self.metrics.total_latency_ms += latency_ms

        if hasattr(response, "usage"):
            usage = response.usage
            tokens_used = usage.total_tokens
            self.metrics.total_tokens += tokens_used
            self.metrics.total_prompt_tokens += usage.prompt_tokens
            self.metrics.total_completion_tokens += usage.completion_tokens

            # Record rate limiter usage
            self.rate_limiter.record_usage(tokens_used)

            # Estimate cost
            self.metrics.total_cost += self._estimate_cost(tokens_used, model)

        # Track by model
        self.metrics.requests_by_model[model] = self.metrics.requests_by_model.get(model, 0) + 1

    def _estimate_cost(self, tokens: int, model: str) -> float:
        """Estimate cost based on token usage"""
        # Cost per 1K tokens (approximate)
        cost_map = {
            "gpt-4-turbo": 0.01,
            "gpt-4": 0.03,
            "gpt-3.5-turbo": 0.0015,
            "claude-3-opus": 0.015,
            "claude-3-sonnet": 0.003,
            "claude-2": 0.008,
            "gemini-pro": 0.00025,
        }

        # Find matching cost
        for model_prefix, cost_per_1k in cost_map.items():
            if model_prefix in model.lower():
                return (tokens / 1000) * cost_per_1k

        # Default cost
        return (tokens / 1000) * 0.01

    def _get_request_id(self) -> str:
        """Generate unique request ID"""
        with self._lock:
            self._request_id += 1
            return f"req_{self._request_id}_{int(time.time() * 1000)}"

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        return {
            "total_requests": self.metrics.total_requests,
            "successful_requests": self.metrics.successful_requests,
            "failed_requests": self.metrics.failed_requests,
            "success_rate": self.metrics.successful_requests / max(self.metrics.total_requests, 1),
            "total_tokens": self.metrics.total_tokens,
            "total_cost": f"${self.metrics.total_cost:.2f}",
            "average_latency_ms": self.metrics.total_latency_ms / max(self.metrics.successful_requests, 1),
            "cache_hit_rate": self.metrics.cache_hits / max(self.metrics.cache_hits + self.metrics.cache_misses, 1),
            "errors": dict(self.metrics.errors_by_type),
            "models": dict(self.metrics.requests_by_model),
        }


# Global client registry
_client_registry: Dict[str, LLMClient] = {}
_registry_lock = threading.Lock()


def get_llm_client(config: Optional[LLMConfig] = None) -> LLMClient:
    """Get or create LLM client with advanced caching"""
    if config is None:
        config = LLMConfig()

    # Generate unique key for this configuration
    config_key = f"{config.provider.value}:{config.model}:{config.temperature}:{config.max_tokens}"

    with _registry_lock:
        if config_key not in _client_registry:
            _client_registry[config_key] = LLMClient(config)
            logger.info(f"Created new LLM client: {config_key}")

        return _client_registry[config_key]


def get_all_metrics() -> Dict[str, Any]:
    """Get metrics for all clients"""
    with _registry_lock:
        return {client_key: client.get_metrics() for client_key, client in _client_registry.items()}


# Utility functions
def build_structured_prompt(sections: Dict[str, Any], separator: str = "\n" + "=" * 50 + "\n") -> str:
    """Build a structured prompt from sections"""
    prompt_parts = []

    for section_name, content in sections.items():
        header = f"=== {section_name.upper()} ==="
        prompt_parts.append(header)

        if isinstance(content, (dict, list)):
            prompt_parts.append(json.dumps(content, indent=2))
        else:
            prompt_parts.append(str(content))

        prompt_parts.append("")  # Empty line after each section

    return separator.join(prompt_parts)


def parse_llm_json_response(response_text: str, strict: bool = False) -> Dict[str, Any]:
    """Safely parse JSON from LLM response with multiple strategies"""
    # Strategy 1: Direct JSON parsing
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        if strict:
            raise

    # Strategy 2: Extract from markdown code blocks
    # Try ```json blocks
    json_match = re.search(r"```json\s*(.*?)\s*```", response_text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            if strict:
                raise

    # Try ``` blocks without json marker
    code_match = re.search(r"```\s*(.*?)\s*```", response_text, re.DOTALL)
    if code_match:
        try:
            return json.loads(code_match.group(1))
        except json.JSONDecodeError:
            if strict:
                raise

    # Strategy 3: Find JSON-like structure
    json_pattern = re.search(r"\{[^{}]*\{[^{}]*\}[^{}]*\}|\{[^{}]+\}", response_text, re.DOTALL)
    if json_pattern:
        try:
            return json.loads(json_pattern.group(0))
        except json.JSONDecodeError:
            if strict:
                raise

    # Strategy 4: Try to fix common issues
    # Remove trailing commas
    fixed_text = re.sub(r",\s*}", "}", response_text)
    fixed_text = re.sub(r",\s*]", "]", fixed_text)

    # Try to find and parse JSON structure
    start_idx = fixed_text.find("{")
    if start_idx != -1:
        bracket_count = 0
        end_idx = start_idx

        for i in range(start_idx, len(fixed_text)):
            if fixed_text[i] == "{":
                bracket_count += 1
            elif fixed_text[i] == "}":
                bracket_count -= 1
                if bracket_count == 0:
                    end_idx = i + 1
                    break

        if end_idx > start_idx:
            try:
                return json.loads(fixed_text[start_idx:end_idx])
            except json.JSONDecodeError:
                if strict:
                    raise

    # If all strategies fail
    error_msg = f"Could not parse JSON from response: {response_text[:200]}..."
    logger.error(error_msg)

    if strict:
        raise ValueError(error_msg)

    # Return a default structure
    return {"error": "Failed to parse LLM response", "raw_response": response_text}


def estimate_tokens(text: str, model: str = "gpt-4") -> int:
    """Estimate token count for text"""
    # More accurate estimation based on model
    if "gpt" in model.lower():
        # GPT models: ~4 characters per token for English
        return max(int(len(text) / 4), 1)
    elif "claude" in model.lower():
        # Claude: similar to GPT
        return max(int(len(text) / 4), 1)
    else:
        # Conservative estimate
        return max(int(len(text) / 3), 1)


class LLMStreamHandler:
    """Handler for streaming responses"""

    def __init__(self, callback: Optional[Callable[[str], None]] = None):
        self.callback = callback or print
        self.accumulated_text = ""

    def __call__(self, chunk: str):
        self.accumulated_text += chunk
        if self.callback:
            self.callback(chunk)


# Cost tracking utilities
class CostTracker:
    """Track and analyze LLM costs"""

    def __init__(self):
        self.sessions = {}
        self.current_session = None

    def start_session(self, session_name: str):
        """Start a new cost tracking session"""
        self.current_session = session_name
        self.sessions[session_name] = {
            "start_time": datetime.now(timezone.utc),
            "requests": 0,
            "tokens": 0,
            "cost": 0.0,
        }

    def record_usage(self, tokens: int, cost: float):
        """Record usage for current session"""
        if self.current_session and self.current_session in self.sessions:
            session = self.sessions[self.current_session]
            session["requests"] += 1
            session["tokens"] += tokens
            session["cost"] += cost

    def get_session_report(self, session_name: str) -> Dict[str, Any]:
        """Get report for a specific session"""
        if session_name not in self.sessions:
            return {"error": f"Session '{session_name}' not found"}

        session = self.sessions[session_name]
        duration = (datetime.now(timezone.utc) - session["start_time"]).total_seconds()

        return {
            "session_name": session_name,
            "duration_seconds": duration,
            "total_requests": session["requests"],
            "total_tokens": session["tokens"],
            "total_cost": f"${session['cost']:.4f}",
            "avg_tokens_per_request": session["tokens"] / max(session["requests"], 1),
            "avg_cost_per_request": f"${session['cost'] / max(session['requests'], 1):.4f}",
        }

    def get_all_sessions_report(self) -> Dict[str, Any]:
        """Get report for all sessions"""
        return {name: self.get_session_report(name) for name in self.sessions}


# Global cost tracker
_cost_tracker = CostTracker()


def get_cost_tracker() -> CostTracker:
    """Get global cost tracker instance"""
    return _cost_tracker

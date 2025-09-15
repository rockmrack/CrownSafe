"""
User-Agent blocking middleware
Blocks requests from known malicious scanners and bots
"""

import os
import re
import logging
from typing import List, Optional, Pattern
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class UserAgentBlocker(BaseHTTPMiddleware):
    """
    Middleware to block requests from suspicious user agents
    """
    
    # Known malicious scanner patterns
    DEFAULT_BLOCKED_PATTERNS = [
        "sqlmap",      # SQL injection scanner
        "nikto",       # Web vulnerability scanner
        "acunetix",    # Vulnerability scanner
        "nmap",        # Network scanner
        "masscan",     # Port scanner
        "metasploit",  # Penetration testing
        "burpsuite",   # Security testing
        "zaproxy",     # OWASP ZAP
        "openvas",     # Vulnerability scanner
        "nessus",      # Vulnerability scanner
        "w3af",        # Web app attack framework
        "havij",       # SQL injection tool
        "hydra",       # Brute force tool
        "dirbuster",   # Directory brute force
        "gobuster",    # Directory/file brute force
        "wpscan",      # WordPress scanner
        "joomscan",    # Joomla scanner
        "nuclei",      # Vulnerability scanner
        "python-requests/",  # Block generic Python (optional)
        "curl/",       # Block curl (optional - may affect legitimate testing)
        "wget/",       # Block wget (optional)
    ]
    
    # User agents to always allow (whitelist)
    ALLOWED_PATTERNS = [
        "babyshield",  # Our own app
        "postman",     # API testing
        "insomnia",    # API testing
        "paw/",        # API testing
    ]
    
    def __init__(
        self, 
        app, 
        blocked_patterns: Optional[List[str]] = None,
        allowed_patterns: Optional[List[str]] = None,
        block_empty_ua: bool = False,
        case_sensitive: bool = False
    ):
        """
        Initialize UA blocker
        
        Args:
            app: ASGI application
            blocked_patterns: List of UA patterns to block
            allowed_patterns: List of UA patterns to always allow
            block_empty_ua: Whether to block empty user agents
            case_sensitive: Whether pattern matching is case sensitive
        """
        super().__init__(app)
        
        # Load patterns from environment or use defaults
        env_blocked = os.getenv("BLOCKED_USER_AGENTS", "")
        if env_blocked:
            env_patterns = [p.strip() for p in env_blocked.split(",") if p.strip()]
            self.blocked_patterns = blocked_patterns or env_patterns
        else:
            self.blocked_patterns = blocked_patterns or self.DEFAULT_BLOCKED_PATTERNS
        
        self.allowed_patterns = allowed_patterns or self.ALLOWED_PATTERNS
        self.block_empty_ua = block_empty_ua or os.getenv("BLOCK_EMPTY_USER_AGENT", "false").lower() == "true"
        self.case_sensitive = case_sensitive
        
        # Compile regex patterns for efficiency
        flags = 0 if case_sensitive else re.IGNORECASE
        self.blocked_regex = [
            re.compile(re.escape(pattern), flags) 
            for pattern in self.blocked_patterns
        ]
        self.allowed_regex = [
            re.compile(re.escape(pattern), flags)
            for pattern in self.allowed_patterns
        ]
        
        logger.info(f"UA blocker configured with {len(self.blocked_patterns)} blocked patterns")
    
    async def dispatch(self, request: Request, call_next):
        """
        Check user agent and block if suspicious
        """
        # Get user agent
        user_agent = request.headers.get("user-agent", "").strip()
        trace_id = getattr(request.state, "trace_id", None)
        
        # Check for empty UA
        if not user_agent:
            if self.block_empty_ua:
                logger.warning(
                    "Request blocked: Empty user agent",
                    extra={
                        "traceId": trace_id,
                        "path": request.url.path,
                        "ip": request.client.host if request.client else None
                    }
                )
                return self._forbidden_response(trace_id, "User-Agent header required")
            else:
                # Allow empty UA but log it
                logger.debug(
                    "Empty user agent allowed",
                    extra={
                        "traceId": trace_id,
                        "path": request.url.path
                    }
                )
                return await call_next(request)
        
        # Check whitelist first
        for allowed_pattern in self.allowed_regex:
            if allowed_pattern.search(user_agent):
                logger.debug(f"User agent explicitly allowed: {user_agent[:50]}")
                return await call_next(request)
        
        # Check blocklist
        for blocked_pattern in self.blocked_regex:
            if blocked_pattern.search(user_agent):
                logger.warning(
                    f"Request blocked: Suspicious user agent",
                    extra={
                        "traceId": trace_id,
                        "path": request.url.path,
                        "user_agent": user_agent[:100],  # Truncate for logs
                        "pattern": blocked_pattern.pattern,
                        "ip": request.client.host if request.client else None
                    }
                )
                return self._forbidden_response(trace_id, "User-Agent not allowed")
        
        # Check for additional suspicious patterns
        if self._is_suspicious_ua(user_agent):
            logger.warning(
                f"Request blocked: Suspicious UA characteristics",
                extra={
                    "traceId": trace_id,
                    "path": request.url.path,
                    "user_agent": user_agent[:100]
                }
            )
            return self._forbidden_response(trace_id, "User-Agent not allowed")
        
        # Allow the request
        return await call_next(request)
    
    def _is_suspicious_ua(self, user_agent: str) -> bool:
        """
        Check for additional suspicious patterns
        
        Args:
            user_agent: User agent string
            
        Returns:
            True if suspicious
        """
        ua_lower = user_agent.lower()
        
        # Check for SQL injection attempts in UA
        sql_patterns = [
            "' or ",
            "\" or ",
            "1=1",
            "union select",
            "drop table",
            "<script",
            "javascript:",
            "../",
            "..\\",
        ]
        
        for pattern in sql_patterns:
            if pattern in ua_lower:
                return True
        
        # Check for excessive length (possible buffer overflow attempt)
        if len(user_agent) > 500:
            return True
        
        # Check for non-ASCII characters (possible encoding attack)
        try:
            user_agent.encode('ascii')
        except UnicodeEncodeError:
            # Contains non-ASCII characters
            # This might be too strict for international UAs
            pass
        
        return False
    
    def _forbidden_response(self, trace_id: Optional[str], message: str) -> JSONResponse:
        """
        Create forbidden response
        
        Args:
            trace_id: Request trace ID
            message: Error message
            
        Returns:
            403 Forbidden response
        """
        return JSONResponse(
            content={
                "ok": False,
                "error": {
                    "code": "FORBIDDEN",
                    "message": message
                },
                "traceId": trace_id
            },
            status_code=403,
            headers={
                "Content-Type": "application/json",
                "Cache-Control": "no-cache, no-store, must-revalidate"
            }
        )


class SmartUserAgentFilter(UserAgentBlocker):
    """
    Advanced UA filter with ML-based detection (future enhancement)
    """
    
    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        # Could integrate with ML model for advanced bot detection
        self.suspicious_score_threshold = 0.7
    
    def calculate_suspicion_score(self, user_agent: str) -> float:
        """
        Calculate suspicion score for a user agent
        
        Args:
            user_agent: User agent string
            
        Returns:
            Score between 0 (safe) and 1 (suspicious)
        """
        score = 0.0
        
        # Length anomaly
        if len(user_agent) < 10:
            score += 0.3
        elif len(user_agent) > 300:
            score += 0.4
        
        # Missing common browser tokens
        common_tokens = ["Mozilla", "Chrome", "Safari", "Firefox", "Edge"]
        if not any(token in user_agent for token in common_tokens):
            score += 0.2
        
        # Contains suspicious tokens
        suspicious_tokens = ["bot", "spider", "crawl", "scan", "hack"]
        for token in suspicious_tokens:
            if token.lower() in user_agent.lower():
                score += 0.2
                break
        
        # Entropy check (randomness)
        # High entropy might indicate generated/obfuscated UA
        # (simplified check)
        unique_chars = len(set(user_agent))
        if unique_chars / max(len(user_agent), 1) > 0.8:
            score += 0.1
        
        return min(score, 1.0)

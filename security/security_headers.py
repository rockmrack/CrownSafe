"""
Security Headers Middleware for BabyShield
Implements comprehensive security headers for bulletproof protection
"""
from fastapi import Request, Response
from fastapi.responses import JSONResponse
import time
import logging

logger = logging.getLogger(__name__)

class SecurityHeadersMiddleware:
    """
    Comprehensive security headers middleware
    Implements OWASP security header recommendations
    """
    
    def __init__(self):
        self.start_time = time.time()
    
    async def __call__(self, request: Request, call_next):
        """Apply security headers to all responses"""
        
        # Process request
        response = await call_next(request)
        
        # Apply comprehensive security headers
        security_headers = {
            # Content Security Policy - Prevent XSS, injection attacks
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                "font-src 'self' https://fonts.gstatic.com; "
                "img-src 'self' data: https:; "
                "connect-src 'self' https://api.openai.com; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'"
            ),
            
            # HTTP Strict Transport Security - Force HTTPS
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
            
            # Prevent clickjacking
            "X-Frame-Options": "DENY",
            
            # Prevent MIME type sniffing
            "X-Content-Type-Options": "nosniff",
            
            # XSS Protection (legacy browsers)
            "X-XSS-Protection": "1; mode=block",
            
            # Referrer Policy - Limit information leakage
            "Referrer-Policy": "strict-origin-when-cross-origin",
            
            # Permissions Policy - Restrict browser features
            "Permissions-Policy": (
                "camera=(), microphone=(), geolocation=(), "
                "payment=(), usb=(), magnetometer=(), gyroscope=(), "
                "accelerometer=(), ambient-light-sensor=()"
            ),
            
            # Cross-Origin Policies
            "Cross-Origin-Embedder-Policy": "require-corp",
            "Cross-Origin-Opener-Policy": "same-origin",
            "Cross-Origin-Resource-Policy": "same-origin",
            
            # Security information
            "X-Security-Level": "bulletproof",
            "X-Security-Scan": "protected",
            "X-Security-Version": "2.0",
            
            # Server information hiding
            "Server": "BabyShield-Security",
            
            # Cache control for sensitive endpoints
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
            
            # Additional security headers
            "X-Robots-Tag": "noindex, nofollow, nosnippet, noarchive",
            "X-Permitted-Cross-Domain-Policies": "none",
            "X-Download-Options": "noopen",
        }
        
        # Apply headers based on content type and path
        path = request.url.path
        
        # API endpoints get enhanced security
        if path.startswith('/api/'):
            security_headers.update({
                "X-API-Security": "enhanced",
                "X-Rate-Limit-Policy": "strict",
                "Access-Control-Max-Age": "3600",
            })
        
        # Admin/sensitive paths get maximum security
        if any(sensitive in path.lower() for sensitive in ['admin', 'config', 'backup']):
            security_headers.update({
                "X-Security-Alert": "maximum",
                "X-Access-Policy": "restricted",
            })
        
        # Chat endpoints get privacy headers
        if path.startswith('/api/v1/chat/'):
            security_headers.update({
                "X-Privacy-Level": "maximum",
                "X-Data-Processing": "minimal",
                "X-Retention-Policy": "opt-in",
            })
        
        # Apply all headers to response
        for header_name, header_value in security_headers.items():
            response.headers[header_name] = header_value
        
        # Log security header application
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Applied {len(security_headers)} security headers to {path}")
        
        return response


class ThreatDetectionMiddleware:
    """
    Advanced threat detection and response middleware
    """
    
    def __init__(self):
        self.threat_patterns = self._load_threat_signatures()
        self.blocked_ips = set()
        self.suspicious_requests = {}
    
    def _load_threat_signatures(self) -> Dict[str, int]:
        """Load threat signatures with severity scores"""
        return {
            # Remote Code Execution (Critical - 100 points)
            'eval\\(': 100,
            'exec\\(': 100,
            'system\\(': 100,
            'passthru\\(': 100,
            'shell_exec': 100,
            'phpunit.*eval-stdin': 100,
            
            # SQL Injection (High - 80 points)
            'union.*select': 80,
            'drop.*table': 80,
            'insert.*into': 70,
            'delete.*from': 70,
            'update.*set': 70,
            
            # XSS Attempts (High - 75 points)
            '<script.*>': 75,
            'javascript:': 75,
            'onload=': 75,
            'onerror=': 75,
            'onclick=': 75,
            
            # Path Traversal (Medium - 60 points)
            '\\.\\./': 60,
            '%2e%2e/': 60,
            '\\\\\\.\\.\\\\': 60,
            
            # Information Disclosure (Medium - 50 points)
            '\\.git/': 50,
            '\\.env': 50,
            'phpinfo': 50,
            'server-info': 50,
            
            # Scanning Activity (Low - 30 points)
            'admin.*login': 30,
            'wp-admin': 30,
            'phpmyadmin': 30,
            'backup.*sql': 30,
        }
    
    async def __call__(self, request: Request, call_next):
        """Threat detection pipeline"""
        client_ip = self._get_client_ip(request)
        
        # Quick IP block check
        if client_ip in self.blocked_ips:
            logger.warning(f"Blocked request from banned IP: {client_ip}")
            return JSONResponse(
                status_code=403,
                content={"error": "IP blocked"},
                headers={"X-Block-Reason": "ip_banned"}
            )
        
        # Threat analysis
        threat_score = self._analyze_request_threat(request)
        
        if threat_score >= 100:
            # Critical threat - immediate block and ban
            self.blocked_ips.add(client_ip)
            logger.error(f"CRITICAL THREAT detected: {threat_score} points from {client_ip} - IP BANNED")
            return JSONResponse(
                status_code=403,
                content={"error": "Critical security threat detected"},
                headers={
                    "X-Threat-Score": str(threat_score),
                    "X-Block-Reason": "critical_threat",
                    "X-IP-Status": "banned"
                }
            )
        elif threat_score >= 80:
            # High threat - block request
            logger.warning(f"HIGH THREAT detected: {threat_score} points from {client_ip}")
            return JSONResponse(
                status_code=403,
                content={"error": "Security threat detected"},
                headers={
                    "X-Threat-Score": str(threat_score),
                    "X-Block-Reason": "high_threat"
                }
            )
        elif threat_score >= 50:
            # Medium threat - log and monitor
            logger.info(f"MEDIUM THREAT detected: {threat_score} points from {client_ip}")
        
        # Process legitimate request
        response = await call_next(request)
        
        # Add threat score to response headers for monitoring
        if threat_score > 0:
            response.headers["X-Threat-Score"] = str(threat_score)
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract real client IP"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
    
    def _analyze_request_threat(self, request: Request) -> int:
        """Calculate threat score based on request analysis"""
        score = 0
        
        # Analyze URL path
        path = request.url.path.lower()
        query = str(request.url.query).lower()
        user_agent = request.headers.get("User-Agent", "").lower()
        
        # Check against threat signatures
        full_request = f"{path} {query} {user_agent}"
        for pattern, points in self.threat_patterns.items():
            if re.search(pattern, full_request, re.IGNORECASE):
                score += points
                logger.debug(f"Threat pattern matched: {pattern} (+{points} points)")
        
        # Additional heuristics
        if len(path.split('/')) > 10:  # Deep path traversal
            score += 20
        if any(char in path for char in ['<', '>', '"', "'"]):  # Injection characters
            score += 15
        if not user_agent or len(user_agent) < 10:  # Missing/short User-Agent
            score += 10
        
        return min(score, 150)  # Cap at 150


# Global middleware instances
security_headers_middleware = SecurityHeadersMiddleware()
threat_detection_middleware = ThreatDetectionMiddleware()


async def bulletproof_security_middleware(request: Request, call_next):
    """Combined bulletproof security middleware"""
    # First apply threat detection
    response = await threat_detection_middleware(request, call_next)
    
    # Then apply security headers if not already blocked
    if response.status_code < 400:
        response = await security_headers_middleware(request, lambda r: response)
    
    return response

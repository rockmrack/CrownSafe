"""
Security package for API protection
"""

from .cors import add_strict_cors, get_allowed_origins, CORSConfig
from .headers import (
    SecurityHeadersMiddleware,
    get_security_headers_dict,
    apply_security_headers,
)
from .integration import setup_security, get_security_config, validate_security_config

__all__ = [
    # CORS
    "add_strict_cors",
    "get_allowed_origins",
    "CORSConfig",
    # Headers
    "SecurityHeadersMiddleware",
    "get_security_headers_dict",
    "apply_security_headers",
    # Integration
    "setup_security",
    "get_security_config",
    "validate_security_config",
]

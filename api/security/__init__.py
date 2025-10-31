"""Security package for API protection."""

from .cors import CORSConfig, add_strict_cors, get_allowed_origins
from .headers import (
    SecurityHeadersMiddleware,
    apply_security_headers,
    get_security_headers_dict,
)
from .integration import get_security_config, setup_security, validate_security_config

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

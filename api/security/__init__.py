"""Security package for API protection."""

from .cors import CORSConfig, add_strict_cors, get_allowed_origins
from .headers import (
    SecurityHeadersMiddleware,
    apply_security_headers,
    get_security_headers_dict,
)
from .integration import get_security_config, setup_security, validate_security_config

__all__ = [
    "CORSConfig",
    # Headers
    "SecurityHeadersMiddleware",
    # CORS
    "add_strict_cors",
    "apply_security_headers",
    "get_allowed_origins",
    "get_security_config",
    "get_security_headers_dict",
    # Integration
    "setup_security",
    "validate_security_config",
]

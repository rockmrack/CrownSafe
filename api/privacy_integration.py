"""
Privacy compliance integration for FastAPI app
Integrates all privacy features from Task 8
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles


def setup_privacy_compliance(app: FastAPI):
    """
    Integrate all privacy compliance features into the FastAPI app
    
    This includes:
    - User privacy endpoints (GDPR/CCPA rights)
    - Admin privacy management
    - Legal pages (privacy, terms, data deletion)
    - PII masking in logs
    
    Args:
        app: FastAPI application instance
    """
    
    # Import privacy routers
    from api.routes import privacy, admin_privacy
    
    # Include user privacy endpoints
    app.include_router(
        privacy.router,
        tags=["privacy"],
        responses={
            401: {"description": "Unauthorized"},
            429: {"description": "Too many requests"}
        }
    )
    
    # Include admin privacy management
    app.include_router(
        admin_privacy.router,
        tags=["admin", "privacy"],
        dependencies=[],  # Admin auth already in router
        responses={
            401: {"description": "Admin authentication required"},
            403: {"description": "Forbidden"}
        }
    )
    
    # Mount legal pages
    try:
        app.mount(
            "/legal",
            StaticFiles(directory="static/legal", html=True),
            name="legal"
        )
        print("✅ Legal pages mounted at /legal/*")
    except RuntimeError as e:
        print(f"⚠️ Could not mount legal pages: {e}")
    
    # Configure logging with PII masking
    configure_privacy_logging()
    
    print("✅ Privacy compliance features integrated")


def configure_privacy_logging():
    """
    Configure logging to mask PII in logs
    """
    import logging
    from api.utils.privacy import mask_pii
    
    # Create custom formatter that masks PII
    class PIIMaskingFormatter(logging.Formatter):
        """Custom formatter that masks PII in log messages"""
        
        def format(self, record):
            # Format the base message
            msg = super().format(record)
            
            # Mask PII in the message
            masked_msg = mask_pii(msg)
            
            return masked_msg
    
    # Apply to all handlers
    root_logger = logging.getLogger()
    formatter = PIIMaskingFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    for handler in root_logger.handlers:
        handler.setFormatter(formatter)
    
    print("✅ PII masking configured for logs")


def get_privacy_config():
    """
    Get privacy configuration from environment
    
    Returns:
        Dictionary with privacy configuration
    """
    import os
    
    return {
        "dpo_email": os.getenv("PRIVACY_DPO_EMAIL", "support@babyshield.app"),
        "retention_years": int(os.getenv("PRIVACY_RETENTION_YEARS", "3")),
        "rate_limit_enabled": os.getenv("RATE_LIMIT_REDIS_URL") is not None,
        "features": {
            "data_export": True,
            "data_deletion": True,
            "data_rectification": True,
            "processing_restriction": True,
            "objection": True,
            "verification_required": True
        },
        "compliance": {
            "gdpr": True,
            "ccpa": True,
            "coppa": True,
            "pipeda": True,
            "lgpd": True,
            "appi": True
        },
        "legal_pages": {
            "privacy_policy": "/legal/privacy",
            "terms_of_service": "/legal/terms",
            "data_deletion": "/legal/data-deletion"
        }
    }


def validate_privacy_setup():
    """
    Validate that privacy features are properly configured
    
    Returns:
        Tuple of (is_valid, errors)
    """
    errors = []
    
    # Check environment variables
    import os
    
    if not os.getenv("PRIVACY_DPO_EMAIL"):
        errors.append("PRIVACY_DPO_EMAIL not configured")
    
    # Check database tables
    try:
        from core_infra.database import engine
        from sqlalchemy import inspect
        
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        if "privacy_requests" not in tables:
            errors.append("privacy_requests table not found - run migrations")
    except Exception as e:
        errors.append(f"Database check failed: {e}")
    
    # Check static files
    import os
    if not os.path.exists("static/legal/privacy.html"):
        errors.append("Legal pages not found in static/legal/")
    
    # Check models
    try:
        from db.models.privacy_request import PrivacyRequest
    except ImportError:
        errors.append("PrivacyRequest model not importable")
    
    is_valid = len(errors) == 0
    
    return is_valid, errors


# Usage in main.py:
# from api.privacy_integration import setup_privacy_compliance
# setup_privacy_compliance(app)


# Export functions
__all__ = [
    "setup_privacy_compliance",
    "configure_privacy_logging",
    "get_privacy_config",
    "validate_privacy_setup"
]

"""
Sentry Error Tracking Integration.

This module initializes Sentry for error tracking and performance monitoring.
It integrates with FastAPI and SQLAlchemy to capture errors and slow queries.
"""
import os
import logging
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

logger = logging.getLogger(__name__)


def init_sentry():
    """
    Initialize Sentry error tracking.
    
    Configuration is done via environment variables:
    - SENTRY_DSN: Sentry project DSN (required)
    - ENVIRONMENT: Environment name (default: "production")
    - GIT_COMMIT: Git commit SHA for release tracking
    - SENTRY_TRACES_SAMPLE_RATE: Percentage of transactions to trace (default: 0.1)
    - SENTRY_PROFILES_SAMPLE_RATE: Percentage of transactions to profile (default: 0.1)
    
    Returns:
        bool: True if Sentry was initialized, False otherwise
    """
    sentry_dsn = os.getenv("SENTRY_DSN")
    
    if not sentry_dsn:
        logger.info("Sentry not configured (SENTRY_DSN not set)")
        return False
    
    try:
        # Get configuration
        environment = os.getenv("ENVIRONMENT", "production")
        release = os.getenv("GIT_COMMIT", "unknown")
        traces_sample_rate = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1"))
        profiles_sample_rate = float(os.getenv("SENTRY_PROFILES_SAMPLE_RATE", "0.1"))
        
        # Initialize Sentry
        sentry_sdk.init(
            dsn=sentry_dsn,
            integrations=[
                # FastAPI integration - captures request/response data
                FastApiIntegration(
                    transaction_style="url",  # Group by URL pattern
                    failed_request_status_codes=[500, 501, 502, 503, 504],
                ),
                # SQLAlchemy integration - captures slow queries
                SqlalchemyIntegration(),
                # Logging integration - captures log messages as breadcrumbs
                LoggingIntegration(
                    level=logging.INFO,  # Capture info and above
                    event_level=logging.ERROR,  # Send errors as events
                ),
            ],
            # Performance monitoring
            traces_sample_rate=traces_sample_rate,
            profiles_sample_rate=profiles_sample_rate,
            
            # Environment and release tracking
            environment=environment,
            release=release,
            
            # Additional configuration
            send_default_pii=False,  # Don't send PII by default
            attach_stacktrace=True,  # Include stacktraces
            max_breadcrumbs=50,  # Keep last 50 breadcrumbs
            
            # Before send hook to scrub sensitive data
            before_send=scrub_sensitive_data,
        )
        
        logger.info(
            f"✅ Sentry error tracking initialized "
            f"(env={environment}, release={release[:8]}, traces={traces_sample_rate})"
        )
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize Sentry: {e}")
        return False


def scrub_sensitive_data(event, hint):
    """
    Scrub sensitive data from Sentry events before sending.
    
    Args:
        event: The Sentry event dict
        hint: Additional context
        
    Returns:
        Modified event dict or None to drop the event
    """
    # Scrub sensitive headers
    if "request" in event and "headers" in event["request"]:
        sensitive_headers = ["authorization", "cookie", "x-api-key"]
        for header in sensitive_headers:
            if header in event["request"]["headers"]:
                event["request"]["headers"][header] = "[REDACTED]"
    
    # Scrub sensitive query parameters
    if "request" in event and "query_string" in event["request"]:
        sensitive_params = ["api_key", "token", "password"]
        query_string = event["request"]["query_string"]
        for param in sensitive_params:
            if param in query_string.lower():
                event["request"]["query_string"] = "[REDACTED]"
                break
    
    return event


def capture_exception(error: Exception, context: dict = None):
    """
    Manually capture an exception and send to Sentry.
    
    Args:
        error: The exception to capture
        context: Additional context to include
    """
    if context:
        with sentry_sdk.push_scope() as scope:
            for key, value in context.items():
                scope.set_context(key, value)
            sentry_sdk.capture_exception(error)
    else:
        sentry_sdk.capture_exception(error)


def capture_message(message: str, level: str = "info", context: dict = None):
    """
    Manually capture a message and send to Sentry.
    
    Args:
        message: The message to capture
        level: Severity level (debug, info, warning, error, fatal)
        context: Additional context to include
    """
    if context:
        with sentry_sdk.push_scope() as scope:
            for key, value in context.items():
                scope.set_context(key, value)
            sentry_sdk.capture_message(message, level=level)
    else:
        sentry_sdk.capture_message(message, level=level)

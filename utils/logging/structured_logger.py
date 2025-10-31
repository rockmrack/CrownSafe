"""
Structured Logging Module for BabyShield Backend
Issue #32 - Phase 2 Implementation
"""

import sys
from pathlib import Path
from typing import Any, Dict

from fastapi import Request
from loguru import logger


# Configure structured logging
def setup_logging(config):
    """Setup structured logging with JSON format"""
    # config should be passed in by the caller

    # Remove default loguru handler
    logger.remove()

    # Add structured JSON handler
    logger.add(
        sys.stdout,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {name}:{function}:{line} | {message}",
        level=config.LOG_LEVEL,
        serialize=True if config.LOG_FORMAT == "json" else False,
        enqueue=True,
        diagnose=True,
    )

    # Add file handler with rotation
    log_path = Path(config.LOG_FILE)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger.add(
        str(log_path),
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {name}:{function}:{line} | {message}",
        level=config.LOG_LEVEL,
        rotation=config.LOG_ROTATION,
        retention=config.LOG_RETENTION,
        serialize=True if config.LOG_FORMAT == "json" else False,
        enqueue=True,
    )

    return logger


# Request logging middleware
def log_request(request: Request, response_time: float = None, status_code: int = None):
    """Log HTTP request with context"""
    logger.info(
        "HTTP Request",
        extra={
            "method": request.method,
            "url": str(request.url),
            "client_ip": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent", "unknown"),
            "response_time_ms": response_time,
            "status_code": status_code,
            "request_size": request.headers.get("content-length", 0),
        },
    )


# Performance logging
def log_performance(operation: str, duration_ms: float, **kwargs):
    """Log performance metrics"""
    logger.info(
        f"Performance: {operation}",
        extra={"operation": operation, "duration_ms": duration_ms, **kwargs},
    )


# Error logging with context
def log_error(error: Exception, context: Dict[str, Any] = None):
    """Log error with full context"""
    logger.error(
        f"Error: {type(error).__name__}",
        extra={
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context or {},
        },
    )

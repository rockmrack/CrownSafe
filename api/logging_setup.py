"""
Structured JSON logging configuration for production
Provides consistent JSON log format for all application logs
"""

import json
import logging
import sys
import time
from typing import Any, Dict


class JsonFormatter(logging.Formatter):
    """
    Custom formatter to output logs as JSON
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON
        """
        # Base payload
        payload: Dict[str, Any] = {
            "timestamp": int(time.time() * 1000),  # Unix timestamp in milliseconds
            "time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add standard extras if present (from middleware/handlers)
        standard_extras = [
            "traceId",
            "correlationId",
            "method",
            "path",
            "query",
            "status",
            "duration_ms",
            "ip",
            "ua",
            "referer",
            "user_id",
            "error_code",
            "error_type",
        ]

        for key in standard_extras:
            if hasattr(record, key):
                value = getattr(record, key)
                if value is not None:
                    payload[key] = value

        # Add exception info if present
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
            payload["exc_type"] = record.exc_info[0].__name__ if record.exc_info[0] else None

        # Add source location for debugging (only for errors)
        if record.levelno >= logging.ERROR:
            payload["source"] = {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName,
            }

        # Convert to JSON
        return json.dumps(payload, default=str)


def setup_json_logging(log_level: str = "INFO"):
    """
    Configure all loggers to use JSON formatting

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    # Create handler with JSON formatter
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(getattr(logging, log_level, logging.INFO))

    # Disable redundant uvicorn access logs (we have our own)
    logging.getLogger("uvicorn.access").handlers = []
    logging.getLogger("uvicorn.access").propagate = False

    # Configure uvicorn error logger to use JSON
    uvicorn_error = logging.getLogger("uvicorn.error")
    uvicorn_error.handlers = [handler]

    # Configure specific loggers
    loggers_config = {
        "app": logging.INFO,
        "access": logging.INFO,
        "api": logging.INFO,
        "database": logging.WARNING,
        "sqlalchemy.engine": logging.WARNING,
        "sqlalchemy.pool": logging.WARNING,
        "httpx": logging.WARNING,
        "httpcore": logging.WARNING,
        "redis": logging.WARNING,
    }

    for logger_name, level in loggers_config.items():
        logger = logging.getLogger(logger_name)
        logger.handlers = [handler]
        logger.setLevel(level)
        logger.propagate = False

    # Log startup message
    logging.getLogger("app").info("JSON logging configured", extra={"log_level": log_level})

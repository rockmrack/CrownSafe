"""Structured logging configuration for BabyShield
Provides consistent logging across the application.
"""

import json
import logging
import logging.config
import os
from datetime import datetime, UTC


class StructuredFormatter(logging.Formatter):
    """Custom formatter that outputs structured JSON logs."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add extra fields if present
        if hasattr(record, "user_id"):
            log_obj["user_id"] = record.user_id
        if hasattr(record, "request_id"):
            log_obj["request_id"] = record.request_id
        if hasattr(record, "path"):
            log_obj["path"] = record.path
        if hasattr(record, "method"):
            log_obj["method"] = record.method
        if hasattr(record, "status_code"):
            log_obj["status_code"] = record.status_code
        if hasattr(record, "duration_ms"):
            log_obj["duration_ms"] = record.duration_ms

        # Add exception info if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_obj)


class ConsoleFormatter(logging.Formatter):
    """Colored console formatter for development."""

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        # Add color for console output
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.RESET}"

        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")

        # Build message
        message = f"{timestamp} | {record.levelname:8s} | {record.name:20s} | {record.getMessage()}"

        # Add extra context if available
        extras = []
        if hasattr(record, "user_id"):
            extras.append(f"user={record.user_id}")
        if hasattr(record, "path"):
            extras.append(f"path={record.path}")
        if hasattr(record, "duration_ms"):
            extras.append(f"duration={record.duration_ms}ms")

        if extras:
            message += f" | {' '.join(extras)}"

        # Add exception if present
        if record.exc_info:
            message += f"\n{self.formatException(record.exc_info)}"

        return message


def setup_logging(
    log_level: str = None,
    log_format: str = "console",
    log_file: str = None,  # "console" or "json"
) -> None:
    """Setup logging configuration for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Format for logs ("console" for development, "json" for production)
        log_file: Optional file path for log output

    """
    # Get log level from environment or parameter
    if log_level is None:
        log_level = os.getenv("LOG_LEVEL", "INFO")

    # Base configuration
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {"()": StructuredFormatter},
            "console": {"()": ConsoleFormatter},
            "simple": {"format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"},
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "console" if log_format == "console" else "json",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            # Application loggers
            "api": {"level": log_level, "handlers": ["console"], "propagate": False},
            "core_infra": {
                "level": log_level,
                "handlers": ["console"],
                "propagate": False,
            },
            "agents": {"level": log_level, "handlers": ["console"], "propagate": False},
            # Third-party loggers (less verbose)
            "uvicorn": {"level": "INFO", "handlers": ["console"], "propagate": False},
            "sqlalchemy": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False,
            },
            "redis": {"level": "WARNING", "handlers": ["console"], "propagate": False},
        },
        "root": {"level": log_level, "handlers": ["console"]},
    }

    # Add file handler if specified
    if log_file:
        config["handlers"]["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": log_level,
            "formatter": "json",
            "filename": log_file,
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
        }
        # Add file handler to all loggers
        for logger_config in config["loggers"].values():
            if "file" not in logger_config["handlers"]:
                logger_config["handlers"].append("file")
        config["root"]["handlers"].append("file")

    # Apply configuration
    logging.config.dictConfig(config)

    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info(
        "Logging configured",
        extra={"log_level": log_level, "log_format": log_format, "log_file": log_file},
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance

    """
    return logging.getLogger(name)


# Request logging middleware
class RequestLogger:
    """Middleware to log all requests and responses."""

    def __init__(self, app) -> None:
        self.app = app
        self.logger = logging.getLogger("api.requests")

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Generate request ID
        import uuid

        request_id = str(uuid.uuid4())[:8]

        # Log request
        start_time = datetime.now(UTC)
        path = scope["path"]
        method = scope["method"]

        self.logger.info(
            f"Request started: {method} {path}",
            extra={"request_id": request_id, "path": path, "method": method},
        )

        # Process request
        async def send_wrapper(message) -> None:
            if message["type"] == "http.response.start":
                # Log response
                duration_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)
                status_code = message["status"]

                log_level = logging.INFO
                if status_code >= 500:
                    log_level = logging.ERROR
                elif status_code >= 400:
                    log_level = logging.WARNING

                self.logger.log(
                    log_level,
                    f"Request completed: {method} {path} -> {status_code}",
                    extra={
                        "request_id": request_id,
                        "path": path,
                        "method": method,
                        "status_code": status_code,
                        "duration_ms": duration_ms,
                    },
                )

            await send(message)

        await self.app(scope, receive, send_wrapper)


# Initialize logging when module is imported
setup_logging()

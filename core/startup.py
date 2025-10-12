#!/usr/bin/env python3
"""
Production startup script for BabyShield API
Handles environment setup and graceful degradation
"""

import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def log_feature_status():
    """Log the status of all major features"""
    logger.info("🔍 BabyShield Feature Status:")

    # OCR Features
    tesseract_enabled = os.getenv("ENABLE_TESSERACT", "false").lower() == "true"
    easyocr_enabled = os.getenv("ENABLE_EASYOCR", "false").lower() == "true"
    logger.info(f"  📝 Tesseract OCR: {'✅ Enabled' if tesseract_enabled else '❌ Disabled'}")
    logger.info(f"  📝 EasyOCR: {'✅ Enabled' if easyocr_enabled else '❌ Disabled'}")

    # Barcode Features
    datamatrix_enabled = os.getenv("ENABLE_DATAMATRIX", "false").lower() == "true"
    logger.info(
        f"  📊 DataMatrix Barcodes: {'✅ Enabled' if datamatrix_enabled else '❌ Disabled (requires pylibdmtx + system libs)'}"
    )

    # Receipt Validation
    receipt_validation_enabled = os.getenv("ENABLE_RECEIPT_VALIDATION", "false").lower() == "true"
    logger.info(f"  🧾 Receipt Validation: {'✅ Enabled' if receipt_validation_enabled else '❌ Disabled'}")

    # API Keys
    openai_available = bool(os.getenv("OPENAI_API_KEY"))
    logger.info(f"  🤖 OpenAI Vision: {'✅ Available' if openai_available else '⚠️  Not configured'}")

    # Database
    db_url = os.getenv("DATABASE_URL", "")
    db_type = "PostgreSQL" if "postgresql" in db_url else "SQLite" if "sqlite" in db_url else "Unknown"
    logger.info(f"  🗄️  Database: {db_type}")

    logger.info("🚀 BabyShield startup configuration complete!")


def check_environment():
    """Check and set required environment variables"""

    # Set defaults for critical environment variables
    defaults = {
        "API_HOST": "0.0.0.0",
        "API_PORT": "8001",
        "TEST_MODE": "false",
        "ENABLE_CACHE": "true",
        "ENABLE_BACKGROUND_TASKS": "false",
        "LOG_LEVEL": "INFO",
    }

    for key, value in defaults.items():
        if key not in os.environ:
            os.environ[key] = value
            logger.info(f"Set {key}={value} (default)")

    # Check for database URL
    if "DATABASE_URL" not in os.environ:
        # Use SQLite for development/testing only
        if os.environ.get("TEST_MODE", "false").lower() == "true":
            os.environ["DATABASE_URL"] = "sqlite:///./babyshield_test.db"
            logger.warning("Using SQLite database for TEST_MODE")
        else:
            logger.error("DATABASE_URL not set - required for production")
            # For production, DATABASE_URL must be explicitly set to PostgreSQL
            # Do not provide a default that would silently use PostgreSQL without credentials
            logger.info("Please set DATABASE_URL=postgresql+psycopg://user:pass@host:5432/dbname")
            # For local development fallback only (will fail if PostgreSQL not available)
            os.environ["DATABASE_URL"] = "postgresql+psycopg://postgres:postgres@localhost/babyshield"
            logger.warning("Using default PostgreSQL connection (DEV ONLY - will fail if not available)")

    # Check for optional service keys
    if "OPENAI_API_KEY" not in os.environ:
        logger.warning("OPENAI_API_KEY not set - visual identification will be unavailable")
        # Don't set a mock key - let the service handle missing keys gracefully

    # Log enabled features status
    log_feature_status()

    if "JWT_SECRET_KEY" not in os.environ:
        os.environ["JWT_SECRET_KEY"] = "development-secret-key-change-in-production"
        logger.warning("JWT_SECRET_KEY not set - using default (UNSAFE for production)")

    if "SECRET_KEY" not in os.environ:
        os.environ["SECRET_KEY"] = "development-secret-key-change-in-production"
        logger.warning("SECRET_KEY not set - using default (UNSAFE for production)")


def create_database_tables():
    """Create database tables if they don't exist"""
    try:
        from core_infra.database import create_tables, engine

        logger.info("Creating database tables...")
        create_tables()
        logger.info("Database tables ready")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        # Continue anyway - tables might already exist


def start_api():
    """Start the FastAPI application"""
    import uvicorn

    host = os.environ.get("API_HOST", "0.0.0.0")
    port = int(os.environ.get("API_PORT", "8001"))

    logger.info(f"Starting BabyShield API on {host}:{port}")

    # Import the app
    try:
        from api.main_babyshield import app

        logger.info("Successfully loaded main_babyshield app")
    except ImportError as e:
        logger.error(f"Failed to import main_babyshield: {e}")
        logger.info("Falling back to simplified API")
        try:
            from api.main_babyshield_simplified import app
        except ImportError:
            logger.error("No API module available!")
            sys.exit(1)

    # Run the server
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=os.environ.get("LOG_LEVEL", "info").lower(),
        access_log=True,
        use_colors=False,  # Disable colors for production logs
    )


if __name__ == "__main__":
    logger.info("=== BabyShield API Starting ===")

    # Setup environment
    check_environment()

    # Create database tables
    create_database_tables()

    # Start the API
    start_api()

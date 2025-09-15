#!/usr/bin/env python3
"""
Production startup script for BabyShield API
Handles environment setup and graceful degradation
"""

import os
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_environment():
    """Check and set required environment variables"""
    
    # Set defaults for critical environment variables
    defaults = {
        'API_HOST': '0.0.0.0',
        'API_PORT': '8001',
        'TEST_MODE': 'false',
        'ENABLE_CACHE': 'true',
        'ENABLE_BACKGROUND_TASKS': 'false',
        'LOG_LEVEL': 'INFO'
    }
    
    for key, value in defaults.items():
        if key not in os.environ:
            os.environ[key] = value
            logger.info(f"Set {key}={value} (default)")
    
    # Check for database URL
    if 'DATABASE_URL' not in os.environ:
        # Use SQLite for development/testing
        if os.environ.get('TEST_MODE', 'false').lower() == 'true':
            os.environ['DATABASE_URL'] = 'sqlite:///./babyshield_test.db'
            logger.warning("Using SQLite database for TEST_MODE")
        else:
            logger.warning("DATABASE_URL not set - using PostgreSQL default")
            os.environ['DATABASE_URL'] = 'postgresql://postgres:postgres@localhost/babyshield'
    
    # Set mock keys for optional services if not provided
    if 'OPENAI_API_KEY' not in os.environ:
        os.environ['OPENAI_API_KEY'] = 'sk-mock-key-for-testing'
        logger.warning("OPENAI_API_KEY not set - using mock key")
    
    if 'JWT_SECRET_KEY' not in os.environ:
        os.environ['JWT_SECRET_KEY'] = 'development-secret-key-change-in-production'
        logger.warning("JWT_SECRET_KEY not set - using default (UNSAFE for production)")
    
    if 'SECRET_KEY' not in os.environ:
        os.environ['SECRET_KEY'] = 'development-secret-key-change-in-production'
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
    
    host = os.environ.get('API_HOST', '0.0.0.0')
    port = int(os.environ.get('API_PORT', '8001'))
    
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
        log_level=os.environ.get('LOG_LEVEL', 'info').lower(),
        access_log=True,
        use_colors=False  # Disable colors for production logs
    )

if __name__ == "__main__":
    logger.info("=== BabyShield API Starting ===")
    
    # Setup environment
    check_environment()
    
    # Create database tables
    create_database_tables()
    
    # Start the API
    start_api()

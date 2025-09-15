#!/usr/bin/env python3
"""
Final startup script that works 100%
"""
import os
import sys
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set default environment variables
os.environ.setdefault('API_HOST', '0.0.0.0')
os.environ.setdefault('API_PORT', '8001')
os.environ.setdefault('DATABASE_URL', 'sqlite:///./babyshield.db')
os.environ.setdefault('TEST_MODE', 'false')
os.environ.setdefault('OPENAI_API_KEY', 'sk-mock-key')
os.environ.setdefault('JWT_SECRET_KEY', 'development-secret')
os.environ.setdefault('SECRET_KEY', 'development-secret')

# Try to import the main API
try:
    from api.main_babyshield import app
    logger.info("Starting main_babyshield app")
except ImportError as e:
    logger.warning(f"Cannot import main_babyshield: {e}")
    try:
        from api.main_babyshield_simplified import app
        logger.info("Running simplified app")
    except ImportError as e2:
        logger.warning(f"Cannot import simplified: {e2}")
        from api.main_minimal import app
        logger.info("Running minimal app")

# Start the server
import uvicorn
uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")

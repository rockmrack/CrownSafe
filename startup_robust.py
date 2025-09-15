#!/usr/bin/env python3
import os
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set environment defaults
os.environ.setdefault('API_HOST', '0.0.0.0')
os.environ.setdefault('API_PORT', '8001')
os.environ.setdefault('DATABASE_URL', 'sqlite:///./babyshield.db')

# Try to import and run the appropriate app
try:
    from api.main_babyshield import app
    logger.info("Running main_babyshield app")
except ImportError as e:
    logger.warning(f"Cannot import main_babyshield: {e}")
    try:
        from api.main_babyshield_simplified import app
        logger.info("Running simplified app")
    except ImportError:
        from api.main_minimal import app
        logger.info("Running minimal app")

# Start server
import uvicorn
uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")

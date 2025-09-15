#!/usr/bin/env python3
"""
Production startup script for BabyShield API
Handles environment setup and database initialization
"""

import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set default environment variables
os.environ.setdefault('OPENAI_API_KEY', os.environ.get('OPENAI_API_KEY', 'sk-mock-key'))
os.environ.setdefault('JWT_SECRET_KEY', os.environ.get('JWT_SECRET_KEY', 'dev-jwt-key'))
os.environ.setdefault('SECRET_KEY', os.environ.get('SECRET_KEY', 'dev-secret-key'))
os.environ.setdefault('ENCRYPTION_KEY', os.environ.get('ENCRYPTION_KEY', 'dev-encryption-key'))
os.environ.setdefault('DISABLE_REDIS_WARNING', 'true')

# Try to import and run the main API
try:
    from api.main_babyshield import app
    logger.info("Starting BabyShield API (Production)")
    
    # Create recalls table if it doesn't exist
    try:
        from core_infra.database import engine
        from sqlalchemy import text
        
        with engine.connect() as conn:
            # Create recalls table if missing (PostgreSQL compatible)
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS recalls (
                    id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
                    product_name TEXT,
                    brand TEXT,
                    recall_date DATE,
                    description TEXT,
                    hazard TEXT,
                    remedy TEXT,
                    agency TEXT,
                    country TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
            logger.info("✅ Recalls table verified/created")
    except Exception as e:
        logger.warning(f"Could not create recalls table: {e}")
    
    # Run with uvicorn
    import uvicorn
    
    # Get configuration from environment
    api_host = os.environ.get('API_HOST', '0.0.0.0')
    api_port = int(os.environ.get('API_PORT', 8001))
    workers = int(os.environ.get('WORKERS', 1))
    
    # Run the app
    uvicorn.run(app, host=api_host, port=api_port, workers=workers)
    
except ImportError as e:
    logger.error(f"Failed to import main API: {e}")
    logger.info("Running simplified app")
    
    # Fallback to simplified app
    from fastapi import FastAPI
    import uvicorn
    
    app = FastAPI(title="BabyShield API (Simplified)")
    
    @app.get("/health")
    def health():
        return {"status": "ok", "mode": "simplified"}
    
    api_host = os.environ.get('API_HOST', '0.0.0.0')
    api_port = int(os.environ.get('API_PORT', 8001))
    
    uvicorn.run(app, host=api_host, port=api_port)
"""
Configuration file for BabyShield Backend
This file provides basic configuration settings.
"""

# Basic configuration
DEBUG = False
TESTING = False

# Database configuration
DATABASE_URL = "sqlite:///babyshield.db"

# Application settings
APP_NAME = "BabyShield Backend"
APP_VERSION = "1.0.0"

# Security settings
SECRET_KEY = "your-secret-key-here"

# Logging configuration
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

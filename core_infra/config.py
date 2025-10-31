"""
Centralized configuration management for BabyShield
Handles environment variables and default values
"""

import os
from pathlib import Path
from typing import Optional


class Config:
    """Application configuration"""

    # Base directory
    BASE_DIR = Path(__file__).resolve().parent.parent

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/babyshield")
    DATABASE_POOL_SIZE: int = int(os.getenv("DATABASE_POOL_SIZE", "20"))
    DATABASE_MAX_OVERFLOW: int = int(os.getenv("DATABASE_MAX_OVERFLOW", "40"))

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    REDIS_CACHE_TTL: int = int(os.getenv("REDIS_CACHE_TTL", "3600"))

    # API Configuration
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8001"))
    API_WORKERS: int = int(os.getenv("API_WORKERS", "4"))
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-this-in-production")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret-change-this")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

    # AWS Configuration (Optional)
    AWS_ACCESS_KEY_ID: Optional[str] = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    S3_BUCKET_NAME: Optional[str] = os.getenv("S3_BUCKET_NAME")

    # External APIs (Optional)
    GOOGLE_VISION_API_KEY: Optional[str] = os.getenv("GOOGLE_VISION_API_KEY")
    CPSC_API_KEY: Optional[str] = os.getenv("CPSC_API_KEY")
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")

    # Celery
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")

    # Feature Flags
    ENABLE_RATE_LIMITING: bool = os.getenv("ENABLE_RATE_LIMITING", "False").lower() == "true"
    ENABLE_AUTHENTICATION: bool = os.getenv("ENABLE_AUTHENTICATION", "False").lower() == "true"
    ENABLE_CACHE: bool = os.getenv("ENABLE_CACHE", "True").lower() == "true"
    ENABLE_ASYNC_PROCESSING: bool = os.getenv("ENABLE_ASYNC_PROCESSING", "True").lower() == "true"

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    @classmethod
    def is_production(cls) -> bool:
        """Check if running in production"""
        return not cls.DEBUG

    @classmethod
    def validate(cls) -> bool:
        """Validate critical configuration"""
        errors = []

        if cls.is_production():
            if cls.SECRET_KEY == "dev-secret-key-change-this-in-production":
                errors.append("SECRET_KEY must be changed in production")
            if cls.JWT_SECRET_KEY == "dev-jwt-secret-change-this":
                errors.append("JWT_SECRET_KEY must be changed in production")

        if errors:
            for error in errors:
                print(f"❌ Config Error: {error}")
            return False

        return True


# Create global config instance
config = Config()

# Validate on import (only warn, don't fail)
if not config.validate():
    print("⚠️ Configuration warnings detected. Review before production deployment.")

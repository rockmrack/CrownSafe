"""
Production Configuration
Settings optimized for production deployment with security and performance
"""

from .base import BaseConfig

class ProductionConfig(BaseConfig):
    """Production environment configuration"""
    
    # Production-specific overrides
    DEBUG: bool = False
    RELOAD: bool = False
    
    # Database - use PostgreSQL or production SQLite
    DATABASE_URL: str = "postgresql://user:password@localhost/babyshield_prod"
    DATABASE_ECHO: bool = False  # No SQL logging in production
    
    # Security - strict settings
    SECRET_KEY: str = "CHANGE-THIS-IN-PRODUCTION-USE-STRONG-SECRET"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # Shorter tokens for security
    
    # CORS - restrict to specific domains
    CORS_ORIGINS: list = [
        "https://yourdomain.com",
        "https://www.yourdomain.com",
        "https://api.yourdomain.com",
    ]
    
    # Logging - production level
    LOG_LEVEL: str = "INFO"
    
    # File uploads - production directory
    UPLOAD_DIR: str = "/app/uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB limit
    
    # AI/ML - production cache
    MODEL_CACHE_DIR: str = "/app/models"
    
    # Enable rate limiting in production
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD: int = 60
    
    # Monitoring - enabled in production
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9090
    
    # Worker settings - production Redis
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/0"
    
    # Additional production settings
    TRUSTED_HOSTS: list = ["yourdomain.com", "www.yourdomain.com"]
    SECURE_SSL_REDIRECT: bool = True
    SECURE_HSTS_SECONDS: int = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS: bool = True
    SECURE_FRAME_DENY: bool = True
    SECURE_CONTENT_TYPE_NOSNIFF: bool = True
    
    class Config:
        env_file = ".env.production"
        env_file_encoding = "utf-8"
        case_sensitive = True

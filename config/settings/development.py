"""
Development Configuration
Settings optimized for local development
"""

from .base import BaseConfig

class DevelopmentConfig(BaseConfig):
    """Development environment configuration"""
    
    # Development-specific overrides
    DEBUG: bool = True
    RELOAD: bool = True
    
    # Database - use local SQLite
    DATABASE_URL: str = "sqlite:///./babyshield_dev.db"
    DATABASE_ECHO: bool = True  # Show SQL queries in development
    
    # Security - relaxed for development
    SECRET_KEY: str = "dev-secret-key-not-for-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # Longer tokens in dev
    
    # CORS - allow all origins in development
    CORS_ORIGINS: list = [
        "http://localhost:3000",  # React dev server
        "http://localhost:8080",  # Vue dev server
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080",
        "http://localhost:5173",  # Vite dev server
    ]
    
    # Logging - more verbose in development
    LOG_LEVEL: str = "DEBUG"
    
    # File uploads - local directory
    UPLOAD_DIR: str = "uploads_dev"
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB for testing
    
    # AI/ML - use environment variables or defaults
    MODEL_CACHE_DIR: str = "models_dev"
    
    # Disable rate limiting in development
    RATE_LIMIT_ENABLED: bool = False
    
    # Monitoring - disabled in development
    ENABLE_METRICS: bool = False
    
    # Worker settings - use local Redis or in-memory
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    class Config:
        env_file = ".env.development"
        env_file_encoding = "utf-8"
        case_sensitive = True

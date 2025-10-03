"""
Base Configuration Class
Contains all common configuration settings for BabyShield
"""

import os
from pathlib import Path
from typing import Optional, List
from pydantic import Field
from pydantic_settings import BaseSettings
from decouple import config as env_config

class BaseConfig(BaseSettings):
    """Base configuration settings for BabyShield backend"""
    
    # Environment identification
    ENVIRONMENT: str = Field(default="development", description="Application environment")
    """Base configuration class with common settings"""
    
    # Application Settings
    APP_NAME: str = "BabyShield Backend"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False, env="DEBUG")
    
    # Server Settings
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8001, env="PORT")
    RELOAD: bool = Field(default=False, env="RELOAD")
    
    # Database Settings
    DATABASE_URL: str = Field(default="sqlite:///./babyshield.db", env="DATABASE_URL")
    DATABASE_ECHO: bool = Field(default=False, env="DATABASE_ECHO")
    
    # Security Settings
    SECRET_KEY: str = Field(env="SECRET_KEY", default="your-secret-key-change-in-production")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    ALGORITHM: str = "HS256"
    
    # API Settings
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: List[str] = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]
    
    # File Upload Settings
    UPLOAD_DIR: str = Field(default="uploads", env="UPLOAD_DIR")
    MAX_FILE_SIZE: int = Field(default=10 * 1024 * 1024, env="MAX_FILE_SIZE")  # 10MB
    ALLOWED_EXTENSIONS: List[str] = [".jpg", ".jpeg", ".png", ".pdf"]
    
    # Logging Settings
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # AI/ML Settings
    OPENAI_API_KEY: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    MODEL_CACHE_DIR: str = Field(default="models", env="MODEL_CACHE_DIR")
    
    # Redis/Cache Settings (if used)
    REDIS_URL: Optional[str] = Field(default=None, env="REDIS_URL")
    CACHE_TTL: int = Field(default=300, env="CACHE_TTL")  # 5 minutes
    
    # Monitoring Settings
    ENABLE_METRICS: bool = Field(default=False, env="ENABLE_METRICS")
    METRICS_PORT: int = Field(default=9090, env="METRICS_PORT")
    
    # Worker Settings
    CELERY_BROKER_URL: Optional[str] = Field(default=None, env="CELERY_BROKER_URL")
    CELERY_RESULT_BACKEND: Optional[str] = Field(default=None, env="CELERY_RESULT_BACKEND")
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    RATE_LIMIT_REQUESTS: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    RATE_LIMIT_PERIOD: int = Field(default=60, env="RATE_LIMIT_PERIOD")  # seconds
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        
    @property
    def database_path(self) -> Path:
        """Get database file path for SQLite"""
        if self.DATABASE_URL.startswith("sqlite:///"):
            return Path(self.DATABASE_URL.replace("sqlite:///", ""))
        return Path("babyshield.db")
    
    @property
    def upload_path(self) -> Path:
        """Get upload directory path"""
        return Path(self.UPLOAD_DIR)
    
    def ensure_directories(self):
        """Create necessary directories"""
        self.upload_path.mkdir(exist_ok=True)
        Path(self.MODEL_CACHE_DIR).mkdir(exist_ok=True)
        
        # Create database directory if SQLite
        if self.DATABASE_URL.startswith("sqlite:///"):
            self.database_path.parent.mkdir(parents=True, exist_ok=True)


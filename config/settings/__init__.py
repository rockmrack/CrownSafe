"""
BabyShield Configuration Management System
Provides environment-aware configuration loading
"""

import os
from typing import Optional
from .base import BaseConfig
from .development import DevelopmentConfig
from .production import ProductionConfig

# Configuration mapping
config_map = {
    'development': DevelopmentConfig,
    'dev': DevelopmentConfig,
    'staging': ProductionConfig,  # Use production config for staging
    'production': ProductionConfig,
    'prod': ProductionConfig,
}

def get_config(environment: Optional[str] = None) -> BaseConfig:
    """
    Get configuration based on environment
    
    Args:
        environment: Environment name (development, staging, production)
                    If None, uses ENVIRONMENT env var, defaults to 'development'
    
    Returns:
        Configuration instance
    """
    if environment is None:
        environment = os.getenv('ENVIRONMENT', 'development').lower()
    
    config_class = config_map.get(environment, DevelopmentConfig)
    return config_class()

# Global config instance
config = get_config()

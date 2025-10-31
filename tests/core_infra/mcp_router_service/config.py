# RossNetAgents/core_infra/mcp_router_service/config.py

import logging
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Configuration settings for the MCP Router Service.
    Reads settings from environment variables or a .env file.
    """

    SERVICE_NAME: str = "MCP_Router_Service"
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="Logging level for the service"
    )

    # --- Network Settings ---
    HOST: str = Field(default="0.0.0.0", description="Host address to bind the service")
    PORT: int = Field(
        default=8001, description="Port to bind the service"
    )  # Using a different port than the agent server (8003)

    # --- Router Settings ---
    # In a real implementation, you might have settings for:
    # - Max queue sizes
    # - Timeout durations
    # - Connection details for underlying message queues (if used)
    # - Discovery service update interval

    # --- Security Settings (Placeholders for now) ---
    JWT_SECRET_KEY: str = Field(
        default="YOUR_SUPER_SECRET_KEY_CHANGE_ME",
        description="Secret key for JWT encoding/decoding. CHANGE IN PRODUCTION!",
    )
    JWT_ALGORITHM: str = Field(default="HS256", description="Algorithm used for JWT")
    # In production, consider using asymmetric keys (RS256/ES256) and managing keys securely.

    class Config:
        # If you use a .env file, Pydantic will load it automatically
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore extra fields from environment variables


# Instantiate settings
settings = Settings()

# Configure logging based on settings
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(settings.SERVICE_NAME)

logger.info(f"Configuration loaded for {settings.SERVICE_NAME}")
logger.info(f"Log level set to: {settings.LOG_LEVEL}")
logger.info(f"Service will run on {settings.HOST}:{settings.PORT}")

# Example of accessing a setting:
# from .config import settings
# print(settings.HOST)

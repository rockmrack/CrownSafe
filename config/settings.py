"""Configuration settings for Crown Safe Backend
Handles environment-specific configuration with validation.
"""

import logging

try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings
from pydantic import Field, root_validator, validator


class Settings(BaseSettings):
    """Application settings with validation."""

    # Environment
    environment: str = Field(default="development", env="ENVIRONMENT")
    is_production: bool = Field(default=False, env="IS_PRODUCTION")

    # Database
    database_url: str | None = Field(default=None, env="DATABASE_URL")
    db_username: str | None = Field(default=None, env="DB_USERNAME")
    db_password: str | None = Field(default=None, env="DB_PASSWORD")
    db_host: str | None = Field(default=None, env="DB_HOST")
    db_port: int | None = Field(default=None, env="DB_PORT")
    db_name: str | None = Field(default=None, env="DB_NAME")

    # API
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8001, env="API_PORT")

    # Security
    secret_key: str = Field(default="dev-secret-key", env="SECRET_KEY")
    openai_api_key: str | None = Field(default=None, env="OPENAI_API_KEY")

    # Features
    enable_agents: bool = Field(default=True, env="ENABLE_AGENTS")

    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s", env="LOG_FORMAT")

    @root_validator(pre=False, skip_on_failure=True)
    def construct_database_url(cls, values):
        """Construct database URL from individual components and validate."""
        environment = values.get("environment", "development")
        is_production = values.get("is_production", False)
        database_url = values.get("database_url")

        # Debug logging
        logging.info(
            f"[DEBUG] BEFORE: environment={environment}, is_production={is_production}, database_url={database_url}",
        )
        logging.info(
            f"[DEBUG] DB_*: username={values.get('db_username')}, host={values.get('db_host')}, port={values.get('db_port')}, name={values.get('db_name')}",  # noqa: E501
        )

        # If we have individual DB components, ALWAYS use them (even if database_url is set to SQLite)
        if all(
            [
                values.get("db_username"),
                values.get("db_password"),
                values.get("db_host"),
                values.get("db_port"),
                values.get("db_name"),
            ],
        ):
            username = values["db_username"]
            password = values["db_password"]
            host = values["db_host"]
            port = values["db_port"]
            dbname = values["db_name"]
            database_url = f"postgresql://{username}:{password}@{host}:{port}/{dbname}"
            values["database_url"] = database_url
            logging.info("[OK] Constructed DATABASE_URL from individual DB components")

        # Production safety check - must have PostgreSQL
        if environment.lower() in ["production", "prod"] or is_production:
            if not database_url or "sqlite" in database_url.lower():
                error_msg = (
                    "CRITICAL ERROR: Production environment requires PostgreSQL database URL. "
                    "Please configure PostgreSQL database URL or provide DB_* environment variables. "
                    f"Current DATABASE_URL: {database_url}"
                )
                logging.error(error_msg)
                raise ValueError(error_msg)

        # Default to SQLite for development if no URL provided
        # Production must explicitly set DATABASE_URL to PostgreSQL
        if not database_url:
            database_url = "sqlite:///./crownsafe_dev.db"
            values["database_url"] = database_url
            logging.warning(
                "No DATABASE_URL provided - using SQLite (development only). "
                "Production requires postgresql+psycopg://...",
            )

        logging.info(f"[DEBUG] AFTER: database_url={database_url}")
        return values

    @validator("environment")
    def validate_environment(cls, v):
        """Validate environment value."""
        valid_envs = ["development", "dev", "production", "prod", "testing", "test"]
        if v.lower() not in valid_envs:
            raise ValueError(f"Invalid environment '{v}'. Must be one of: {valid_envs}")
        return v.lower()

    @validator("secret_key")
    def validate_secret_key(cls, v, values):
        """Validate secret key for production."""
        environment = values.get("environment", "development")
        is_production = values.get("is_production", False)

        if (environment.lower() in ["production", "prod"] or is_production) and v == "dev-secret-key":
            raise ValueError("CRITICAL ERROR: Default secret key not allowed in production")

        return v

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra environment variables (don't fail on unknown vars)


# Global settings instance
_settings: Settings | None = None


def get_config() -> Settings:
    """Get application configuration."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def validate_production_config():
    """Validate production configuration on startup."""
    config = get_config()

    if config.environment.lower() in ["production", "prod"] or config.is_production:
        logger = logging.getLogger(__name__)

        # Check critical settings
        if not config.openai_api_key:
            logger.warning("OpenAI API key not configured in production")

        if config.secret_key == "dev-secret-key":
            logger.error("CRITICAL: Using default secret key in production")
            raise ValueError("Default secret key not allowed in production")

        logger.info("Production configuration validated successfully")

    return config

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# Add project root to Python path (two levels up from db/migrations/)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import your models - ALL models must be imported for alembic to detect them
# These imports are intentionally "unused" but required for Alembic autogenerate
# ruff: noqa: F401
from api.models.user_report import UserReport  # noqa: E402

# CROWN SAFE: Import hair product safety models
from core_infra.crown_safe_models import (  # noqa: E402
    BrandCertificationModel,
    HairProductModel,
    HairProfileModel,
    IngredientModel,
    MarketInsightModel,
    ProductReviewModel,
    ProductScanModel,
    SalonAccountModel,
)
from core_infra.database import User  # noqa: E402
from core_infra.enhanced_database_schema import Base  # noqa: E402

# Import risk assessment models
from core_infra.risk_assessment_models import (  # noqa: E402
    CompanyComplianceProfile,
    DataIngestionJob,
    ProductDataSource,
    ProductGoldenRecord,
    ProductRiskProfile,
    RiskAssessmentReport,
    SafetyIncident,
)

# Import visual agent models
from core_infra.visual_agent_models import (  # noqa: E402
    ImageAnalysisCache,
    ImageExtraction,
    ImageJob,
    MFVSession,
    ReviewQueue,
)

# LEGACY BABY CODE: FamilyMember and Allergy models removed
# from core_infra.database import FamilyMember, Allergy
# Import incident reporting models
from db.models.incident_report import (  # noqa: E402
    AgencyNotification,
    IncidentCluster,
    IncidentReport,
)
from db.models.ingestion_run import IngestionRun  # noqa: E402
from db.models.privacy_request import PrivacyRequest  # noqa: E402
from db.models.report_record import ReportRecord  # noqa: E402

# Import other db models
from db.models.scan_history import SafetyReport, ScanHistory  # noqa: E402
from db.models.serial_verification import SerialVerification  # noqa: E402
from db.models.share_token import ShareToken  # noqa: E402

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def get_database_url():
    """Get database URL from environment or config."""
    # First try environment variable (for Docker/production)
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    # Fallback to config file
    return config.get_main_option("sqlalchemy.url")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

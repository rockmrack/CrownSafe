"""Shared SQLAlchemy Base for all models.

This module provides a single declarative_base() instance that should be
used by all ORM models to ensure proper metadata registration.
"""

from sqlalchemy.ext.declarative import declarative_base

# Single Base instance for all models
Base = declarative_base()

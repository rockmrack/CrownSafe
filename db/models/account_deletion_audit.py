from sqlalchemy import JSON, Column, DateTime, Integer, String
from sqlalchemy.sql import func

from core_infra.database import Base


class AccountDeletionAudit(Base):
    __tablename__ = "account_deletion_audit"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, index=True, nullable=False)
    jti = Column(String(64), index=True)
    status = Column(String(16), nullable=False)  # requested|completed|failed
    source = Column(String(16), nullable=True)  # mobile|web|api
    meta = Column(JSON, nullable=True)  # e.g., user agent, ip hash
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

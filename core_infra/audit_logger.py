"""
Audit logging system for BabyShield
Tracks all data changes for compliance and debugging
"""

import json
import logging
import traceback
from contextvars import ContextVar
from datetime import datetime
from functools import wraps
from typing import Any, Dict, List, Optional

from sqlalchemy import JSON, Column, DateTime, Integer, String, Text, event
from sqlalchemy.orm import Session

# Context variable for request tracking
current_user_context: ContextVar[Optional[int]] = ContextVar("current_user", default=None)
current_request_id: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


def get_base():
    """
    Lazy import of Base to avoid circular import.
    database.py needs to finish initializing before we can import Base.
    """
    from core_infra.database import Base

    return Base


class AuditLog(get_base()):
    """
    Audit log table for tracking all changes
    """

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    user_id = Column(Integer, nullable=True)  # Who made the change
    request_id = Column(String(50), nullable=True)  # Track related requests
    action = Column(String(50), nullable=False)  # CREATE, UPDATE, DELETE, VIEW
    entity_type = Column(String(100), nullable=False)  # Table/Model name
    entity_id = Column(String(100), nullable=True)  # ID of affected record
    old_value = Column(JSON, nullable=True)  # Previous state
    new_value = Column(JSON, nullable=True)  # New state
    changes = Column(JSON, nullable=True)  # Diff of changes
    ip_address = Column(String(45), nullable=True)  # Client IP
    user_agent = Column(Text, nullable=True)  # Browser/Client info
    endpoint = Column(String(255), nullable=True)  # API endpoint
    method = Column(String(10), nullable=True)  # HTTP method
    status_code = Column(Integer, nullable=True)  # Response status
    error = Column(Text, nullable=True)  # Error message if failed
    extra_metadata = Column(
        "metadata", JSON, nullable=True
    )  # Additional context (renamed to avoid SQLAlchemy reserved attribute)


class AuditLogger:
    """
    Main audit logging service
    """

    def __init__(self, db_session: Session = None):
        self.db_session = db_session
        self.logger = logging.getLogger(__name__)

    def log(
        self,
        action: str,
        entity_type: str,
        entity_id: Any = None,
        old_value: Dict = None,
        new_value: Dict = None,
        metadata: Dict = None,
        error: str = None,
    ):
        """
        Create an audit log entry
        """
        try:
            # Get context
            user_id = current_user_context.get()
            request_id = current_request_id.get()

            # Calculate changes
            changes = None
            if old_value and new_value:
                changes = self._calculate_diff(old_value, new_value)

            # Create audit entry
            audit_entry = AuditLog(
                user_id=user_id,
                request_id=request_id,
                action=action,
                entity_type=entity_type,
                entity_id=str(entity_id) if entity_id else None,
                old_value=old_value,
                new_value=new_value,
                changes=changes,
                error=error,
                metadata=metadata,
            )

            if self.db_session:
                self.db_session.add(audit_entry)
                # Don't commit here - let the main transaction handle it
                self.db_session.flush()

            # Also log to standard logger
            self.logger.info(
                f"AUDIT: {action} {entity_type} {entity_id}",
                extra={
                    "user_id": user_id,
                    "request_id": request_id,
                    "changes": changes,
                },
            )

        except Exception as e:
            self.logger.error(f"Failed to create audit log: {e}")

    def _calculate_diff(self, old: Dict, new: Dict) -> Dict:
        """
        Calculate differences between old and new values
        """
        changes = {}

        # Find changed fields
        all_keys = set(old.keys()) | set(new.keys())

        for key in all_keys:
            old_val = old.get(key)
            new_val = new.get(key)

            if old_val != new_val:
                changes[key] = {"old": old_val, "new": new_val}

        return changes if changes else None

    def log_create(self, entity: Any):
        """Log entity creation"""
        self.log(
            action="CREATE",
            entity_type=entity.__class__.__name__,
            entity_id=getattr(entity, "id", None),
            new_value=self._serialize_entity(entity),
        )

    def log_update(self, entity: Any, old_state: Dict):
        """Log entity update"""
        self.log(
            action="UPDATE",
            entity_type=entity.__class__.__name__,
            entity_id=getattr(entity, "id", None),
            old_value=old_state,
            new_value=self._serialize_entity(entity),
        )

    def log_delete(self, entity: Any):
        """Log entity deletion"""
        self.log(
            action="DELETE",
            entity_type=entity.__class__.__name__,
            entity_id=getattr(entity, "id", None),
            old_value=self._serialize_entity(entity),
        )

    def log_view(self, entity_type: str, entity_id: Any, metadata: Dict = None):
        """Log data access/viewing"""
        self.log(
            action="VIEW",
            entity_type=entity_type,
            entity_id=entity_id,
            metadata=metadata,
        )

    def log_api_call(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        user_id: int = None,
        error: str = None,
    ):
        """Log API calls"""
        self.log(
            action="API_CALL",
            entity_type="API",
            metadata={
                "endpoint": endpoint,
                "method": method,
                "status_code": status_code,
                "user_id": user_id,
            },
            error=error,
        )

    def _serialize_entity(self, entity: Any) -> Dict:
        """
        Serialize entity to dictionary
        """
        if hasattr(entity, "to_dict"):
            return entity.to_dict()
        elif hasattr(entity, "__dict__"):
            data = {}
            for key, value in entity.__dict__.items():
                if not key.startswith("_"):
                    try:
                        # Try to serialize
                        json.dumps(value)
                        data[key] = value
                    except (TypeError, ValueError):
                        # Fall back to string representation
                        data[key] = str(value)
            return data
        else:
            return {"value": str(entity)}


# SQLAlchemy event listeners for automatic audit logging
def setup_audit_listeners(Base, db_session):
    """
    Setup automatic audit logging for SQLAlchemy models
    """
    audit_logger = AuditLogger(db_session)

    @event.listens_for(Base, "after_insert", propagate=True)
    def receive_after_insert(mapper, connection, target):
        """Log after insert"""
        audit_logger.log_create(target)

    @event.listens_for(Base, "before_update", propagate=True)
    def receive_before_update(mapper, connection, target):
        """Store old state before update"""
        # Store old state in a temporary attribute
        target._audit_old_state = audit_logger._serialize_entity(target)

    @event.listens_for(Base, "after_update", propagate=True)
    def receive_after_update(mapper, connection, target):
        """Log after update"""
        old_state = getattr(target, "_audit_old_state", {})
        audit_logger.log_update(target, old_state)
        # Clean up
        if hasattr(target, "_audit_old_state"):
            delattr(target, "_audit_old_state")

    @event.listens_for(Base, "after_delete", propagate=True)
    def receive_after_delete(mapper, connection, target):
        """Log after delete"""
        audit_logger.log_delete(target)


# Decorators for audit logging
def audit_action(action: str, entity_type: str = None):
    """
    Decorator to audit function calls
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            audit_logger = AuditLogger()

            # Get entity type from function name if not provided
            entity = entity_type or func.__name__

            try:
                # Execute function
                result = func(*args, **kwargs)

                # Log success
                audit_logger.log(
                    action=action,
                    entity_type=entity,
                    metadata={
                        "function": func.__name__,
                        "args": str(args)[:100],  # Truncate for safety
                        "success": True,
                    },
                )

                return result

            except Exception as e:
                # Log failure
                audit_logger.log(
                    action=action,
                    entity_type=entity,
                    error=str(e),
                    metadata={
                        "function": func.__name__,
                        "args": str(args)[:100],
                        "success": False,
                        "traceback": traceback.format_exc(),
                    },
                )
                raise

        return wrapper

    return decorator


def audit_api_endpoint(func):
    """
    Decorator for auditing API endpoints
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        from fastapi import Request

        # Find request object in args
        request = None
        for arg in args:
            if isinstance(arg, Request):
                request = arg
                break

        audit_logger = AuditLogger()

        try:
            # Execute endpoint
            response = await func(*args, **kwargs)

            # Log success
            if request:
                audit_logger.log_api_call(
                    endpoint=request.url.path,
                    method=request.method,
                    status_code=200,
                    user_id=getattr(request.state, "user_id", None),
                )

            return response

        except Exception as e:
            # Log failure
            if request:
                audit_logger.log_api_call(
                    endpoint=request.url.path,
                    method=request.method,
                    status_code=500,
                    user_id=getattr(request.state, "user_id", None),
                    error=str(e),
                )
            raise

    return wrapper


# Query audit logs
class AuditQuery:
    """
    Query audit logs
    """

    def __init__(self, db_session: Session):
        self.db = db_session

    def get_user_activity(self, user_id: int, limit: int = 100) -> List[AuditLog]:
        """Get activity for a specific user"""
        return (
            self.db.query(AuditLog)
            .filter(AuditLog.user_id == user_id)
            .order_by(AuditLog.timestamp.desc())
            .limit(limit)
            .all()
        )

    def get_entity_history(self, entity_type: str, entity_id: str) -> List[AuditLog]:
        """Get history for a specific entity"""
        return (
            self.db.query(AuditLog)
            .filter(AuditLog.entity_type == entity_type, AuditLog.entity_id == entity_id)
            .order_by(AuditLog.timestamp.desc())
            .all()
        )

    def get_recent_changes(self, hours: int = 24) -> List[AuditLog]:
        """Get recent changes"""
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(hours=hours)

        return self.db.query(AuditLog).filter(AuditLog.timestamp >= cutoff).order_by(AuditLog.timestamp.desc()).all()

    def search_logs(
        self,
        action: str = None,
        entity_type: str = None,
        user_id: int = None,
        start_date: datetime = None,
        end_date: datetime = None,
    ) -> List[AuditLog]:
        """Search audit logs with filters"""
        query = self.db.query(AuditLog)

        if action:
            query = query.filter(AuditLog.action == action)
        if entity_type:
            query = query.filter(AuditLog.entity_type == entity_type)
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        if start_date:
            query = query.filter(AuditLog.timestamp >= start_date)
        if end_date:
            query = query.filter(AuditLog.timestamp <= end_date)

        return query.order_by(AuditLog.timestamp.desc()).all()


# Middleware to set audit context
async def audit_middleware(request, call_next):
    """
    Middleware to set audit context for requests
    """
    import uuid

    # Generate request ID
    request_id = str(uuid.uuid4())[:8]
    current_request_id.set(request_id)

    # Set user ID if authenticated
    if hasattr(request.state, "user"):
        current_user_context.set(request.state.user.id)

    # Process request
    response = await call_next(request)

    # Clear context
    current_request_id.set(None)
    current_user_context.set(None)

    return response

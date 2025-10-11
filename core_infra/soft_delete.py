"""
Soft delete functionality for BabyShield
Enables data recovery and maintains data history
"""

from sqlalchemy import Column, DateTime, Boolean, Integer, event
from sqlalchemy.orm import Query, Session
from sqlalchemy.ext.declarative import declared_attr
from datetime import datetime
from typing import Optional, List, Any, Dict
import logging

logger = logging.getLogger(__name__)


class SoftDeleteMixin:
    """
    Mixin to add soft delete functionality to any model

    Usage:
        class User(Base, SoftDeleteMixin):
            __tablename__ = "users"
            ...
    """

    @declared_attr
    def is_deleted(cls):
        """Flag to mark record as deleted"""
        return Column(Boolean, default=False, nullable=False, index=True)

    @declared_attr
    def deleted_at(cls):
        """Timestamp when record was deleted"""
        return Column(DateTime, nullable=True, index=True)

    @declared_attr
    def deleted_by(cls):
        """User ID who deleted the record"""
        return Column(Integer, nullable=True)

    def soft_delete(self, deleted_by_id: Optional[int] = None):
        """
        Soft delete this record
        """
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
        self.deleted_by = deleted_by_id

        logger.info(f"Soft deleted {self.__class__.__name__} id={getattr(self, 'id', 'unknown')}")

    def restore(self):
        """
        Restore a soft-deleted record
        """
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None

        logger.info(f"Restored {self.__class__.__name__} id={getattr(self, 'id', 'unknown')}")

    def hard_delete(self, session: Session):
        """
        Permanently delete this record (use with caution!)
        """
        logger.warning(
            f"Hard deleting {self.__class__.__name__} id={getattr(self, 'id', 'unknown')}"
        )
        session.delete(self)

    @classmethod
    def query_active(cls, session: Session) -> Query:
        """
        Query only active (non-deleted) records
        """
        return session.query(cls).filter(not cls.is_deleted)

    @classmethod
    def query_deleted(cls, session: Session) -> Query:
        """
        Query only deleted records
        """
        return session.query(cls).filter(cls.is_deleted)

    @classmethod
    def query_all(cls, session: Session) -> Query:
        """
        Query all records including deleted
        """
        return session.query(cls)


class SoftDeleteQuery(Query):
    """
    Custom query class that automatically filters out soft-deleted records
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._include_deleted = False

    def include_deleted(self) -> "SoftDeleteQuery":
        """
        Include soft-deleted records in results
        """
        self._include_deleted = True
        return self

    def only_deleted(self) -> "SoftDeleteQuery":
        """
        Return only soft-deleted records
        """
        return self.filter(self.column_descriptions[0]["type"].is_deleted)

    def __iter__(self):
        """
        Override iteration to filter soft-deleted by default
        """
        if not self._include_deleted:
            # Check if model has soft delete
            model = self.column_descriptions[0]["type"]
            if hasattr(model, "is_deleted"):
                return super().filter(not model.is_deleted).__iter__()

        return super().__iter__()

    def all(self):
        """
        Override all() to filter soft-deleted by default
        """
        if not self._include_deleted:
            model = self.column_descriptions[0]["type"]
            if hasattr(model, "is_deleted"):
                return super().filter(not model.is_deleted).all()

        return super().all()

    def first(self):
        """
        Override first() to filter soft-deleted by default
        """
        if not self._include_deleted:
            model = self.column_descriptions[0]["type"]
            if hasattr(model, "is_deleted"):
                return super().filter(not model.is_deleted).first()

        return super().first()

    def one(self):
        """
        Override one() to filter soft-deleted by default
        """
        if not self._include_deleted:
            model = self.column_descriptions[0]["type"]
            if hasattr(model, "is_deleted"):
                return super().filter(not model.is_deleted).one()

        return super().one()

    def count(self):
        """
        Override count() to filter soft-deleted by default
        """
        if not self._include_deleted:
            model = self.column_descriptions[0]["type"]
            if hasattr(model, "is_deleted"):
                return super().filter(not model.is_deleted).count()

        return super().count()


def soft_delete_filter(mapper, class_):
    """
    Automatically filter out soft-deleted records
    Add this as an event listener to your models
    """

    @event.listens_for(class_, "load", propagate=True)
    def receive_load(target, context):
        """Check if loaded instance is soft-deleted"""
        if hasattr(target, "is_deleted") and target.is_deleted:
            # Log access to deleted record
            logger.warning(
                f"Accessed soft-deleted {class_.__name__} id={getattr(target, 'id', 'unknown')}"
            )


class RecycleBin:
    """
    Manage soft-deleted records (like a recycle bin)
    """

    def __init__(self, session: Session):
        self.session = session

    def get_deleted_items(self, model: type, limit: int = 100, offset: int = 0) -> List[Any]:
        """
        Get deleted items of a specific type
        """
        if not hasattr(model, "is_deleted"):
            raise ValueError(f"{model.__name__} doesn't support soft delete")

        return (
            self.session.query(model)
            .filter(model.is_deleted)
            .order_by(model.deleted_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def restore_item(self, item: Any) -> bool:
        """
        Restore a soft-deleted item
        """
        if not hasattr(item, "restore"):
            raise ValueError(f"{type(item).__name__} doesn't support restore")

        try:
            item.restore()
            self.session.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to restore item: {e}")
            self.session.rollback()
            return False

    def restore_all(self, model: type) -> int:
        """
        Restore all deleted items of a type
        """
        if not hasattr(model, "is_deleted"):
            raise ValueError(f"{model.__name__} doesn't support soft delete")

        count = (
            self.session.query(model)
            .filter(model.is_deleted)
            .update(
                {
                    model.is_deleted: False,
                    model.deleted_at: None,
                    model.deleted_by: None,
                }
            )
        )

        self.session.commit()
        logger.info(f"Restored {count} {model.__name__} records")
        return count

    def empty_trash(self, model: type, older_than_days: int = 30) -> int:
        """
        Permanently delete old soft-deleted records
        """
        from datetime import timedelta

        if not hasattr(model, "is_deleted"):
            raise ValueError(f"{model.__name__} doesn't support soft delete")

        cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)

        # Get records to delete
        to_delete = (
            self.session.query(model).filter(model.is_deleted, model.deleted_at < cutoff_date).all()
        )

        count = len(to_delete)

        # Hard delete them
        for item in to_delete:
            self.session.delete(item)

        self.session.commit()
        logger.info(f"Permanently deleted {count} old {model.__name__} records")
        return count

    def get_deletion_stats(self) -> Dict[str, int]:
        """
        Get statistics about deleted records
        """
        stats = {}

        # Get all models with soft delete
        from core_infra.database import Base

        for model in Base.__subclasses__():
            if hasattr(model, "is_deleted"):
                count = self.session.query(model).filter(model.is_deleted).count()
                stats[model.__name__] = count

        return stats


# Cascade soft delete for relationships
def cascade_soft_delete(parent: Any, related_attr: str):
    """
    Soft delete related records when parent is soft deleted

    Usage:
        user.soft_delete()
        cascade_soft_delete(user, 'family_members')
    """
    if not hasattr(parent, related_attr):
        return

    related_items = getattr(parent, related_attr)

    if related_items:
        if isinstance(related_items, list):
            for item in related_items:
                if hasattr(item, "soft_delete"):
                    item.soft_delete(deleted_by_id=parent.deleted_by)
        else:
            if hasattr(related_items, "soft_delete"):
                related_items.soft_delete(deleted_by_id=parent.deleted_by)


# Middleware to track who deleted records
class DeletionTracker:
    """
    Track who is deleting records
    """

    @staticmethod
    def track_deletion(session: Session, user_id: int):
        """
        Set up tracking for this session
        """

        @event.listens_for(session, "before_flush")
        def receive_before_flush(session, flush_context, instances):
            """Track deletions before flush"""
            for instance in session.deleted:
                if hasattr(instance, "soft_delete"):
                    # Convert hard delete to soft delete
                    session.expunge(instance)
                    instance.soft_delete(deleted_by_id=user_id)
                    session.add(instance)


# Example usage with existing models
"""
# Update your models to use soft delete:

from core_infra.soft_delete import SoftDeleteMixin

class User(Base, SoftDeleteMixin):
    __tablename__ = "users"
    # ... existing fields ...

class Product(Base, SoftDeleteMixin):
    __tablename__ = "products"
    # ... existing fields ...

# In your API endpoints:

@app.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        # Soft delete instead of hard delete
        user.soft_delete(deleted_by_id=current_user.id)
        cascade_soft_delete(user, 'family_members')
        db.commit()
        return {"message": "User deleted"}
    
@app.post("/users/{user_id}/restore")
def restore_user(user_id: int, db: Session = Depends(get_db)):
    # Include deleted records in query
    user = db.query(User).include_deleted().filter(User.id == user_id).first()
    if user and user.is_deleted:
        user.restore()
        db.commit()
        return {"message": "User restored"}

# Admin recycle bin endpoint:

@app.get("/admin/recycle-bin")
def get_recycle_bin(db: Session = Depends(get_db)):
    bin = RecycleBin(db)
    stats = bin.get_deletion_stats()
    return {"deleted_items": stats}
"""

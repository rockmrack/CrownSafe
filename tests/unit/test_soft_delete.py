"""Unit tests for core_infra/soft_delete.py
Tests soft delete functionality, mixins, query classes, and recycle bin operations
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from sqlalchemy import Column, DateTime, Integer, String

from core_infra.soft_delete import (
    DeletionTracker,
    RecycleBin,
    SoftDeleteMixin,
    SoftDeleteQuery,
    cascade_soft_delete,
    soft_delete_filter,
)


class TestModel(SoftDeleteMixin):
    """Test model for soft delete functionality"""

    __tablename__ = "test_model"

    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)


class TestSoftDeleteMixin:
    """Test SoftDeleteMixin functionality"""

    def test_soft_delete_columns(self):
        """Test that soft delete columns are properly defined"""
        # Check that columns are declared attributes
        assert hasattr(TestModel, "is_deleted")
        assert hasattr(TestModel, "deleted_at")
        assert hasattr(TestModel, "deleted_by")

    def test_soft_delete_method(self):
        """Test soft_delete method"""
        model = TestModel()
        model.id = 1
        model.name = "Test Item"

        # Before soft delete
        assert model.is_deleted is False
        assert model.deleted_at is None
        assert model.deleted_by is None

        # Perform soft delete
        model.soft_delete(deleted_by_id=123)

        # After soft delete
        assert model.is_deleted is True
        assert model.deleted_at is not None
        assert model.deleted_by == 123

    def test_restore_method(self):
        """Test restore method"""
        model = TestModel()
        model.id = 1
        model.name = "Test Item"

        # Soft delete first
        model.soft_delete(deleted_by_id=123)
        assert model.is_deleted is True
        assert model.deleted_at is not None
        assert model.deleted_by == 123

        # Restore
        model.restore()

        # After restore
        assert model.is_deleted is False
        assert model.deleted_at is None
        assert model.deleted_by is None

    def test_hard_delete_method(self):
        """Test hard_delete method"""
        model = TestModel()
        model.id = 1
        model.name = "Test Item"

        mock_session = Mock()

        # Perform hard delete
        model.hard_delete(mock_session)

        # Should call session.delete
        mock_session.delete.assert_called_once_with(model)

    def test_query_active_classmethod(self):
        """Test query_active class method"""
        mock_session = Mock()
        mock_query = Mock()
        mock_session.query.return_value = mock_query

        result = TestModel.query_active(mock_session)

        mock_session.query.assert_called_once_with(TestModel)
        mock_query.filter.assert_called_once()
        assert result == mock_query.filter.return_value

    def test_query_deleted_classmethod(self):
        """Test query_deleted class method"""
        mock_session = Mock()
        mock_query = Mock()
        mock_session.query.return_value = mock_query

        result = TestModel.query_deleted(mock_session)

        mock_session.query.assert_called_once_with(TestModel)
        mock_query.filter.assert_called_once()
        assert result == mock_query.filter.return_value

    def test_query_all_classmethod(self):
        """Test query_all class method"""
        mock_session = Mock()
        mock_query = Mock()
        mock_session.query.return_value = mock_query

        result = TestModel.query_all(mock_session)

        mock_session.query.assert_called_once_with(TestModel)
        assert result == mock_query


class TestSoftDeleteQuery:
    """Test SoftDeleteQuery functionality"""

    def test_init(self):
        """Test SoftDeleteQuery initialization"""
        query = SoftDeleteQuery()
        assert query._include_deleted is False

    def test_include_deleted(self):
        """Test include_deleted method"""
        query = SoftDeleteQuery()
        result = query.include_deleted()

        assert result == query
        assert query._include_deleted is True

    def test_only_deleted(self):
        """Test only_deleted method"""
        query = SoftDeleteQuery()
        mock_model = Mock()
        mock_model.is_deleted = Mock()

        # Mock column_descriptions
        query.column_descriptions = [{"type": mock_model}]

        result = query.only_deleted()

        # Should call filter with is_deleted == True
        query.filter.assert_called_once()
        assert result == query.filter.return_value

    def test_iter_without_include_deleted(self):
        """Test __iter__ method without include_deleted"""

        class TestQuery(SoftDeleteQuery):
            def __iter__(self):
                return "mocked_iter"

        query = TestQuery()
        mock_model = Mock()
        mock_model.is_deleted = Mock()

        # Mock column_descriptions
        query.column_descriptions = [{"type": mock_model}]

        result = SoftDeleteQuery.__iter__(query)

        # Should call filter with is_deleted == False
        query.filter.assert_called_once()
        assert result == query.filter.return_value.__iter__.return_value

    def test_iter_with_include_deleted(self):
        """Test __iter__ method with include_deleted"""

        class TestQuery(SoftDeleteQuery):
            def __iter__(self):
                return "mocked_iter"

        query = TestQuery()
        query._include_deleted = True

        result = SoftDeleteQuery.__iter__(query)

        # Should not call filter
        query.filter.assert_not_called()
        assert result == "mocked_iter"

    def test_all_without_include_deleted(self):
        """Test all() method without include_deleted"""
        query = SoftDeleteQuery()
        mock_model = Mock()
        mock_model.is_deleted = Mock()

        # Mock column_descriptions
        query.column_descriptions = [{"type": mock_model}]

        result = query.all()

        # Should call filter with is_deleted == False
        query.filter.assert_called_once()
        assert result == query.filter.return_value.all.return_value

    def test_all_with_include_deleted(self):
        """Test all() method with include_deleted"""
        query = SoftDeleteQuery()
        query._include_deleted = True

        # Mock super().all()
        with patch("core_infra.soft_delete.Query.all") as mock_super_all:
            mock_super_all.return_value = []

            result = query.all()

            # Should not call filter
            query.filter.assert_not_called()
            assert result == mock_super_all.return_value

    def test_first_without_include_deleted(self):
        """Test first() method without include_deleted"""
        query = SoftDeleteQuery()
        mock_model = Mock()
        mock_model.is_deleted = Mock()

        # Mock column_descriptions
        query.column_descriptions = [{"type": mock_model}]

        result = query.first()

        # Should call filter with is_deleted == False
        query.filter.assert_called_once()
        assert result == query.filter.return_value.first.return_value

    def test_one_without_include_deleted(self):
        """Test one() method without include_deleted"""
        query = SoftDeleteQuery()
        mock_model = Mock()
        mock_model.is_deleted = Mock()

        # Mock column_descriptions
        query.column_descriptions = [{"type": mock_model}]

        result = query.one()

        # Should call filter with is_deleted == False
        query.filter.assert_called_once()
        assert result == query.filter.return_value.one.return_value

    def test_count_without_include_deleted(self):
        """Test count() method without include_deleted"""
        query = SoftDeleteQuery()
        mock_model = Mock()
        mock_model.is_deleted = Mock()

        # Mock column_descriptions
        query.column_descriptions = [{"type": mock_model}]

        result = query.count()

        # Should call filter with is_deleted == False
        query.filter.assert_called_once()
        assert result == query.filter.return_value.count.return_value


class TestSoftDeleteFilter:
    """Test soft_delete_filter function"""

    def test_soft_delete_filter(self):
        """Test soft_delete_filter event listener"""
        # This is more of an integration test
        # We'll test that the function can be called without error
        try:
            soft_delete_filter(Mock(), TestModel)
            # If no exception is raised, the test passes
            assert True
        except Exception as e:
            pytest.fail(f"soft_delete_filter raised an exception: {e}")


class TestRecycleBin:
    """Test RecycleBin functionality"""

    def test_init(self):
        """Test RecycleBin initialization"""
        mock_session = Mock()
        bin = RecycleBin(mock_session)
        assert bin.session == mock_session

    def test_get_deleted_items(self):
        """Test get_deleted_items method"""
        mock_session = Mock()
        mock_query = Mock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [
            Mock(),
            Mock(),
        ]

        bin = RecycleBin(mock_session)
        result = bin.get_deleted_items(TestModel, limit=10, offset=0)

        assert len(result) == 2
        mock_session.query.assert_called_once_with(TestModel)
        mock_query.filter.assert_called_once()
        mock_query.filter.return_value.order_by.assert_called_once()
        mock_query.filter.return_value.order_by.return_value.offset.assert_called_once_with(0)
        mock_query.filter.return_value.offset.return_value.limit.assert_called_once_with(10)

    def test_get_deleted_items_invalid_model(self):
        """Test get_deleted_items with model that doesn't support soft delete"""
        mock_session = Mock()
        bin = RecycleBin(mock_session)

        # Create a model without soft delete
        class NonSoftDeleteModel:
            pass

        with pytest.raises(ValueError, match="doesn't support soft delete"):
            bin.get_deleted_items(NonSoftDeleteModel)

    def test_restore_item(self):
        """Test restore_item method"""
        mock_session = Mock()
        mock_item = Mock()
        mock_item.restore = Mock()

        bin = RecycleBin(mock_session)
        result = bin.restore_item(mock_item)

        assert result is True
        mock_item.restore.assert_called_once()
        mock_session.commit.assert_called_once()

    def test_restore_item_failure(self):
        """Test restore_item method with failure"""
        mock_session = Mock()
        mock_item = Mock()
        mock_item.restore = Mock(side_effect=Exception("Restore failed"))

        bin = RecycleBin(mock_session)
        result = bin.restore_item(mock_item)

        assert result is False
        mock_item.restore.assert_called_once()
        mock_session.rollback.assert_called_once()

    def test_restore_item_invalid_item(self):
        """Test restore_item with item that doesn't support restore"""
        mock_session = Mock()
        mock_item = Mock()
        # Remove restore method
        del mock_item.restore

        bin = RecycleBin(mock_session)

        with pytest.raises(ValueError, match="doesn't support restore"):
            bin.restore_item(mock_item)

    def test_restore_all(self):
        """Test restore_all method"""
        mock_session = Mock()
        mock_query = Mock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value.update.return_value = 5

        bin = RecycleBin(mock_session)
        result = bin.restore_all(TestModel)

        assert result == 5
        mock_session.query.assert_called_once_with(TestModel)
        mock_query.filter.assert_called_once()
        mock_query.filter.return_value.update.assert_called_once()
        mock_session.commit.assert_called_once()

    def test_empty_trash(self):
        """Test empty_trash method"""
        mock_session = Mock()
        mock_query = Mock()
        mock_session.query.return_value = mock_query

        # Mock records to delete
        mock_records = [Mock(), Mock()]
        mock_query.filter.return_value.all.return_value = mock_records

        bin = RecycleBin(mock_session)
        result = bin.empty_trash(TestModel, older_than_days=30)

        assert result == 2
        mock_session.query.assert_called_once_with(TestModel)
        mock_query.filter.assert_called_once()
        # Should delete each record
        assert mock_session.delete.call_count == 2
        mock_session.commit.assert_called_once()

    def test_get_deletion_stats(self):
        """Test get_deletion_stats method"""
        mock_session = Mock()
        mock_query = Mock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value.count.return_value = 3

        bin = RecycleBin(mock_session)

        with patch("core_infra.soft_delete.Base") as mock_base:
            mock_base.__subclasses__.return_value = [TestModel]

            result = bin.get_deletion_stats()

            assert result == {TestModel.__name__: 3}
            mock_session.query.assert_called_once_with(TestModel)
            mock_query.filter.assert_called_once()


class TestCascadeSoftDelete:
    """Test cascade_soft_delete function"""

    def test_cascade_soft_delete_list(self):
        """Test cascade_soft_delete with list of items"""
        parent = Mock()
        parent.deleted_by = 123

        item1 = Mock()
        item1.soft_delete = Mock()
        item2 = Mock()
        item2.soft_delete = Mock()

        parent.family_members = [item1, item2]

        cascade_soft_delete(parent, "family_members")

        item1.soft_delete.assert_called_once_with(deleted_by_id=123)
        item2.soft_delete.assert_called_once_with(deleted_by_id=123)

    def test_cascade_soft_delete_single_item(self):
        """Test cascade_soft_delete with single item"""
        parent = Mock()
        parent.deleted_by = 123

        item = Mock()
        item.soft_delete = Mock()

        parent.family_member = item

        cascade_soft_delete(parent, "family_member")

        item.soft_delete.assert_called_once_with(deleted_by_id=123)

    def test_cascade_soft_delete_no_attribute(self):
        """Test cascade_soft_delete with non-existent attribute"""
        parent = Mock()

        # Should not raise an exception
        cascade_soft_delete(parent, "non_existent_attribute")

    def test_cascade_soft_delete_no_soft_delete_method(self):
        """Test cascade_soft_delete with item without soft_delete method"""
        parent = Mock()
        parent.deleted_by = 123

        item = Mock()
        # Remove soft_delete method
        del item.soft_delete

        parent.family_member = item

        # Should not raise an exception
        cascade_soft_delete(parent, "family_member")


class TestDeletionTracker:
    """Test DeletionTracker functionality"""

    def test_track_deletion(self):
        """Test track_deletion method"""
        mock_session = Mock()
        user_id = 123

        # Mock event listener
        with patch("core_infra.soft_delete.event") as mock_event:
            DeletionTracker.track_deletion(mock_session, user_id)

            # Should register a before_flush listener
            mock_event.listens_for.assert_called_once_with(mock_session, "before_flush")

    def test_track_deletion_callback(self):
        """Test the before_flush callback behavior"""
        mock_session = Mock()
        user_id = 123

        # Mock instances with soft_delete method
        mock_instance1 = Mock()
        mock_instance1.soft_delete = Mock()
        mock_instance2 = Mock()
        mock_instance2.soft_delete = Mock()

        mock_session.deleted = [mock_instance1, mock_instance2]

        # Create the callback function
        with patch("core_infra.soft_delete.event") as mock_event:
            DeletionTracker.track_deletion(mock_session, user_id)

            # Get the callback function
            callback = mock_event.listens_for.call_args[0][2]

            # Call the callback
            callback(mock_session, Mock(), [])

            # Should convert hard delete to soft delete
            mock_session.expunge.assert_called()
            mock_instance1.soft_delete.assert_called_once_with(deleted_by_id=user_id)
            mock_instance2.soft_delete.assert_called_once_with(deleted_by_id=user_id)
            mock_session.add.assert_called()


if __name__ == "__main__":
    pytest.main([__file__])

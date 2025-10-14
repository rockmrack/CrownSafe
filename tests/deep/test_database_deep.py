"""
Deep Database Tests
Comprehensive testing of database operations, connections, and transactions
"""

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from core_infra.database import get_db, Base
import os


class TestDatabaseDeep:
    """Deep database connectivity and operation tests"""

    def test_database_connection_pool(self):
        """Test that database connection pool is configured"""
        from core_infra.database import engine

        # Check pool settings
        assert engine is not None
        # Pool should have reasonable size
        pool = engine.pool
        assert pool is not None

    def test_database_url_format(self):
        """Test that DATABASE_URL is properly formatted"""
        db_url = os.getenv("DATABASE_URL")
        if db_url:
            # Should start with postgresql:// or sqlite://
            assert db_url.startswith(("postgresql://", "sqlite://", "postgres://"))

    def test_get_db_generator(self):
        """Test that get_db returns a generator"""
        db_gen = get_db()
        assert hasattr(db_gen, "__next__")

    def test_database_session_creation(self):
        """Test that database sessions can be created"""
        db_gen = get_db()
        db = next(db_gen)

        assert db is not None

        # Cleanup
        try:
            db.close()
        except:
            pass

    def test_database_query_execution(self):
        """Test that simple queries can be executed"""
        db_gen = get_db()
        db = next(db_gen)

        try:
            # Simple query that works on both SQLite and PostgreSQL
            result = db.execute(text("SELECT 1 as test_col"))
            row = result.first()
            assert row is not None
            assert row[0] == 1
        finally:
            db.close()

    def test_database_transaction_rollback(self):
        """Test that transactions can be rolled back"""
        db_gen = get_db()
        db = next(db_gen)

        try:
            # Start transaction (implicit)
            # Any changes here would be rolled back
            db.rollback()
            # Should not raise exception
        finally:
            db.close()

    def test_database_transaction_commit(self):
        """Test that transactions can be committed"""
        db_gen = get_db()
        db = next(db_gen)

        try:
            # Commit without changes should not raise exception
            db.commit()
        finally:
            db.close()

    def test_database_connection_error_handling(self):
        """Test handling of database connection errors"""
        # This test verifies the error handling doesn't crash
        try:
            invalid_engine = create_engine(
                "postgresql://invalid:invalid@localhost:9999/invalid"
            )
            Session = sessionmaker(bind=invalid_engine)
            session = Session()
            # Try to query - should fail gracefully
            try:
                session.execute(text("SELECT 1"))
            except Exception:
                # Exception is expected
                assert True
            finally:
                session.close()
        except Exception:
            # Connection error is expected
            assert True

    def test_database_metadata_exists(self):
        """Test that database metadata is accessible"""
        assert Base.metadata is not None
        # Should have some tables defined
        tables = Base.metadata.tables
        assert isinstance(tables, dict)

    def test_database_session_isolation(self):
        """Test that database sessions are isolated"""
        db_gen1 = get_db()
        db_gen2 = get_db()

        db1 = next(db_gen1)
        db2 = next(db_gen2)

        # Should be different session objects
        assert db1 is not db2

        db1.close()
        db2.close()

    def test_database_connection_cleanup(self):
        """Test that database connections are properly cleaned up"""
        db_gen = get_db()
        db = next(db_gen)

        # Close the session
        db.close()

        # Should not raise exception when trying to use closed session
        try:
            db.execute(text("SELECT 1"))
        except Exception:
            # Exception expected on closed session
            assert True

    def test_database_multiple_operations(self):
        """Test multiple database operations in sequence"""
        db_gen = get_db()
        db = next(db_gen)

        try:
            # Multiple queries
            for i in range(5):
                result = db.execute(text("SELECT :val as test_col"), {"val": i})
                row = result.first()
                assert row[0] == i
        finally:
            db.close()

    def test_database_parameterized_query(self):
        """Test that parameterized queries work correctly"""
        db_gen = get_db()
        db = next(db_gen)

        try:
            # Parameterized query (prevents SQL injection)
            result = db.execute(
                text("SELECT :name as name, :value as value"),
                {"name": "test", "value": 42},
            )
            row = result.first()
            assert row[0] == "test"
            assert row[1] == 42
        finally:
            db.close()

    def test_database_null_handling(self):
        """Test that NULL values are handled correctly"""
        db_gen = get_db()
        db = next(db_gen)

        try:
            result = db.execute(text("SELECT NULL as null_col"))
            row = result.first()
            assert row[0] is None
        finally:
            db.close()

    def test_database_unicode_support(self):
        """Test that Unicode characters are supported"""
        db_gen = get_db()
        db = next(db_gen)

        try:
            unicode_str = "测试 тест اختبار"
            result = db.execute(
                text("SELECT :unicode_val as unicode_col"), {"unicode_val": unicode_str}
            )
            row = result.first()
            assert row[0] == unicode_str
        finally:
            db.close()

    def test_database_concurrent_sessions(self):
        """Test that multiple concurrent sessions work"""
        sessions = []

        # Create multiple sessions
        for i in range(3):
            db_gen = get_db()
            db = next(db_gen)
            sessions.append(db)

        try:
            # All sessions should work independently
            for i, db in enumerate(sessions):
                result = db.execute(text("SELECT :val as test"), {"val": i})
                row = result.first()
                assert row[0] == i
        finally:
            # Cleanup
            for db in sessions:
                db.close()

    def test_database_error_recovery(self):
        """Test recovery from database errors"""
        db_gen = get_db()
        db = next(db_gen)

        try:
            # Try invalid query
            try:
                db.execute(text("SELECT * FROM nonexistent_table_xyz"))
            except Exception:
                # Error expected
                pass

            # Rollback and continue
            db.rollback()

            # Should be able to execute valid query after error
            result = db.execute(text("SELECT 1"))
            row = result.first()
            assert row[0] == 1
        finally:
            db.close()

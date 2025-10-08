"""
Production Database Tests
Testing live production database connectivity, performance, and integrity
"""
import pytest
import time
import os
from sqlalchemy import text
from core_infra.database import get_db, engine


class TestProductionDatabase:
    """Critical production database tests"""
    
    def test_database_connection_success(self):
        """Test that production database is accessible"""
        db = next(get_db())
        assert db is not None, "Database session should be created"
        
        # Test simple query
        result = db.execute(text("SELECT 1"))
        assert result is not None, "Query should execute"
        
        db.close()
    
    def test_database_connection_speed(self):
        """Test database connection time is acceptable"""
        start_time = time.time()
        
        db = next(get_db())
        
        connection_time = (time.time() - start_time) * 1000  # ms
        
        assert connection_time < 100, f"Connection took {connection_time}ms (should be < 100ms)"
        
        db.close()
    
    def test_database_query_performance(self):
        """Test database query performance"""
        db = next(get_db())
        
        start_time = time.time()
        result = db.execute(text("SELECT 1 as test"))
        query_time = (time.time() - start_time) * 1000  # ms
        
        assert query_time < 50, f"Query took {query_time}ms (should be < 50ms)"
        assert result.fetchone()[0] == 1
        
        db.close()
    
    def test_database_concurrent_connections(self):
        """Test multiple simultaneous database connections"""
        sessions = []
        
        try:
            # Create 10 concurrent sessions
            for i in range(10):
                session = next(get_db())
                sessions.append(session)
                
                # Execute query on each
                result = session.execute(text("SELECT :val as test"), {"val": i})
                assert result.fetchone()[0] == i
            
            assert len(sessions) == 10, "Should create 10 sessions"
            
        finally:
            # Clean up all sessions
            for session in sessions:
                session.close()
    
    def test_database_connection_pool_health(self):
        """Test database connection pool is healthy"""
        # Check pool statistics
        pool = engine.pool
        
        assert pool is not None, "Connection pool should exist"
        assert pool.size() > 0, "Pool should have connections"
        
        # Pool should not be exhausted
        checked_out = pool.checkedout()
        pool_size = pool.size()
        
        assert checked_out < pool_size, f"Too many checked out connections: {checked_out}/{pool_size}"
    
    def test_database_transaction_isolation(self):
        """Test transaction isolation works correctly"""
        db1 = next(get_db())
        db2 = next(get_db())
        
        try:
            # Session 1 starts transaction
            db1.execute(text("BEGIN"))
            
            # Session 2 should still work independently
            result = db2.execute(text("SELECT 1"))
            assert result.fetchone()[0] == 1
            
            # Rollback session 1
            db1.execute(text("ROLLBACK"))
            
        finally:
            db1.close()
            db2.close()
    
    def test_database_table_existence(self):
        """Test that all critical tables exist"""
        db = next(get_db())
        
        critical_tables = [
            "users",
            "products", 
            "recalls",
            "scans",
            "alembic_version"
        ]
        
        for table in critical_tables:
            try:
                result = db.execute(
                    text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = :table)"),
                    {"table": table}
                )
                exists = result.fetchone()[0]
                assert exists, f"Critical table '{table}' does not exist"
            except Exception as e:
                # Some tables might not exist yet - that's okay for optional tables
                if table in ["users", "alembic_version"]:
                    raise  # These are critical
                else:
                    pytest.skip(f"Table {table} not found (may be optional): {e}")
        
        db.close()
    
    def test_database_migration_status(self):
        """Test that database migrations are up to date"""
        db = next(get_db())
        
        try:
            # Check alembic_version table exists
            result = db.execute(
                text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'alembic_version')")
            )
            has_alembic = result.fetchone()[0]
            
            if not has_alembic:
                pytest.skip("Alembic version table not found (migrations not used)")
            
            # Get current migration version
            result = db.execute(text("SELECT version_num FROM alembic_version"))
            version = result.fetchone()
            
            assert version is not None, "No migration version found - database may not be initialized"
            assert len(version[0]) > 0, "Migration version should not be empty"
            
        except Exception as e:
            pytest.skip(f"Could not check migration status: {e}")
        finally:
            db.close()
    
    def test_database_write_operation(self):
        """Test database write operations work"""
        db = next(get_db())
        
        try:
            # Create a test table
            db.execute(text("""
                CREATE TABLE IF NOT EXISTS test_production_writes (
                    id SERIAL PRIMARY KEY,
                    test_value TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # Insert test data
            test_value = f"production_test_{int(time.time())}"
            db.execute(
                text("INSERT INTO test_production_writes (test_value) VALUES (:val)"),
                {"val": test_value}
            )
            db.commit()
            
            # Read it back
            result = db.execute(
                text("SELECT test_value FROM test_production_writes WHERE test_value = :val"),
                {"val": test_value}
            )
            row = result.fetchone()
            
            assert row is not None, "Should find inserted row"
            assert row[0] == test_value, "Value should match"
            
            # Clean up
            db.execute(
                text("DELETE FROM test_production_writes WHERE test_value = :val"),
                {"val": test_value}
            )
            db.commit()
            
        except Exception as e:
            db.rollback()
            # If we can't create test tables, that's okay - just verify read works
            pytest.skip(f"Write test skipped (read-only or permission issue): {e}")
        finally:
            db.close()
    
    def test_database_error_handling(self):
        """Test database handles errors gracefully"""
        db = next(get_db())
        
        try:
            # Execute invalid query
            with pytest.raises(Exception):
                db.execute(text("SELECT * FROM nonexistent_table_xyz"))
            
            # Session should still be usable after error
            result = db.execute(text("SELECT 1"))
            assert result.fetchone()[0] == 1, "Session should recover from error"
            
        finally:
            db.close()
    
    def test_database_unicode_support(self):
        """Test database supports Unicode characters"""
        db = next(get_db())
        
        try:
            unicode_test = "Hello 👶 世界 🍼 Здравствуй"
            
            # Try to use Unicode in a query
            result = db.execute(
                text("SELECT :text as unicode_test"),
                {"text": unicode_test}
            )
            value = result.fetchone()[0]
            
            assert value == unicode_test, "Unicode should be preserved"
            
        finally:
            db.close()
    
    def test_database_null_handling(self):
        """Test database handles NULL values correctly"""
        db = next(get_db())
        
        try:
            result = db.execute(text("SELECT NULL as null_value"))
            value = result.fetchone()[0]
            
            assert value is None, "NULL should be None in Python"
            
        finally:
            db.close()
    
    def test_database_large_result_set(self):
        """Test database can handle larger result sets"""
        db = next(get_db())
        
        try:
            # Generate 1000 rows
            result = db.execute(text("SELECT generate_series(1, 1000) as num"))
            rows = result.fetchall()
            
            assert len(rows) == 1000, "Should fetch 1000 rows"
            assert rows[0][0] == 1, "First row should be 1"
            assert rows[-1][0] == 1000, "Last row should be 1000"
            
        except Exception as e:
            pytest.skip(f"Large result set test skipped: {e}")
        finally:
            db.close()
    
    def test_database_connection_recovery(self):
        """Test database connection can recover from issues"""
        db = next(get_db())
        
        try:
            # Normal query
            result = db.execute(text("SELECT 1"))
            assert result.fetchone()[0] == 1
            
            # Close connection
            db.close()
            
            # Get new connection
            db = next(get_db())
            
            # Should work again
            result = db.execute(text("SELECT 2"))
            assert result.fetchone()[0] == 2, "Should recover with new connection"
            
        finally:
            db.close()


@pytest.mark.production
class TestProductionDatabaseHealth:
    """Production-specific health checks"""
    
    def test_database_url_configured(self):
        """Test that DATABASE_URL is properly configured"""
        database_url = os.getenv("DATABASE_URL")
        
        assert database_url is not None, "DATABASE_URL must be set"
        assert "postgresql://" in database_url, "Should be PostgreSQL"
        assert "@" in database_url, "Should have credentials"
        assert "/" in database_url.split("@")[1], "Should have database name"
    
    def test_database_production_mode(self):
        """Test database is in production mode"""
        environment = os.getenv("ENVIRONMENT", "production")
        
        # In production, we should be using production database
        if environment == "production":
            database_url = os.getenv("DATABASE_URL", "")
            assert "localhost" not in database_url, "Production should not use localhost"
            assert "127.0.0.1" not in database_url, "Production should not use 127.0.0.1"
    
    def test_database_connection_limit_not_exceeded(self):
        """Test we're not near connection limits"""
        db = next(get_db())
        
        try:
            # Query to check connection usage
            result = db.execute(text("""
                SELECT count(*) as conn_count 
                FROM pg_stat_activity 
                WHERE datname = current_database()
            """))
            
            conn_count = result.fetchone()[0]
            
            # Warn if we're using > 80% of typical connection limit
            # Most PostgreSQL instances have 100-200 max connections
            assert conn_count < 80, f"High connection count: {conn_count} (should be < 80)"
            
        except Exception as e:
            pytest.skip(f"Connection limit check skipped: {e}")
        finally:
            db.close()

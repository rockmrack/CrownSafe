-- =====================================================
-- Create Read-Only Database User for BabyShield
-- =====================================================
-- This script creates a read-only user for application queries
-- to minimize security risk from SQL injection or compromised credentials

-- Step 1: Create the read-only user
-- (Run as superuser or database owner)

-- Drop user if exists (for idempotency)
DROP USER IF EXISTS babyshield_readonly;

-- Create new user with strong password
-- IMPORTANT: Change this password and store securely!
CREATE USER babyshield_readonly WITH PASSWORD 'CHANGE_THIS_STRONG_PASSWORD_123!@#';

-- Step 2: Grant CONNECT privilege to the database
GRANT CONNECT ON DATABASE babyshield TO babyshield_readonly;

-- Step 3: Grant USAGE on schema
GRANT USAGE ON SCHEMA public TO babyshield_readonly;

-- Step 4: Grant SELECT on all existing tables
GRANT SELECT ON ALL TABLES IN SCHEMA public TO babyshield_readonly;

-- Step 5: Grant SELECT on all existing sequences (for reading current values)
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO babyshield_readonly;

-- Step 6: Set default privileges for future tables
-- This ensures new tables are automatically readable
ALTER DEFAULT PRIVILEGES IN SCHEMA public 
GRANT SELECT ON TABLES TO babyshield_readonly;

ALTER DEFAULT PRIVILEGES IN SCHEMA public 
GRANT SELECT ON SEQUENCES TO babyshield_readonly;

-- Step 7: Grant EXECUTE on specific read-only functions if any
-- Example: GRANT EXECUTE ON FUNCTION public.get_recall_count() TO babyshield_readonly;

-- =====================================================
-- Create Read-Write User for Admin Operations
-- =====================================================

-- Drop user if exists
DROP USER IF EXISTS babyshield_app;

-- Create application user with full access
CREATE USER babyshield_app WITH PASSWORD 'CHANGE_THIS_APP_PASSWORD_456!@#';

-- Grant full privileges
GRANT CONNECT ON DATABASE babyshield TO babyshield_app;
GRANT USAGE ON SCHEMA public TO babyshield_app;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO babyshield_app;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO babyshield_app;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO babyshield_app;

-- Set default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public 
GRANT ALL ON TABLES TO babyshield_app;

ALTER DEFAULT PRIVILEGES IN SCHEMA public 
GRANT ALL ON SEQUENCES TO babyshield_app;

ALTER DEFAULT PRIVILEGES IN SCHEMA public 
GRANT EXECUTE ON FUNCTIONS TO babyshield_app;

-- =====================================================
-- Create Admin User for Migrations
-- =====================================================

DROP USER IF EXISTS babyshield_admin;
CREATE USER babyshield_admin WITH PASSWORD 'CHANGE_THIS_ADMIN_PASSWORD_789!@#' CREATEDB CREATEROLE;

-- Grant superuser-like privileges for migrations
GRANT ALL PRIVILEGES ON DATABASE babyshield TO babyshield_admin;
GRANT ALL PRIVILEGES ON SCHEMA public TO babyshield_admin;
ALTER USER babyshield_admin SET search_path TO public;

-- =====================================================
-- Verify User Permissions
-- =====================================================

-- Check user privileges
SELECT 
    grantee,
    privilege_type,
    table_name
FROM information_schema.table_privileges
WHERE grantee IN ('babyshield_readonly', 'babyshield_app', 'babyshield_admin')
ORDER BY grantee, table_name
LIMIT 20;

-- Check user roles
SELECT 
    rolname,
    rolsuper,
    rolcreaterole,
    rolcreatedb,
    rolcanlogin
FROM pg_roles
WHERE rolname LIKE 'babyshield_%';

-- =====================================================
-- Row-Level Security (Optional but Recommended)
-- =====================================================

-- Enable RLS on sensitive tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE family_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;

-- Create policy for read-only user (can only see active users)
CREATE POLICY readonly_users_policy ON users
    FOR SELECT
    TO babyshield_readonly
    USING (is_active = true);

-- Create policy for app user (full access)
CREATE POLICY app_users_policy ON users
    FOR ALL
    TO babyshield_app
    USING (true)
    WITH CHECK (true);

-- =====================================================
-- Connection Limits and Security Settings
-- =====================================================

-- Set connection limits
ALTER USER babyshield_readonly CONNECTION LIMIT 100;
ALTER USER babyshield_app CONNECTION LIMIT 50;
ALTER USER babyshield_admin CONNECTION LIMIT 5;

-- Set statement timeout for readonly user (prevent long-running queries)
ALTER USER babyshield_readonly SET statement_timeout = '30s';

-- Set lock timeout
ALTER USER babyshield_readonly SET lock_timeout = '10s';

-- Prevent readonly user from creating objects
ALTER USER babyshield_readonly SET default_transaction_read_only = on;

-- =====================================================
-- Audit Configuration
-- =====================================================

-- Enable logging for security events
-- (Requires pg_audit extension)
-- CREATE EXTENSION IF NOT EXISTS pgaudit;

-- Configure audit logging for sensitive operations
-- ALTER SYSTEM SET pgaudit.log = 'ALL';
-- ALTER SYSTEM SET pgaudit.log_catalog = off;
-- ALTER SYSTEM SET pgaudit.log_parameter = on;
-- ALTER SYSTEM SET pgaudit.log_statement_once = on;

-- =====================================================
-- Usage in Application
-- =====================================================

/*
Connection strings for different operations:

1. Read-Only Operations (99% of queries):
   DATABASE_URL_READONLY="postgresql://babyshield_readonly:PASSWORD@host:5432/babyshield"

2. Write Operations (inserts, updates, deletes):
   DATABASE_URL="postgresql://babyshield_app:PASSWORD@host:5432/babyshield"

3. Migrations Only:
   DATABASE_URL_ADMIN="postgresql://babyshield_admin:PASSWORD@host:5432/babyshield"

Python example:
```python
from sqlalchemy import create_engine

# Use readonly for SELECT queries
readonly_engine = create_engine(os.environ['DATABASE_URL_READONLY'])

# Use app user for modifications
app_engine = create_engine(os.environ['DATABASE_URL'])

# Query with readonly
with readonly_engine.connect() as conn:
    result = conn.execute("SELECT * FROM recalls_enhanced WHERE id = %s", [recall_id])
```
*/

-- =====================================================
-- Monitoring Queries
-- =====================================================

-- Monitor active connections by user
SELECT 
    usename,
    application_name,
    client_addr,
    state,
    COUNT(*) as connection_count
FROM pg_stat_activity
WHERE usename LIKE 'babyshield_%'
GROUP BY usename, application_name, client_addr, state
ORDER BY connection_count DESC;

-- Monitor long-running queries
SELECT 
    usename,
    query,
    state,
    query_start,
    NOW() - query_start as duration
FROM pg_stat_activity
WHERE usename LIKE 'babyshield_%'
    AND state != 'idle'
    AND NOW() - query_start > interval '1 minute'
ORDER BY duration DESC;

-- =====================================================
-- Revoke Unnecessary Privileges
-- =====================================================

-- Revoke public access
REVOKE ALL ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON DATABASE babyshield FROM PUBLIC;

-- Only grant what's needed
GRANT USAGE ON SCHEMA public TO babyshield_readonly, babyshield_app, babyshield_admin;

-- =====================================================
-- Password Rotation Reminder
-- =====================================================

-- Set password expiration (requires PostgreSQL 10+)
-- ALTER USER babyshield_readonly VALID UNTIL '2024-04-01';
-- ALTER USER babyshield_app VALID UNTIL '2024-04-01';
-- ALTER USER babyshield_admin VALID UNTIL '2024-04-01';

-- =====================================================
-- Backup Script for User Recreation
-- =====================================================

/*
To regenerate users after database restore:

\set readonly_pass 'NEW_READONLY_PASSWORD'
\set app_pass 'NEW_APP_PASSWORD'
\set admin_pass 'NEW_ADMIN_PASSWORD'

CREATE USER babyshield_readonly WITH PASSWORD :'readonly_pass';
CREATE USER babyshield_app WITH PASSWORD :'app_pass';
CREATE USER babyshield_admin WITH PASSWORD :'admin_pass' CREATEDB CREATEROLE;

-- Then run this entire script
*/

-- =====================================================
-- Final Security Checks
-- =====================================================

-- Ensure no excessive privileges
SELECT 
    r.rolname,
    r.rolsuper,
    r.rolcreaterole,
    r.rolcreatedb,
    r.rolcanlogin,
    r.rolreplication,
    r.rolbypassrls,
    ARRAY(
        SELECT b.rolname
        FROM pg_catalog.pg_auth_members m
        JOIN pg_catalog.pg_roles b ON (m.roleid = b.oid)
        WHERE m.member = r.oid
    ) as memberof
FROM pg_catalog.pg_roles r
WHERE r.rolname LIKE 'babyshield_%'
ORDER BY 1;

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Read-only database user setup complete!';
    RAISE NOTICE 'Remember to:';
    RAISE NOTICE '1. Change all default passwords';
    RAISE NOTICE '2. Store passwords in AWS Parameter Store';
    RAISE NOTICE '3. Update connection strings in application';
    RAISE NOTICE '4. Test readonly access thoroughly';
    RAISE NOTICE '5. Set up password rotation schedule';
END $$;

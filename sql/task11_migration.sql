-- Task 11: Add OAuth and User Data Management fields
-- Run this on your production database

-- 1. Add OAuth fields to users table
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS provider_id VARCHAR(255) UNIQUE;

ALTER TABLE users 
ADD COLUMN IF NOT EXISTS provider_type VARCHAR(50);

ALTER TABLE users 
ADD COLUMN IF NOT EXISTS last_login TIMESTAMP;

ALTER TABLE users 
ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- 2. Make email optional for OAuth users (they might not provide it)
ALTER TABLE users 
ALTER COLUMN email DROP NOT NULL;

-- 3. Create index for faster OAuth lookups
CREATE INDEX IF NOT EXISTS ix_users_provider_id 
ON users(provider_id);

-- 4. Add settings tracking table (optional - if you want persistence)
CREATE TABLE IF NOT EXISTS user_settings (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    crashlytics_enabled BOOLEAN DEFAULT FALSE,
    notifications_enabled BOOLEAN DEFAULT TRUE,
    offline_mode BOOLEAN DEFAULT FALSE,
    auto_retry BOOLEAN DEFAULT TRUE,
    language VARCHAR(10) DEFAULT 'en',
    theme VARCHAR(10) DEFAULT 'auto',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id)
);

-- 5. Add privacy requests table for DSAR compliance
CREATE TABLE IF NOT EXISTS privacy_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_type VARCHAR(50) NOT NULL, -- 'export' or 'delete'
    user_id VARCHAR(255),
    email_hash VARCHAR(255),
    status VARCHAR(50) DEFAULT 'pending', -- pending, processing, completed, failed
    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    metadata JSONB,
    trace_id VARCHAR(100)
);

-- 6. Add audit log for privacy operations
CREATE TABLE IF NOT EXISTS privacy_audit_log (
    id SERIAL PRIMARY KEY,
    operation VARCHAR(50) NOT NULL,
    user_id VARCHAR(255),
    ip_address VARCHAR(45),
    user_agent TEXT,
    success BOOLEAN,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. Verify changes
SELECT 
    column_name, 
    data_type, 
    is_nullable
FROM information_schema.columns 
WHERE table_name = 'users' 
    AND column_name IN ('provider_id', 'provider_type', 'last_login', 'created_at');

-- 8. Sample query to check OAuth users (after deployment)
-- SELECT 
--     id, 
--     provider_type, 
--     last_login,
--     created_at
-- FROM users 
-- WHERE provider_id IS NOT NULL
-- LIMIT 10;

-- Enable pg_trgm extension for fuzzy text search in production
-- Run this directly on the PostgreSQL database if Alembic migration fails
-- 
-- Usage:
-- psql "postgresql://babyshield_user:MandarunLabadiena25!@babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com:5432/postgres" -f enable_pg_trgm_prod.sql

-- Enable the extension
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Verify it's enabled
SELECT * FROM pg_extension WHERE extname = 'pg_trgm';

-- Create GIN indexes for better fuzzy search performance
CREATE INDEX IF NOT EXISTS idx_recalls_product_trgm 
ON recalls_enhanced USING gin (lower(product_name) gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_recalls_brand_trgm 
ON recalls_enhanced USING gin (lower(brand) gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_recalls_description_trgm 
ON recalls_enhanced USING gin (lower(description) gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_recalls_hazard_trgm 
ON recalls_enhanced USING gin (lower(hazard) gin_trgm_ops);

-- Show created indexes
SELECT schemaname, tablename, indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'recalls_enhanced' 
AND indexname LIKE '%trgm%';

-- Test the similarity function
SELECT similarity('baby', 'baby');  -- Should return 1.0
SELECT similarity('baby', 'babe');  -- Should return ~0.75
SELECT similarity('baby', 'toddler');  -- Should return ~0.0

COMMIT;

# Migration Guide: Search Quality Improvements

## Quick Start

### 1. Apply Database Migration

```bash
# Run the migration
alembic upgrade head

# Verify pg_trgm is enabled
psql -d your_database -c "SELECT * FROM pg_extension WHERE extname = 'pg_trgm';"

# Analyze tables for optimizer
psql -d your_database -c "VACUUM ANALYZE recalls_enhanced;"
```

### 2. Verify Indexes Created

```sql
-- Check new indexes exist
SELECT indexname FROM pg_indexes 
WHERE tablename IN ('recalls', 'recalls_enhanced')
AND indexname LIKE '%trgm%';

-- Should see:
-- ix_recalls_enhanced_product_name_trgm
-- ix_recalls_enhanced_brand_trgm
-- ix_recalls_enhanced_description_trgm
-- ix_recalls_enhanced_hazard_trgm
```

### 3. Test Search Improvements

```bash
# Test fuzzy search (typo tolerance)
curl -X POST http://localhost:8000/api/v1/search/advanced \
  -H "Content-Type: application/json" \
  -d '{"product": "Triacting Nite", "limit": 3}'

# Test keyword AND logic
curl -X POST http://localhost:8000/api/v1/search/advanced \
  -H "Content-Type: application/json" \
  -d '{"keywords": ["baby", "food"], "limit": 5}'

# Test exact ID lookup
curl -X POST http://localhost:8000/api/v1/search/advanced \
  -H "Content-Type: application/json" \
  -d '{"id": "2024-FDA-12345"}'
```

### 4. Run Test Suite

```bash
# Run search quality tests
python tests/test_search_quality.py

# Or with pytest if available
pytest tests/test_search_quality.py -v
```

## Production Deployment Steps

### Step 1: Database Migration
```bash
# Backup database first!
pg_dump -h your_host -U your_user -d your_db > backup_before_search.sql

# Run migration
alembic upgrade 20250826_search_trgm

# Verify success
echo "SELECT COUNT(*) FROM pg_indexes WHERE indexname LIKE '%trgm%';" | psql
```

### Step 2: Deploy Code
```bash
# Deploy new code files:
# - api/main_babyshield.py (updated)
# - services/search_service.py (new)
# - api/health_endpoints.py (new)
# - api/recall_detail_endpoints.py (new)
# - core_infra/security_headers_middleware.py (new)

# Restart application
systemctl restart babyshield-api
# or
docker-compose restart api
```

### Step 3: Verify Deployment
```bash
# Check health endpoint
curl https://your-domain.com/api/v1/healthz

# Test search with new features
curl -X POST https://your-domain.com/api/v1/search/advanced \
  -H "Content-Type: application/json" \
  -d '{"product": "bottle", "keywords": ["bpa"], "limit": 5}'
```

## Rollback Plan

If issues arise:

### 1. Rollback Database
```bash
# Downgrade migration
alembic downgrade add_subscription_unique_constraint

# Restore from backup if needed
psql -h your_host -U your_user -d your_db < backup_before_search.sql
```

### 2. Rollback Code
```bash
# Revert to previous version
git revert HEAD
# or restore from backup

# Restart application
systemctl restart babyshield-api
```

## Performance Tuning

### PostgreSQL Configuration
```sql
-- Increase work memory for sorting
ALTER SYSTEM SET work_mem = '256MB';

-- Optimize for SSD storage
ALTER SYSTEM SET random_page_cost = 1.1;

-- Reload configuration
SELECT pg_reload_conf();
```

### Monitor Performance
```sql
-- Check query performance
SELECT 
    query,
    calls,
    mean_exec_time,
    max_exec_time
FROM pg_stat_statements
WHERE query LIKE '%similarity%'
ORDER BY mean_exec_time DESC;

-- Check index usage
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read
FROM pg_stat_user_indexes
WHERE indexname LIKE '%trgm%';
```

## Troubleshooting

### Issue: pg_trgm extension not found
```sql
-- As superuser:
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

### Issue: Slow fuzzy searches
```sql
-- Check if indexes are being used
EXPLAIN ANALYZE 
SELECT * FROM recalls_enhanced 
WHERE similarity(lower(product_name), 'bottle') > 0.08;

-- If not using index, recreate it:
DROP INDEX IF EXISTS ix_recalls_enhanced_product_name_trgm;
CREATE INDEX ix_recalls_enhanced_product_name_trgm 
ON recalls_enhanced USING gin (lower(product_name) gin_trgm_ops);
```

### Issue: Out of memory errors
```sql
-- Reduce work_mem temporarily
SET work_mem = '64MB';

-- Or increase system memory limits
```

## Success Metrics

After deployment, verify:

- ✅ Search latency P50 < 300ms
- ✅ Search latency P95 < 800ms
- ✅ Fuzzy matches finding results with 1-2 character typos
- ✅ Keyword AND logic working correctly
- ✅ Exact ID lookups < 50ms
- ✅ No increase in error rates

## Support

For issues or questions:
- Check logs: `/var/log/babyshield/api.log`
- Monitor metrics: Prometheus/Grafana dashboards
- Database queries: `pg_stat_statements` view

## Changelog

### Version 2.0.0 (2025-01-26)
- Added pg_trgm fuzzy matching
- Added keyword AND logic
- Added exact ID lookup
- Added deterministic sorting
- Improved search performance with indexes
- Added security headers
- Added health check endpoints
- Added comprehensive test suite

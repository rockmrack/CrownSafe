# UPSERT Optimization Implementation

## Overview
We've successfully implemented PostgreSQL's `INSERT ... ON CONFLICT` (UPSERT) operations to replace the inefficient check-then-insert pattern throughout the application.

## What Was Changed

### 1. **Core UPSERT Handler** (`core_infra/upsert_handler.py`)
- `UpsertHandler` class with methods for:
  - `upsert_recall()` - Single recall UPSERT
  - `bulk_upsert_recalls()` - Batch recall UPSERT
  - `upsert_subscription()` - Subscription UPSERT
- `EnhancedUpsertHandler` with history tracking capabilities

### 2. **Recall Ingestion** (`agents/recall_data_agent/agent_logic.py`)
- **Before**: 
  ```python
  exists = db.query(RecallDB).filter(RecallDB.recall_id == recall_data.recall_id).first()
  if exists:
      skipped_count += 1
      continue
  db.add(RecallDB(**filtered_payload))
  ```
- **After**: 
  ```python
  success = upsert_handler.upsert_recall(db, filtered_payload)
  ```

### 3. **Batch Processing** (`scripts/ingest_recalls.py`)
- **Before**: Check each record, then insert or update (2N queries)
- **After**: Single bulk UPSERT operation (1 query for N records)

### 4. **Subscription Management** (`core_infra/receipt_validator.py`)
- **Before**: Check for existing, then create or update
- **After**: Atomic UPSERT operation

### 5. **Database Schema Updates**
- Added unique constraint on `subscriptions(user_id, original_transaction_id)`
- Added `updated_at` columns for tracking modifications
- Existing unique constraint on `recalls(recall_id)` utilized

## Performance Improvements

| Metric | Old Method | New Method | Improvement |
|--------|------------|------------|-------------|
| **Queries per record** | 2 (SELECT + INSERT/UPDATE) | 1 (INSERT ON CONFLICT) | **50% reduction** |
| **Atomic operations** | Non-atomic (race conditions) | Fully atomic | **100% atomic** |
| **Batch processing** | 2N queries | 1 query | **Up to Nx faster** |
| **Network roundtrips** | 2 per record | 1 per batch | **50-99% reduction** |

## Benefits

### 1. **No Race Conditions**
- Atomic operations eliminate the window between check and insert
- No duplicate records possible even under high concurrency

### 2. **Better Performance**
- Fewer database queries = lower latency
- Reduced network traffic
- Less database CPU usage
- Better scalability

### 3. **Simpler Code**
- Less code to maintain
- Clearer intent
- Fewer error cases to handle

### 4. **Batch Efficiency**
- Process thousands of records in a single query
- Ideal for bulk data ingestion

## SQL Examples

### Single Record UPSERT
```sql
INSERT INTO recalls (recall_id, product_name, brand, ...) 
VALUES ('TEST-123', 'Product', 'Brand', ...)
ON CONFLICT (recall_id) 
DO UPDATE SET 
    product_name = EXCLUDED.product_name,
    brand = COALESCE(EXCLUDED.brand, recalls.brand),
    updated_at = CURRENT_TIMESTAMP
RETURNING recall_id, (xmax = 0) AS inserted;
```

### Bulk UPSERT
```sql
INSERT INTO recalls (recall_id, product_name, ...) 
VALUES 
    ('ID-1', 'Product 1', ...),
    ('ID-2', 'Product 2', ...),
    ('ID-3', 'Product 3', ...)
ON CONFLICT (recall_id) 
DO UPDATE SET 
    product_name = EXCLUDED.product_name,
    updated_at = CURRENT_TIMESTAMP;
```

## Usage

### For Single Records
```python
from core_infra.upsert_handler import upsert_handler

success = upsert_handler.upsert_recall(db, recall_data)
```

### For Bulk Operations
```python
counts = upsert_handler.bulk_upsert_recalls(db, recalls_list)
print(f"Inserted: {counts['inserted']}, Updated: {counts['updated']}")
```

### For Subscriptions
```python
success = upsert_handler.upsert_subscription(db, subscription_data)
```

## Testing
All UPSERT operations have been tested:
- ✅ Insert new records
- ✅ Update existing records
- ✅ Handle missing required fields
- ✅ Bulk operations
- ✅ Subscription UPSERT

## Migration
Run the migration to add required constraints:
```bash
alembic upgrade head
```

## Monitoring
The UPSERT operations return whether each record was inserted or updated, enabling:
- Accurate metrics on new vs updated records
- Detection of duplicate submission attempts
- Performance monitoring

## Conclusion
The UPSERT optimization has been successfully implemented across all critical data ingestion paths, providing:
- **50% fewer database queries**
- **100% atomic operations**
- **No race conditions**
- **Better performance at scale**

This optimization is production-ready and will significantly improve system performance, especially during bulk data ingestion operations.

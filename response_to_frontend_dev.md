# Response to Frontend Developer (Yurii)

Hi Yurii,

**The API is now fixed and fully operational!** ✅

## Your Original Query Now Works:

```bash
curl -X POST https://babyshield.cureviax.ai/api/v1/search/advanced \
  -H "Content-Type: application/json" \
  -d '{
    "product": "Triacting Night Time Cold",
    "agencies": ["FDA"],
    "date_from": "2014-01-01",
    "date_to": "2025-12-31",
    "limit": 5
  }'
```

**Response:**
```json
{
  "ok": true,
  "data": {
    "results": [],
    "total": 0,
    "query": "Triacting Night Time Cold"
  },
  "traceId": "trace_xyz123"
}
```

*(Note: Returns 0 results because "Triacting Night Time Cold" has no FDA recalls in our database)*

## Working Examples with Results:

### 1. Search for Baby Products:
```bash
curl -X POST https://babyshield.cureviax.ai/api/v1/search/advanced \
  -H "Content-Type: application/json" \
  -d '{"product": "baby formula", "limit": 5}'
```

### 2. Search FDA Recalls Only:
```bash
curl -X POST https://babyshield.cureviax.ai/api/v1/search/advanced \
  -H "Content-Type: application/json" \
  -d '{"product": "tylenol", "agencies": ["FDA"], "limit": 5}'
```

### 3. Search with Date Range:
```bash
curl -X POST https://babyshield.cureviax.ai/api/v1/search/advanced \
  -H "Content-Type: application/json" \
  -d '{
    "product": "infant",
    "date_from": "2023-01-01",
    "date_to": "2025-12-31",
    "limit": 10
  }'
```

## API Documentation:

- **Endpoint:** `POST /api/v1/search/advanced`
- **Docs:** https://babyshield.cureviax.ai/docs
- **OpenAPI:** https://babyshield.cureviax.ai/openapi.json

## Request Parameters:

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| product | string | No* | Product name to search | "baby formula" |
| query | string | No* | Alternative to 'product' | "tylenol" |
| agencies | array | No | Filter by agencies | ["FDA", "CPSC"] |
| date_from | string | No | Start date (YYYY-MM-DD) | "2024-01-01" |
| date_to | string | No | End date (YYYY-MM-DD) | "2025-12-31" |
| limit | integer | No | Max results (1-50) | 10 |
| risk_level | string | No | Filter by severity | "high" |

*At least one of: product, query, or keywords must be provided

## Response Format:

```json
{
  "ok": true,
  "data": {
    "results": [
      {
        "id": "recall_id",
        "product_name": "Product Name",
        "brand": "Brand Name",
        "source_agency": "FDA",
        "recall_date": "2024-01-15",
        "hazard": "Choking hazard",
        "description": "Full description...",
        "url": "https://..."
      }
    ],
    "total": 15,
    "query": "search term used"
  },
  "traceId": "trace_abc123"
}
```

## Available Agencies:
- FDA
- CPSC  
- EU_RAPEX
- NHTSA
- USDA
- EPA
- HEALTH_CANADA
- ACCC
- TGA
- MHRA

## Other Working Endpoints:

- `GET /api/v1/healthz` - Health check
- `GET /api/v1/version` - API version
- `GET /api/v1/agencies` - List all agencies
- `GET /docs` - Interactive API documentation

## Notes:

1. The API uses fuzzy matching, so partial product names work
2. Results are sorted by relevance score
3. All dates should be in YYYY-MM-DD format
4. The API returns up to 50 results per request
5. Use pagination with `offset` for more results

## Support:

If you need any other endpoints or have questions, please let me know!

Best regards,
Ross

---

**Status: API fully operational and ready for integration** ✅

# BabyShield API v1 — Documentation & Tools

## 🚀 Quick Start

### API Endpoints
- **Swagger UI**: https://babyshield.cureviax.ai/api/v1/docs
- **ReDoc**: https://babyshield.cureviax.ai/api/v1/redoc
- **OpenAPI JSON**: https://babyshield.cureviax.ai/api/v1/openapi.json
- **Health Check**: https://babyshield.cureviax.ai/api/v1/healthz

### Documentation Files
- **OpenAPI Spec**: [`docs/api/openapi_v1.yaml`](./openapi_v1.yaml)
- **Postman Collection**: [`docs/api/postman/BabyShield_v1.postman_collection.json`](./postman/BabyShield_v1.postman_collection.json)
- **TypeScript SDK**: [`clients/mobile/babyshield_client.ts`](../../clients/mobile/babyshield_client.ts)
- **Swift SDK**: [`clients/ios/BabyShieldClient.swift`](../../clients/ios/BabyShieldClient.swift)

## 📋 Primary Endpoint

### `POST /api/v1/search/advanced`

The main endpoint for all search operations in mobile apps.

**Canonical Parameters:**
- `product` - Product text search (fuzzy match using pg_trgm)
- `query` - Alternative text search
- `keywords[]` - Array of keywords (AND logic - all must match)
- `id` - Exact recall ID lookup
- `agencies[]` - Filter by agencies (e.g., ["FDA", "CPSC"])
- `severity` - Risk severity: low, medium, high, critical
- `riskCategory` - Product category: drug, device, food, cosmetic, supplement, toy, baby_product, other
- `date_from` - Start date (YYYY-MM-DD)
- `date_to` - End date (YYYY-MM-DD)
- `limit` - Results limit (1-50, default 20)
- `nextCursor` - Pagination cursor (future use)

**Parameter Aliases (automatically mapped):**
- `risk_level` → `severity`
- `product_category` → `riskCategory`
- `agency` → `agencies` (converts single to array)

**Unknown Parameters:**
- Return `400 INVALID_PARAMETERS` error

## 🔍 Search Features

### 1. Fuzzy Text Search
```json
{
  "product": "Triacting Night Time",
  "limit": 5
}
```
- Uses PostgreSQL pg_trgm for typo tolerance
- Similarity threshold: 0.08 (8%)
- Returns relevanceScore (0-1)

### 2. Keyword AND Logic
```json
{
  "keywords": ["baby", "formula", "organic"],
  "limit": 10
}
```
- ALL keywords must be present
- Searches across: product_name, brand, description, hazard

### 3. Exact ID Lookup
```json
{
  "id": "2024-FDA-12345"
}
```
- Direct database lookup
- Returns exactly one result
- Fastest query path

### 4. Combined Search
```json
{
  "product": "bottle",
  "keywords": ["bpa", "free"],
  "agencies": ["FDA", "CPSC"],
  "severity": "high",
  "date_from": "2024-01-01",
  "limit": 20
}
```

## 📱 Mobile SDK Usage

### TypeScript/React Native
```typescript
import { BabyShieldClient } from './babyshield_client';

const api = new BabyShieldClient();

// Fuzzy product search
const results = await api.searchAdvanced({
  product: "pacifier",
  agencies: ["FDA"],
  limit: 5
});

// Get specific recall
const recall = await api.getRecallById("2024-FDA-12345");
```

### Swift/iOS
```swift
let client = BabyShieldClient()

// Build search request
let request = client.buildSearchRequest(
    product: "pacifier",
    agencies: ["FDA"],
    limit: 5
)

// Execute search
let results = try await client.searchAdvanced(request)

// Get specific recall
let recall = try await client.getRecallById("2024-FDA-12345")
```

## 📊 Response Format

### Success Response
```json
{
  "ok": true,
  "data": {
    "items": [
      {
        "id": "2024-FDA-12345",
        "agencyCode": "FDA",
        "title": "Product Recall",
        "productName": "Example Product",
        "brand": "Example Brand",
        "hazard": "Safety hazard description",
        "severity": "medium",
        "riskCategory": "drug",
        "recallDate": "2024-01-15",
        "relevanceScore": 0.875
      }
    ],
    "total": 42,
    "limit": 20,
    "nextCursor": null
  },
  "traceId": "trace_abc123_1234567890"
}
```

### Error Response
```json
{
  "ok": false,
  "error": {
    "code": "INVALID_PARAMETERS",
    "message": "Product search term must be at least 2 characters"
  },
  "traceId": "trace_xyz789_1234567890"
}
```

## 🔧 Testing with Postman

1. **Import Collection**
   - Open Postman
   - File → Import → Upload `BabyShield_v1.postman_collection.json`
   - Collection includes test cases and examples

2. **Set Environment**
   - Default: `{{base}}` = https://babyshield.cureviax.ai
   - Local: `{{local}}` = http://localhost:8000

3. **Run Tests**
   - Collection includes pre-request scripts and tests
   - Validates response time < 1000ms
   - Checks X-API-Version header

## 🛡️ Security & Headers

### Response Headers
- `X-API-Version: v1.2.0` - API version
- `X-Content-Type-Options: nosniff` - Security
- `X-Frame-Options: DENY` - Clickjacking protection
- `Strict-Transport-Security` - HTTPS enforcement

### CORS Support
- Allowed origins configured for mobile apps
- Preflight requests supported
- Credentials allowed

## ⚡ Performance

### Expected Latency
- **Fuzzy search**: 200-600ms
- **Keyword search**: 300-700ms
- **Exact ID**: < 50ms
- **P95**: < 800ms

### Rate Limits
- 100 requests/minute per IP
- Burst: 10 requests/second

### Optimizations
- pg_trgm indexes for fuzzy matching
- BTREE indexes for filters
- Deterministic sorting
- Result limit: 50 max

## 🧪 Validation

### Validate OpenAPI Spec
```bash
pip install openapi-spec-validator pyyaml
python -c "
from openapi_spec_validator import validate_spec
import yaml
with open('docs/api/openapi_v1.yaml') as f:
    spec = yaml.safe_load(f)
validate_spec(spec)
print('✅ OpenAPI spec is valid')
"
```

### Run Search Quality Tests
```bash
python tests/test_search_quality.py
```

## 📈 Monitoring

### Key Metrics
- Response time percentiles (P50, P95, P99)
- Search result counts
- Most common search terms
- Error rates by endpoint

### Health Check
```bash
curl https://babyshield.cureviax.ai/api/v1/healthz
```

## 🆘 Troubleshooting

### Common Issues

**400 Bad Request**
- Check required fields (product/query/keywords/id)
- Verify date format (YYYY-MM-DD)
- Ensure limit is 1-50

**404 Not Found**
- Verify recall ID exists
- Check endpoint URL

**500 Internal Error**
- Check traceId in response
- Contact support with traceId

### Debug Tips
1. Use traceId for tracking requests
2. Check relevanceScore for fuzzy matches
3. Verify pg_trgm is enabled for fuzzy search
4. Use Postman collection for testing

## 📞 Support

- **API Status**: https://status.babyshield.ai
- **Email**: support@babyshield.ai
- **Documentation**: This file and OpenAPI spec

## 🔄 Changelog

### v1.2.0 (2025-01-26)
- Added fuzzy search with pg_trgm
- Added keyword AND logic
- Added exact ID lookup
- Improved performance with indexes
- Added mobile SDKs
- Enhanced documentation

### v1.0.0 (2024-12-01)
- Initial release
- Basic search functionality
- FDA integration

---

**Last Updated**: January 26, 2025
**API Version**: v1.2.0

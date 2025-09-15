# BabyShield API - App Store Readiness Guide

## Overview

This guide ensures the BabyShield API is stable, predictable, and properly documented for App Store and Google Play review processes.

## Quick Start

### Run the Readiness Check

```bash
# Run from project root
python scripts/appstore_readiness_check.py

# Or with custom URL
BABYSHIELD_BASE_URL=https://staging.babyshield.ai python scripts/appstore_readiness_check.py
```

### Expected Output

```
🚀 BABYSHIELD API - APP STORE READINESS CHECK
✅ /api/v1/healthz returns 200
✅ X-API-Version header present
✅ HSTS header present
✅ nosniff header present
✅ X-Frame-Options present
✅ Swagger UI reachable
✅ OpenAPI JSON reachable
✅ advanced search works
✅ aliases accepted
✅ error handling correct
✅ CORS configured
✅ p95 latency < 800ms
🎉 ALL CHECKS PASSED - API IS APP STORE READY!
```

## API Documentation

### Interactive Documentation
- **Swagger UI**: https://babyshield.cureviax.ai/docs
- **ReDoc**: https://babyshield.cureviax.ai/redoc  
- **OpenAPI JSON**: https://babyshield.cureviax.ai/openapi.json

### Versioned Endpoints (Redirects)
- `/api/v1/docs` → `/docs`
- `/api/v1/redoc` → `/redoc`
- `/api/v1/openapi.json` → `/openapi.json`

## Primary Search Endpoint

### POST /api/v1/search/advanced

**Canonical Parameters:**
- `product` (string) - Product search term [Recommended]
- `query` (string) - Alternative to product
- `agencies` (array) - Filter by agencies ["FDA", "CPSC", etc]
- `date_from` (string) - Start date YYYY-MM-DD
- `date_to` (string) - End date YYYY-MM-DD
- `risk_level` (string) - Risk level filter
- `product_category` (string) - Category filter
- `limit` (integer) - Max results (1-100, default 20)
- `nextCursor` (string) - Pagination cursor (future use)

**Accepted Aliases:**
- `severity` → `risk_level`
- `riskCategory` → `product_category`
- `agency` → `agencies` (converts single string to array)

**Example Request:**
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

**Example Response:**
```json
{
  "ok": true,
  "data": {
    "items": [
      {
        "id": "2024-FDA-12345",
        "productName": "Children's Triacting Night Time Cold",
        "brand": "P&L Developments, LLC",
        "hazard": "Incorrect dosing instructions",
        "recallDate": "2024-01-15",
        "agencyCode": "FDA",
        "severity": "medium"
      }
    ],
    "nextCursor": null,
    "total": 1
  },
  "traceId": "trace_abc123_1234567890"
}
```

## Quick Search Endpoints

### GET /api/v1/fda
```bash
curl "https://babyshield.cureviax.ai/api/v1/fda?product=doll&limit=20"
```

### GET /api/v1/agencies
```bash
curl "https://babyshield.cureviax.ai/api/v1/agencies"
```

## Individual Recall Detail

### GET /api/v1/recall/{recall_id}
```bash
curl "https://babyshield.cureviax.ai/api/v1/recall/2024-FDA-12345"
```

## Error Handling

### Standard Error Format
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

### Common Error Codes
- `400 BAD_REQUEST` - Invalid parameters or missing required fields
- `404 NOT_FOUND` - Recall ID not found
- `422 UNPROCESSABLE_ENTITY` - Validation errors
- `429 TOO_MANY_REQUESTS` - Rate limit exceeded
- `500 INTERNAL_ERROR` - Server error

## Security Headers

All responses include:
- `X-API-Version: v1.2.0`
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Strict-Transport-Security: max-age=63072000`
- `Access-Control-Allow-Origin: *` (or specific origin)

## Best Practices

### For Mobile Apps

1. **Use Short Search Terms**: Single words or short phrases work best
   - ✅ Good: "pacifier", "baby food", "car seat"
   - ❌ Avoid: Very long product descriptions

2. **Specify Product Over Query**: The `product` field is preferred
   ```json
   {"product": "bottle", "agencies": ["FDA"]}
   ```

3. **Use Canonical Parameters**: While aliases work, prefer the documented names
   - Use `risk_level` not `severity`
   - Use `product_category` not `riskCategory`

4. **Handle Errors Gracefully**: Check for `ok: false` and display user-friendly messages

5. **Implement Retry Logic**: For network failures or 500 errors

## Performance Expectations

- **P50 Latency**: < 200ms
- **P95 Latency**: < 800ms  
- **Availability**: 99.9% uptime
- **Rate Limits**: 100 requests/minute per IP

## Database Statistics

The API searches across:
- **39 International Agencies**
- **100,000+ Active Recalls**
- **Daily Updates** from all agencies
- **Real-time Data** (< 24h lag)

## Support

For technical issues or questions:
- Email: support@babyshield.ai
- API Status: https://status.babyshield.ai

## Compliance

The API is compliant with:
- ✅ GDPR (no PII in public endpoints)
- ✅ COPPA (no child data collection)
- ✅ HIPAA (no health data stored)
- ✅ App Store Guidelines
- ✅ Google Play Policies

---

**Last Updated**: January 2025
**API Version**: v1.2.0

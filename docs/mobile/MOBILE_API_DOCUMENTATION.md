# 🔌 BabyShield Mobile API Documentation

**Version**: 1.0  
**Base URL**: `https://babyshield.cureviax.ai`  
**Last Updated**: October 10, 2025

---

## 📋 Table of Contents

1. [Authentication](#authentication)
2. [Product Search & Barcode](#product-search--barcode)
3. [Recall Alerts](#recall-alerts)
4. [User Profile](#user-profile)
5. [Family Management](#family-management)
6. [Safety Reports](#safety-reports)
7. [Visual Recognition](#visual-recognition)
8. [Error Handling](#error-handling)
9. [Rate Limiting](#rate-limiting)
10. [TypeScript Types](#typescript-types)

---

## 🔐 Authentication

### Register New User

```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "first_name": "John",
  "last_name": "Doe",
  "phone": "+1234567890",
  "accept_terms": true
}
```

**Response (201 Created)**:
```json
{
  "id": "user_123abc",
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "created_at": "2025-10-10T12:00:00Z",
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 604800
}
```

### Login

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Response (200 OK)**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 604800,
  "user": {
    "id": "user_123abc",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe"
  }
}
```

### Refresh Token

```http
POST /api/v1/auth/refresh
Content-Type: application/json
Authorization: Bearer {refresh_token}

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

**Response (200 OK)**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 604800
}
```

### Password Reset Request

```http
POST /api/v1/auth/password-reset/request
Content-Type: application/json

{
  "email": "user@example.com"
}
```

**Response (200 OK)**:
```json
{
  "message": "Password reset email sent",
  "reset_token_expires_in": 3600
}
```

---

## 🔍 Product Search & Barcode

### Scan Barcode

```http
POST /api/v1/barcode/scan
Content-Type: application/json
Authorization: Bearer {access_token}

{
  "barcode": "012345678905",
  "barcode_type": "UPC-A"
}
```

**Response (200 OK)**:
```json
{
  "success": true,
  "product": {
    "id": "prod_abc123",
    "name": "Baby Monitor XYZ",
    "brand": "SafeBaby",
    "model_number": "SM-100",
    "category": "Baby Monitors",
    "image_url": "https://cdn.babyshield.com/products/sm100.jpg",
    "manufacturer": "SafeBaby Inc.",
    "description": "HD baby monitor with night vision"
  },
  "safety_status": {
    "status": "safe",
    "recall_count": 0,
    "last_checked": "2025-10-10T12:00:00Z"
  },
  "recalls": []
}
```

**Response with Recall (200 OK)**:
```json
{
  "success": true,
  "product": {
    "id": "prod_def456",
    "name": "Crib Model ABC",
    "brand": "BabyCrib Co",
    "model_number": "C-200"
  },
  "safety_status": {
    "status": "recalled",
    "recall_count": 1,
    "severity": "high",
    "last_checked": "2025-10-10T12:00:00Z"
  },
  "recalls": [
    {
      "id": "recall_789",
      "title": "Drop-side crib hazard",
      "description": "Drop-side can detach, creating entrapment hazard",
      "severity": "high",
      "recall_date": "2025-09-15",
      "agency": "CPSC",
      "url": "https://cpsc.gov/recalls/...",
      "remedy": "Free replacement or full refund"
    }
  ]
}
```

### Search Products

```http
GET /api/v1/products/search?q=baby+monitor&limit=20&offset=0
Authorization: Bearer {access_token}
```

**Response (200 OK)**:
```json
{
  "total": 45,
  "limit": 20,
  "offset": 0,
  "results": [
    {
      "id": "prod_abc123",
      "name": "Baby Monitor XYZ",
      "brand": "SafeBaby",
      "model_number": "SM-100",
      "category": "Baby Monitors",
      "image_url": "https://cdn.babyshield.com/products/sm100.jpg",
      "has_recalls": false,
      "safety_score": 95
    }
  ]
}
```

### Get Product Details

```http
GET /api/v1/products/{product_id}
Authorization: Bearer {access_token}
```

**Response (200 OK)**:
```json
{
  "id": "prod_abc123",
  "name": "Baby Monitor XYZ",
  "brand": "SafeBaby",
  "model_number": "SM-100",
  "category": "Baby Monitors",
  "image_url": "https://cdn.babyshield.com/products/sm100.jpg",
  "manufacturer": "SafeBaby Inc.",
  "description": "HD baby monitor with night vision and two-way audio",
  "features": [
    "1080p HD video",
    "Night vision",
    "Two-way audio",
    "Temperature monitoring"
  ],
  "specifications": {
    "dimensions": "5 x 3 x 7 inches",
    "weight": "1.2 lbs",
    "power": "AC adapter"
  },
  "safety_status": {
    "status": "safe",
    "recall_count": 0,
    "safety_score": 95,
    "certifications": ["FCC", "CE"]
  },
  "recalls": [],
  "created_at": "2025-01-15T10:00:00Z",
  "updated_at": "2025-10-10T12:00:00Z"
}
```

---

## 🚨 Recall Alerts

### Get Active Recalls

```http
GET /api/v1/recalls/active?limit=50&offset=0&category=all
Authorization: Bearer {access_token}
```

**Query Parameters**:
- `limit` (int): Number of results (default: 50, max: 100)
- `offset` (int): Pagination offset (default: 0)
- `category` (string): Filter by category (optional)
  - Values: `all`, `toys`, `cribs`, `car_seats`, `strollers`, `monitors`, etc.
- `severity` (string): Filter by severity (optional)
  - Values: `all`, `high`, `medium`, `low`

**Response (200 OK)**:
```json
{
  "total": 234,
  "limit": 50,
  "offset": 0,
  "recalls": [
    {
      "id": "recall_123",
      "title": "Baby Swing Recall - Fall Hazard",
      "description": "Swing can tip over causing injuries",
      "product_name": "Comfort Swing 3000",
      "brand": "BabySwing Co",
      "model_numbers": ["CS-3000", "CS-3001"],
      "severity": "high",
      "recall_date": "2025-10-01",
      "agency": "CPSC",
      "agency_country": "USA",
      "affected_units": 50000,
      "injuries_reported": 5,
      "remedy": "Free repair kit or full refund",
      "manufacturer_contact": {
        "phone": "1-800-123-4567",
        "email": "recalls@babyswing.com",
        "website": "https://babyswing.com/recalls"
      },
      "url": "https://cpsc.gov/recalls/2025/baby-swing",
      "image_url": "https://cdn.babyshield.com/recalls/recall_123.jpg"
    }
  ]
}
```

### Get User's Saved Product Alerts

```http
GET /api/v1/users/me/alerts
Authorization: Bearer {access_token}
```

**Response (200 OK)**:
```json
{
  "total_alerts": 3,
  "alerts": [
    {
      "id": "alert_456",
      "product": {
        "id": "prod_def456",
        "name": "Crib Model ABC",
        "brand": "BabyCrib Co",
        "image_url": "https://cdn.babyshield.com/products/c200.jpg"
      },
      "recall": {
        "id": "recall_789",
        "title": "Drop-side crib hazard",
        "severity": "high",
        "recall_date": "2025-09-15"
      },
      "created_at": "2025-09-16T08:00:00Z",
      "read": false,
      "dismissed": false
    }
  ]
}
```

### Save Product to Watch List

```http
POST /api/v1/products/{product_id}/watch
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "notify_on_recall": true,
  "notes": "Baby's crib"
}
```

**Response (201 Created)**:
```json
{
  "id": "watch_abc123",
  "product_id": "prod_def456",
  "user_id": "user_123abc",
  "notify_on_recall": true,
  "notes": "Baby's crib",
  "created_at": "2025-10-10T12:00:00Z"
}
```

---

## 👤 User Profile

### Get Current User Profile

```http
GET /api/v1/users/me
Authorization: Bearer {access_token}
```

**Response (200 OK)**:
```json
{
  "id": "user_123abc",
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "phone": "+1234567890",
  "profile": {
    "avatar_url": "https://cdn.babyshield.com/avatars/user123.jpg",
    "notification_preferences": {
      "email_alerts": true,
      "push_notifications": true,
      "sms_alerts": false
    },
    "privacy_settings": {
      "share_scan_history": false,
      "anonymous_analytics": true
    }
  },
  "subscription": {
    "tier": "premium",
    "status": "active",
    "expires_at": "2026-10-10T12:00:00Z"
  },
  "statistics": {
    "products_scanned": 45,
    "recalls_checked": 120,
    "alerts_received": 3
  },
  "created_at": "2025-01-10T10:00:00Z",
  "updated_at": "2025-10-10T12:00:00Z"
}
```

### Update User Profile

```http
PATCH /api/v1/users/me
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "first_name": "John",
  "last_name": "Smith",
  "phone": "+1234567890",
  "notification_preferences": {
    "email_alerts": true,
    "push_notifications": true,
    "sms_alerts": true
  }
}
```

**Response (200 OK)**:
```json
{
  "id": "user_123abc",
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Smith",
  "phone": "+1234567890",
  "updated_at": "2025-10-10T12:30:00Z"
}
```

---

## 👨‍👩‍👧‍👦 Family Management

### Get Family Members

```http
GET /api/v1/family/members
Authorization: Bearer {access_token}
```

**Response (200 OK)**:
```json
{
  "total": 2,
  "members": [
    {
      "id": "member_abc",
      "name": "Emma",
      "date_of_birth": "2023-05-15",
      "age_months": 17,
      "relationship": "daughter",
      "avatar_url": "https://cdn.babyshield.com/avatars/baby1.jpg",
      "product_preferences": {
        "age_appropriate_only": true,
        "sensitivity_alerts": ["latex", "phthalates"]
      },
      "created_at": "2025-01-15T10:00:00Z"
    }
  ]
}
```

### Add Family Member

```http
POST /api/v1/family/members
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "name": "Liam",
  "date_of_birth": "2024-08-20",
  "relationship": "son",
  "sensitivity_alerts": ["dairy", "fragrance"]
}
```

**Response (201 Created)**:
```json
{
  "id": "member_def",
  "name": "Liam",
  "date_of_birth": "2024-08-20",
  "age_months": 2,
  "relationship": "son",
  "created_at": "2025-10-10T12:00:00Z"
}
```

---

## 📊 Safety Reports

### Submit Safety Incident Report

```http
POST /api/v1/safety-reports
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "product_id": "prod_abc123",
  "incident_type": "injury",
  "severity": "medium",
  "description": "Baby's finger got pinched in the latch",
  "incident_date": "2025-10-09",
  "photos": [
    "https://upload.babyshield.com/temp/photo1.jpg"
  ],
  "contact_manufacturer": true
}
```

**Response (201 Created)**:
```json
{
  "id": "report_xyz789",
  "status": "submitted",
  "reference_number": "SR-2025-10-001234",
  "submitted_at": "2025-10-10T12:00:00Z",
  "estimated_review_time": "3-5 business days"
}
```

### Get User's Safety Reports

```http
GET /api/v1/safety-reports/me
Authorization: Bearer {access_token}
```

**Response (200 OK)**:
```json
{
  "total": 2,
  "reports": [
    {
      "id": "report_xyz789",
      "product": {
        "id": "prod_abc123",
        "name": "Baby Gate Pro"
      },
      "incident_type": "injury",
      "severity": "medium",
      "status": "under_review",
      "submitted_at": "2025-10-10T12:00:00Z",
      "reference_number": "SR-2025-10-001234"
    }
  ]
}
```

---

## 📸 Visual Recognition

### Analyze Product Image

```http
POST /api/v1/visual/analyze
Authorization: Bearer {access_token}
Content-Type: multipart/form-data

{
  "image": <binary file>,
  "analysis_type": "product_identification"
}
```

**Response (200 OK)**:
```json
{
  "status": "completed",
  "confidence": 0.92,
  "product": {
    "id": "prod_abc123",
    "name": "Baby Monitor XYZ",
    "brand": "SafeBaby",
    "model_number": "SM-100",
    "match_confidence": 0.92
  },
  "alternative_matches": [
    {
      "id": "prod_def456",
      "name": "Baby Monitor ABC",
      "brand": "SafeBaby",
      "confidence": 0.78
    }
  ],
  "safety_check": {
    "status": "safe",
    "recalls": []
  }
}
```

---

## ❌ Error Handling

### Error Response Format

All errors follow this format:

```json
{
  "error": {
    "code": "INVALID_BARCODE",
    "message": "Barcode format is invalid",
    "details": {
      "barcode": "invalid-format",
      "expected_format": "UPC-A, EAN-13, etc."
    },
    "request_id": "req_abc123xyz",
    "timestamp": "2025-10-10T12:00:00Z"
  }
}
```

### Common Error Codes

| HTTP Status | Error Code            | Description                 |
| ----------- | --------------------- | --------------------------- |
| 400         | `INVALID_REQUEST`     | Request body/params invalid |
| 401         | `UNAUTHORIZED`        | Missing or invalid token    |
| 403         | `FORBIDDEN`           | Insufficient permissions    |
| 404         | `NOT_FOUND`           | Resource not found          |
| 409         | `CONFLICT`            | Resource already exists     |
| 422         | `VALIDATION_ERROR`    | Input validation failed     |
| 429         | `RATE_LIMIT_EXCEEDED` | Too many requests           |
| 500         | `INTERNAL_ERROR`      | Server error                |
| 503         | `SERVICE_UNAVAILABLE` | Temporary outage            |

### Example Error Responses

**401 Unauthorized**:
```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Authentication required",
    "details": {
      "reason": "Missing or invalid access token"
    }
  }
}
```

**429 Rate Limit Exceeded**:
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests",
    "details": {
      "limit": 100,
      "window": "1 minute",
      "retry_after": 45
    }
  }
}
```

---

## ⏱️ Rate Limiting

### Rate Limits

| Endpoint Type      | Limit         | Window   |
| ------------------ | ------------- | -------- |
| Authentication     | 5 requests    | 1 minute |
| Barcode Scanning   | 100 requests  | 1 minute |
| Product Search     | 50 requests   | 1 minute |
| Visual Recognition | 20 requests   | 1 minute |
| General API        | 1000 requests | 1 hour   |

### Rate Limit Headers

Every response includes these headers:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1696950000
```

### Handling Rate Limits

```typescript
async function makeAPICall() {
  try {
    const response = await apiClient.get('/api/v1/products/search');
    return response.data;
  } catch (error) {
    if (error.response?.status === 429) {
      const retryAfter = error.response.headers['retry-after'];
      await sleep(retryAfter * 1000);
      return makeAPICall(); // Retry
    }
    throw error;
  }
}
```

---

## 📘 TypeScript Types

See the separate file: `babyshield-api-types.ts` for complete TypeScript type definitions.

Quick reference:

```typescript
import type {
  User,
  Product,
  Recall,
  ScanResponse,
  AuthResponse
} from './types/babyshield-api';

// Example usage
const handleScan = async (barcode: string): Promise<ScanResponse> => {
  const response = await apiClient.post<ScanResponse>('/api/v1/barcode/scan', {
    barcode
  });
  return response.data;
};
```

---

## 🔗 Additional Resources

- **API Status**: https://status.babyshield.com
- **Postman Collection**: [Download](https://babyshield.com/api/postman)
- **OpenAPI Spec**: https://babyshield.cureviax.ai/openapi.json
- **Support**: api-support@babyshield.dev

---

**Last Updated**: October 10, 2025  
**API Version**: 1.0  
**Contact**: dev@babyshield.dev

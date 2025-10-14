---
description: Apply this rule when implementing or reviewing API endpoints that
  use feature flags or authorization checks
alwaysApply: false
---

Always check feature flags and authorization before validating request parameters in API endpoints. This ensures proper HTTP status codes (403 Forbidden for disabled features vs 400 Bad Request for invalid data) and prevents validation errors from masking feature gating.
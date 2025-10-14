# Chat Feature Gating Fix - October 14, 2025

## Problem Summary
The CI test `test_conversation_blocked_when_chat_disabled_globally` was failing with:
```
AssertionError: assert 400 == 403
```

The endpoint was returning **400 Bad Request** (due to missing `message` parameter) instead of the expected **403 Forbidden** when chat was disabled globally.

## Root Cause
The chat conversation endpoint (`/api/v1/chat/conversation`) was checking request parameter validity **before** checking the feature flag. This violated the principle that **authorization checks should always precede validation**.

### Incorrect Order (Before Fix)
1. Parse JSON request body
2. ✅ Validate `message` parameter exists → **400 if missing**
3. Check `chat_enabled_for()` feature flag → 403 if disabled
4. Process request

### Problem
If a request came in with `chat_disabled_globally=True` but **no message parameter**, the endpoint would return 400 instead of 403.

## Solution Implemented

### Correct Order (After Fix)
1. Parse JSON request body
2. ✅ Check `chat_enabled_for()` feature flag → **403 if disabled** ← Moved up!
3. Validate `message` parameter exists → 400 if missing
4. Validate full request schema
5. Process request

### Code Changes in `api/routers/chat.py`

```python
@router.post("/conversation")
async def chat_conversation(request: Request) -> JSONResponse:
    """Main conversation endpoint"""
    try:
        trace_id = getattr(request.state, "trace_id", str(uuid4()))

        # Parse JSON
        try:
            payload = await request.json()
        except json.JSONDecodeError:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "request body must be valid JSON"},
            )

        # Check feature flag BEFORE validating request parameters
        # This ensures we return 403 for disabled features regardless of request validity
        user_id = payload.get("user_id")
        device_id = payload.get("device_id")

        if not chat_enabled_for(user_id, device_id):
            return JSONResponse(
                status_code=403,
                content={"error": True, "message": "chat_disabled"},
            )

        # Now validate request parameters AFTER feature flag check
        # This way, feature gating takes precedence over validation errors
        message = payload.get("message")
        if not isinstance(message, str) or not message.strip():
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "message is required"},
            )
        
        # Continue with request processing...
```

### Additional Improvements
1. **Added `device_id` to `ChatRequest` model** - Supports device-level rollout bucketing when user is not authenticated
2. **Enhanced JSON parsing** - Explicit error messages for invalid JSON or non-object payloads
3. **Added inline comments** - Explains the critical ordering for future maintainability

## Test Coverage

### Updated Tests in `tests/api/routers/test_chat_feature_gating.py`

1. ✅ `test_conversation_blocked_when_chat_disabled_globally` - **Previously failing, now passes**
   - Sends request **without** `message` parameter
   - Expects 403 Forbidden (not 400)
   
2. ✅ `test_conversation_blocked_when_user_not_in_rollout`
   - User not in rollout percentage
   - Expects 403 Forbidden
   
3. ✅ `test_conversation_allowed_when_user_in_rollout`
   - User in rollout, valid request
   - Expects 200 OK with response
   
4. ✅ `test_feature_gating_uses_user_and_device_ids`
   - Tests device_id-based bucketing
   - Expects proper flag check with device_id
   
5. ✅ `test_explain_result_not_gated`
   - Explain endpoint bypasses feature gate
   - Expects 200 OK regardless of feature flag

### Test Results
```bash
$ pytest tests/api/routers/test_chat_feature_gating.py -v
==================== test session starts ====================
collected 5 items 

tests/api/routers/test_chat_feature_gating.py .....  [100%]

==================== 5 passed, 1 warning in 5.78s ====================
```

## Health Check Enhancement

While fixing the chat endpoints, we also added API-prefixed health check aliases to support various readiness probe configurations:

### New Endpoints
- `/api/health` → `{"status": "ok"}`
- `/api/healthz` → `{"status": "ok"}`
- `/api/v1/health` → `{"status": "ok"}`
- `/api/v1/healthz` → `{"status": "ok"}`

These join the existing:
- `/health` → `{"status": "ok"}`
- `/healthz` → `{"status": "ok"}` (raw ASGI, bypasses middleware)
- `/readyz` → Full readiness check with DB connectivity

### Test Coverage
Added `test_api_prefixed_health_aliases` to verify all prefixed variants return 200 OK.

## Git Commit

```bash
commit 1d8de7a
fix(chat): ensure feature flag check precedes validation

- Move chat_enabled_for() check before request parameter validation
- Return 403 Forbidden when chat disabled, regardless of request validity
- Add device_id to ChatRequest model for rollout bucketing
- Improve JSON parsing with explicit error messages

This fixes the test failure where the endpoint was returning 400 instead
of 403 when chat was disabled globally. Feature authorization checks
now properly precede input validation.

feat(health): add API-prefixed health check aliases

- Add /api/health, /api/healthz, /api/v1/health, /api/v1/healthz
- Support readiness probes expecting API prefix
- All return standard {"status": "ok"} response
- Include integration test coverage
```

## Expected HTTP Status Codes

| Scenario                                 | Expected Status     | Reasoning                             |
| ---------------------------------------- | ------------------- | ------------------------------------- |
| Chat disabled globally + invalid request | **403 Forbidden**   | Feature auth failure takes precedence |
| Chat enabled + invalid request           | **400 Bad Request** | Validation failure                    |
| Chat enabled + valid request             | **200 OK**          | Success                               |
| Chat disabled + valid request            | **403 Forbidden**   | Feature auth failure                  |

## API Design Principle

> **Authorization checks must always precede validation checks**

This ensures:
1. Security - Don't leak information about request structure to unauthorized users
2. Clarity - Clear HTTP status codes (403 = forbidden, 400 = bad input)
3. Efficiency - No need to validate complex payloads for unauthorized requests

## Next Steps

1. ✅ Tests pass locally
2. ✅ Commit pushed to GitHub
3. ⏳ CI workflow will re-run automatically
4. ⏳ Verify GitHub Actions passes

## References

- **PR/Commit**: `1d8de7a`
- **Files Changed**:
  - `api/routers/chat.py` - Fixed endpoint ordering
  - `tests/api/routers/test_chat_feature_gating.py` - Updated test suite
  - `api/main_babyshield.py` - Added health aliases
  - `tests/integration/test_api_endpoints.py` - Added health alias test

---

**Fixed by**: GitHub Copilot (Opus)  
**Reviewed and deployed by**: GitHub Copilot (Sonnet)  
**Date**: October 14, 2025

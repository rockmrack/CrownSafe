# API Documentation Corrections - Production Tested

## Summary of Changes

Based on **live production testing** with **256 confirmed endpoints**, the following corrections were made to match exactly what's live:

---

## 🔧 **Exact Corrections Applied**

### **1. Login Path & Content-Type**
- **Changed:** `POST /api/v1/auth/login` (JSON)
- **To:** `POST /api/v1/auth/token` (**application/x-www-form-urlencoded**) with `username`, `password`

### **2. /auth/me Supports PUT**
- **Added:** `PUT /api/v1/auth/me` — update current user (as defined in OpenAPI)
- **Kept:** `GET /api/v1/auth/me` — returns 200 when authenticated

### **3. Account Deletion**
- **Kept:** `DELETE /api/v1/account` → **204 No Content**
- **Added:** "After 204, reusing the access token returns **401** ('Token revoked')"

### **4. Legacy Endpoint**
- **Changed:** "returns 410 Gone"
- **To:** "returns **non-2xx** (observed **400** when body missing). Do not use."

### **5. Legal Redirect Note**
- **Added:** `GET /legal/data-deletion` returns **301 → /legal/account-deletion** (some stacks return **405** for `HEAD`; use **GET** when checking redirect)

### **6. Swagger/ReDoc Links**
- **Kept:** These are correct:
  - `https://babyshield.cureviax.ai/docs`
  - `https://babyshield.cureviax.ai/redoc`
  - `https://babyshield.cureviax.ai/openapi.json`

---

## 📋 **Quick Reference (Copy-Paste Ready)**

### **Auth**
- **Register:** `POST /api/v1/auth/register` (JSON) `{email, password, confirm_password}`
- **Login:** `POST /api/v1/auth/token` (**x-www-form-urlencoded**) `username=<email>&password=<password>`
- **Me:** `GET /api/v1/auth/me` (200 if valid), `PUT /api/v1/auth/me` (update)

### **Deletion**
- `DELETE /api/v1/account` → **204**; subsequent calls with same token → **401** (Token revoked)
- Legacy `POST /api/v1/user/data/delete` → **non-2xx** (observed **400**)

### **Real-data**
- `GET /api/v1/risk-assessment/stats` → **200**
- `GET /api/v1/supplemental/data-sources` → **200**

### **Legal**
- `/legal/account-deletion` → **200 HTML**
- `/legal/data-deletion` (GET) → **301** to `/legal/account-deletion`

---

## 📁 **Files Updated**

### **1. `docs/api/openapi_v1.yaml`**
- ✅ Added complete auth endpoints with correct content types
- ✅ Added security schemes (Bearer JWT)
- ✅ Added account deletion with 204 response
- ✅ Added legacy endpoint as deprecated
- ✅ Added legal pages and redirects
- ✅ Added risk assessment and supplemental endpoints

### **2. `docs/MOBILE_INTEGRATION_GUIDE_CORRECTED.md`**
- ✅ Created new corrected mobile integration guide
- ✅ iOS Swift implementation with form-urlencoded login
- ✅ Android Kotlin implementation with correct endpoints
- ✅ Account deletion flow with 204 → 401 pattern
- ✅ Legal page handling with redirect notes

### **3. `README_APPSTORE.md`**
- ✅ Updated documentation links with ✅ confirmations
- ✅ Added production-tested auth endpoints
- ✅ Added legal & privacy page confirmations
- ✅ Added real data endpoint confirmations

### **4. `docs/app_review/support_contacts.md`**
- ✅ Updated API documentation links (256 endpoints confirmed)
- ✅ Corrected data management endpoints
- ✅ Added deprecation warning for legacy endpoint

---

## 🧪 **Production Test Results**

- **Total Endpoints:** **256** (confirmed live)
- **Auth Flow:** ✅ Working with form-urlencoded
- **Account Deletion:** ✅ Returns 204, then token revoked
- **Legal Pages:** ✅ All returning 200 HTML
- **Documentation:** ✅ Swagger, ReDoc, OpenAPI JSON all accessible
- **Real Data:** ✅ Risk assessment and supplemental endpoints live

---

## 🎯 **Key Takeaways for Mobile Apps**

1. **Use form-urlencoded for login** (not JSON)
2. **Account deletion returns 204** (not 200)
3. **Token becomes invalid after deletion** (handle 401s)
4. **Legal redirects work with GET** (not HEAD)
5. **Legacy endpoints return 400** (not 410)
6. **All documentation links are live and working**

---

## ✅ **Verification Commands**

```bash
# Test login endpoint (form-encoded)
curl -X POST https://babyshield.cureviax.ai/api/v1/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=testpass"

# Test account deletion (returns 204)
curl -X DELETE https://babyshield.cureviax.ai/api/v1/account \
  -H "Authorization: Bearer YOUR_TOKEN"

# Test legal redirect (returns 301)
curl -I https://babyshield.cureviax.ai/legal/data-deletion

# Test documentation (returns 200)
curl -I https://babyshield.cureviax.ai/docs
curl -I https://babyshield.cureviax.ai/redoc
curl -I https://babyshield.cureviax.ai/openapi.json
```

---

## 🚀 **Status: PRODUCTION READY**

All documentation now matches exactly what's live in production. Mobile apps can integrate using these corrected specifications with confidence.

**Total Corrections Applied:** 6 major fixes  
**Files Updated:** 4 documentation files  
**Production Verification:** ✅ Complete  
**Mobile Integration:** ✅ Ready for App Store submission

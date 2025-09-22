# Task 11: App Integration QA Test Plan

## Overview
Comprehensive test plan for OAuth authentication, DSAR compliance, and Crashlytics integration in the BabyShield mobile app.

---

## 1. OAuth Authentication Testing

### 1.1 Apple Sign-In

#### Test Case: ASI-001 - Successful Apple Sign-In
**Preconditions:** User has Apple ID
**Steps:**
1. Open app
2. Tap "Sign in with Apple"
3. Complete Apple authentication
4. Verify JWT tokens received

**Expected Results:**
- User authenticated successfully
- Access token valid for 1 hour
- Refresh token valid for 30 days
- No email stored in database

#### Test Case: ASI-002 - Apple Sign-In with Invalid Token
**Steps:**
1. Attempt sign-in with malformed token
2. Verify error handling

**Expected Results:**
- HTTP 401 Unauthorized
- Clear error message displayed
- No user created

#### Test Case: ASI-003 - Apple Sign-In Offline
**Steps:**
1. Enable airplane mode
2. Attempt Apple sign-in
3. Verify offline handling

**Expected Results:**
- Appropriate offline message
- Request queued if retry enabled
- No crash

### 1.2 Google Sign-In

#### Test Case: GSI-001 - Successful Google Sign-In
**Preconditions:** User has Google account
**Steps:**
1. Open app
2. Tap "Sign in with Google"
3. Complete Google authentication
4. Verify JWT tokens received

**Expected Results:**
- User authenticated successfully
- User ID returned
- No email stored

#### Test Case: GSI-002 - Google Token Expiration
**Steps:**
1. Sign in with Google
2. Wait for token expiration
3. Attempt API call
4. Verify refresh token flow

**Expected Results:**
- Automatic token refresh
- No user intervention required
- Seamless experience

### 1.3 Cross-Platform Testing

#### Test Case: XP-001 - Sign-In Across Devices
**Steps:**
1. Sign in on iOS device
2. Sign in with same account on Android
3. Verify same user_id

**Expected Results:**
- Consistent user_id across platforms
- Settings synchronized
- No duplicate accounts

---

## 2. Data Export Testing

### Test Case: DE-001 - Export User Data (JSON)
**Endpoints:** `POST /api/v1/user/data/export`
**Steps:**
1. Authenticate user
2. Navigate to Settings > Privacy
3. Tap "Export My Data"
4. Select JSON format
5. Confirm export

**Expected Results:**
```json
{
  "ok": true,
  "request_id": "req_abc123",
  "status": "completed",
  "data": {
    "user_id": "123",
    "settings": {...},
    "activity": {...}
  }
}
```

### Test Case: DE-002 - Export with No Data
**Steps:**
1. New user signs in
2. Immediately request export
3. Verify empty data handling

**Expected Results:**
- Export succeeds
- Contains minimal user info
- Clear indication of no activity

### Test Case: DE-003 - Export During High Load
**Steps:**
1. Simulate 100 concurrent exports
2. Monitor response times
3. Verify all complete

**Expected Results:**
- All exports successful
- Response time < 5 seconds
- No timeouts

---

## 3. Data Deletion Testing

### Test Case: DD-001 - Delete All User Data
**Endpoints:** `DELETE /api/v1/account`
**Steps:**
1. Create user with data
2. Navigate to Settings > Privacy
3. Tap "Delete My Account"
4. Confirm deletion twice
5. Submit request

**Expected Results:**
- Confirmation dialog shown
- Warning about permanence
- All data deleted
- User logged out

### Test Case: DD-002 - Deletion Without Confirmation
**Steps:**
1. Attempt deletion without confirm=true
2. Verify rejection

**Expected Results:**
- HTTP 400 Bad Request
- Error: "Deletion must be explicitly confirmed"
- No data deleted

### Test Case: DD-003 - Post-Deletion Access
**Steps:**
1. Delete account
2. Attempt to use same credentials
3. Verify access denied

**Expected Results:**
- Authentication fails
- No user data retrievable
- Must create new account

---

## 4. Crashlytics Toggle Testing

### Test Case: CR-001 - Enable Crashlytics
**Endpoints:** `POST /api/v1/settings/crashlytics`
**Steps:**
1. Open Settings
2. Find "Crash Reporting" (default: OFF)
3. Toggle ON
4. Verify confirmation dialog
5. Confirm enabling

**Request:**
```json
{
  "enabled": true,
  "user_id": "123",
  "device_id": "device_abc",
  "app_version": "1.0.0"
}
```

**Expected Results:**
- Crashlytics enabled
- Privacy notice displayed
- Setting persisted

### Test Case: CR-002 - Disable Crashlytics
**Steps:**
1. From enabled state
2. Toggle OFF
3. Verify immediate effect

**Expected Results:**
- Crashlytics disabled
- No more crash reports sent
- Setting persisted

### Test Case: CR-003 - Default State Verification
**Steps:**
1. Fresh install app
2. Check Crashlytics setting
3. Verify default OFF

**Expected Results:**
- Crashlytics OFF by default
- Requires explicit opt-in
- Privacy-first approach confirmed

### Test Case: CR-004 - Crash with Crashlytics OFF
**Steps:**
1. Ensure Crashlytics OFF
2. Trigger test crash
3. Verify no data sent

**Expected Results:**
- App recovers gracefully
- No crash data transmitted
- Local logging only

---

## 5. Offline & Retry Testing

### Test Case: OR-001 - Offline Authentication
**Steps:**
1. Sign in successfully
2. Enable airplane mode
3. Use app features
4. Verify cached token usage

**Expected Results:**
- Cached auth works offline
- API calls queued
- Sync on reconnection

### Test Case: OR-002 - Retry Failed Requests
**Endpoints:** `GET /api/v1/settings/retry-policy`
**Steps:**
1. Simulate network failure
2. Make API request
3. Verify retry attempts
4. Restore network
5. Verify success

**Expected Retry Policy:**
```json
{
  "max_retries": 3,
  "initial_delay_ms": 1000,
  "backoff_multiplier": 2,
  "retry_on_status_codes": [408, 429, 500, 502, 503, 504]
}
```

### Test Case: OR-003 - Queue Management
**Steps:**
1. Go offline
2. Perform 10 actions
3. Go online
4. Verify queue processing

**Expected Results:**
- All actions queued
- Processed in order
- User notified of sync

---

## 6. Error Handling & UI

### Test Case: EH-001 - Network Error Banner
**Steps:**
1. Disconnect network
2. Attempt search
3. Verify error banner

**Expected Results:**
- Clear error message
- Retry button visible
- Non-blocking UI

### Test Case: EH-002 - Auth Expiration
**Steps:**
1. Expire token manually
2. Attempt protected action
3. Verify re-auth flow

**Expected Results:**
- Automatic refresh attempt
- If fails, prompt re-login
- Preserve user context

### Test Case: EH-003 - Rate Limiting
**Steps:**
1. Exceed rate limit (5 exports/hour)
2. Verify error message
3. Check retry after header

**Expected Results:**
- HTTP 429 Too Many Requests
- Clear wait time shown
- Graceful degradation

---

## 7. Privacy & Security Testing

### Test Case: PS-001 - No Email Storage
**Steps:**
1. Sign in with OAuth
2. Check database
3. Verify no email stored

**Expected Results:**
- Only provider_id hash stored
- No PII in database
- Privacy preserved

### Test Case: PS-002 - Token Security
**Steps:**
1. Intercept JWT token
2. Verify signature
3. Check expiration
4. Attempt replay attack

**Expected Results:**
- Valid signature required
- Token expires properly
- Replay prevented

### Test Case: PS-003 - Secure Logout
**Steps:**
1. Sign in
2. Tap logout
3. Attempt API call with old token
4. Verify rejection

**Expected Results:**
- Token invalidated
- HTTP 401 on reuse
- Complete session cleanup

---

## 8. Performance Testing

### Test Case: PT-001 - Sign-In Speed
**Metrics:**
- Time to complete OAuth: < 3 seconds
- Token generation: < 100ms
- UI response: < 50ms

### Test Case: PT-002 - Data Export Performance
**Metrics:**
- Small data (< 1MB): < 2 seconds
- Medium data (1-10MB): < 5 seconds
- Large data (> 10MB): < 10 seconds

### Test Case: PT-003 - Settings Sync
**Metrics:**
- Setting change: < 500ms
- Cross-device sync: < 2 seconds
- Offline queue: < 100ms

---

## 9. Platform-Specific Testing

### 9.1 iOS Specific

#### Test Case: iOS-001 - Face ID Integration
**Steps:**
1. Enable biometric auth
2. Sign out
3. Sign in with Face ID
4. Verify success

#### Test Case: iOS-002 - App Store Privacy Labels
**Steps:**
1. Verify privacy labels accurate
2. Confirm no email collection
3. Check crash data disclosure

### 9.2 Android Specific

#### Test Case: AND-001 - Google Play Services
**Steps:**
1. Test on device without Play Services
2. Verify graceful degradation
3. Alternative auth options

#### Test Case: AND-002 - Biometric API
**Steps:**
1. Enable fingerprint auth
2. Test authentication
3. Verify secure storage

---

## 10. Acceptance Criteria

### ✅ Authentication
- [ ] Apple Sign-In works on iOS
- [ ] Google Sign-In works on both platforms
- [ ] No email stored in database
- [ ] Tokens refresh automatically
- [ ] Logout clears all data

### ✅ DSAR Compliance
- [ ] Export completes < 5 seconds
- [ ] Deletion is permanent
- [ ] Confirmation required
- [ ] Email verification works
- [ ] Status tracking functional

### ✅ Crashlytics
- [ ] Default OFF
- [ ] Toggle persists
- [ ] No data when disabled
- [ ] Privacy notice shown
- [ ] Settings sync across devices

### ✅ Error Handling
- [ ] Offline mode works
- [ ] Retry logic functions
- [ ] Clear error messages
- [ ] No data loss
- [ ] Graceful recovery

### ✅ Privacy
- [ ] No PII stored
- [ ] Secure token handling
- [ ] Proper data deletion
- [ ] Audit logging works
- [ ] Compliance documented

### ✅ Performance
- [ ] Sign-in < 3 seconds
- [ ] Export < 5 seconds
- [ ] Settings sync < 2 seconds
- [ ] No memory leaks
- [ ] Battery efficient

---

## Test Execution Summary

| Category | Test Cases | Pass | Fail | Skip |
|----------|------------|------|------|------|
| OAuth Auth | 8 | | | |
| Data Export | 3 | | | |
| Data Deletion | 3 | | | |
| Crashlytics | 4 | | | |
| Offline/Retry | 3 | | | |
| Error Handling | 3 | | | |
| Privacy | 3 | | | |
| Performance | 3 | | | |
| Platform | 4 | | | |
| **TOTAL** | **34** | | | |

---

## Sign-Off

- [ ] QA Lead: ___________________ Date: ___________
- [ ] Dev Lead: ___________________ Date: ___________
- [ ] Product Owner: _______________ Date: ___________
- [ ] Privacy Officer: _____________ Date: ___________

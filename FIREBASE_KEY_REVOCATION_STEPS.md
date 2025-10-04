# Firebase Key Revocation - Step-by-Step Guide

**🚨 CRITICAL ACTION - DO THIS NOW**

---

## 🎯 YOUR MISSION

Delete the exposed Firebase service account key to prevent unauthorized access.

---

## 📋 STEP-BY-STEP INSTRUCTIONS

### Step 1: You should now see Google Cloud Console

The page should show: **Service Accounts** for project `babyshield-8f552`

If you're not logged in:
- Sign in with your Google account that has access to BabyShield

---

### Step 2: Find the Service Account

Look for this service account in the list:

```
firebase-adminsdk-fbsvc@babyshield-8f552.iam.gserviceaccount.com
```

**It will look like:**
```
Name: firebase-adminsdk-fbsvc
Email: firebase-adminsdk-fbsvc@babyshield-8f552.iam.gserviceaccount.com
```

---

### Step 3: Click on the Service Account

Click anywhere on that row to open the service account details.

---

### Step 4: Go to the "KEYS" Tab

At the top of the page, you'll see tabs:
- DETAILS
- PERMISSIONS
- **KEYS** ← Click this one

---

### Step 5: Find the Exposed Key

In the Keys section, look for a key with ID starting with:

```
f9d6fbee209506ae0c7d96f3c93ce233048013f6
```

**Key details:**
- Type: JSON
- Created: (some date in the past)
- Key ID: f9d6fbee209506ae...

---

### Step 6: Delete the Key

1. Click the **three dots** (⋮) on the right side of that key row
2. Select **"Delete"**
3. A confirmation dialog will appear
4. **Type "DELETE" in the confirmation box** (if prompted)
5. Click **"Delete"** to confirm

---

### Step 7: Verify Deletion

After deletion:
- ✅ The key should disappear from the list
- ✅ You should see a success message
- ✅ The key is now revoked and cannot be used

---

## ❌ WHAT IF YOU CAN'T FIND THE KEY?

### Scenario A: Key ID not found
- **Good news!** It may have already been revoked
- Check if there are any other keys listed
- If there are other keys, they might be different (safer) keys

### Scenario B: No access to project
- You need to be:
  - Project Owner
  - Project Editor
  - Service Account Admin
- Contact your organization admin for access

### Scenario C: Service account not found
- Double-check the project ID: `babyshield-8f552`
- Use the project selector at the top of the page
- Make sure you're in the correct GCP organization

---

## ✅ AFTER DELETION

Once you've deleted the key, you MUST create a new one:

### Create New Service Account Key

**Option A: Create new key for same service account (if still needed)**

1. While on the KEYS tab
2. Click **"ADD KEY"** button
3. Select **"Create new key"**
4. Choose **JSON** format
5. Click **"Create"**
6. The key will download automatically
7. **Store it securely** - NOT in git!
8. Update your production environment:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="/path/to/new-key.json"
   ```

**Option B: Create entirely new service account (recommended)**

1. Go back to Service Accounts list
2. Click **"+ CREATE SERVICE ACCOUNT"**
3. Name: `babyshield-backend-prod-new`
4. Description: "Production backend (post-security-incident-2025)"
5. Click **"CREATE AND CONTINUE"**
6. Grant minimum permissions:
   - Firebase Authentication Admin (if needed)
   - Cloud Datastore User
   - Storage Object Viewer/Admin (as needed)
7. Click **"DONE"**
8. Click on new service account → KEYS tab
9. ADD KEY → Create new key → JSON
10. Download and store securely

---

## 🔐 SECURITY BEST PRACTICES

### Storage
- ✅ Store in secure location (e.g., AWS Secrets Manager, Azure Key Vault)
- ✅ Use environment variables in production
- ❌ NEVER commit to git
- ❌ NEVER share via email/Slack/etc.

### Permissions
- ✅ Use minimum required permissions (Principle of Least Privilege)
- ✅ Create separate accounts for dev/staging/prod
- ❌ Don't use Owner or Editor roles
- ❌ Don't reuse keys across environments

### Rotation
- ✅ Rotate keys every 90 days
- ✅ Document key creation dates
- ✅ Set calendar reminders
- ✅ Test new keys before revoking old ones

---

## 📊 VERIFICATION CHECKLIST

After completing these steps:

- [ ] Old key deleted from Google Cloud Console
- [ ] Success message received
- [ ] New service account created (or new key for existing)
- [ ] New key downloaded and stored securely
- [ ] Production environment updated with new key
- [ ] Firebase connectivity tested
- [ ] All services working with new key
- [ ] Old key location documented
- [ ] Incident documented in security log

---

## 🚨 IF YOU ENCOUNTER ERRORS

### Error: "Insufficient permissions"
**Solution:** You need Service Account Admin role. Contact your GCP admin.

### Error: "Key not found"
**Solution:** Key may already be deleted. Check audit logs to confirm.

### Error: "Cannot delete last key"
**Solution:** Create a new key first, then delete the old one.

### Service breaks after deletion
**Solution:** 
1. Verify new key is correctly configured
2. Check environment variables
3. Restart services
4. Check logs for authentication errors

---

## 📞 NEED HELP?

### Google Cloud Support
- Console: https://console.cloud.google.com/support
- Documentation: https://cloud.google.com/iam/docs/service-accounts

### Emergency Contact
If you believe the key has been compromised:
1. Delete the key immediately (follow steps above)
2. Review Firebase access logs
3. Contact Google Cloud Support
4. Document the incident
5. Assess breach notification requirements

---

## ✅ COMPLETION

Once you've completed all steps:

1. **Document in security log:**
   ```
   Date: [Today's date]
   Action: Revoked exposed Firebase service account key
   Key ID: f9d6fbee209506ae0c7d96f3c93ce233048013f6
   New key created: [Yes/No]
   Production updated: [Yes/No]
   Verified working: [Yes/No]
   ```

2. **Notify team:**
   - Security team
   - DevOps team  
   - Compliance team
   - Management (if required)

3. **Update documentation:**
   - Mark incident as resolved
   - Document lessons learned
   - Update security procedures

---

## 🎯 QUICK REFERENCE

**URL to open:**
```
https://console.cloud.google.com/iam-admin/serviceaccounts?project=babyshield-8f552
```

**PowerShell command to open:**
```powershell
Start-Process "https://console.cloud.google.com/iam-admin/serviceaccounts?project=babyshield-8f552"
```

**Service Account:**
```
firebase-adminsdk-fbsvc@babyshield-8f552.iam.gserviceaccount.com
```

**Key ID to delete:**
```
f9d6fbee209506ae0c7d96f3c93ce233048013f6
```

---

**Priority:** 🔴 **CRITICAL**  
**Time Sensitivity:** Complete within 1 hour  
**Status:** ⏳ In Progress

---

Good luck! Follow the steps carefully and you'll have this resolved in minutes! 💪


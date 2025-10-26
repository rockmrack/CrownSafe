# Manual Steps to Complete Router Registration Removal

## Issue
File encoding in `api/main_babyshield.py` has corrupted checkmark characters that prevent automated string replacement. Lines 1269-1276 were partially commented (first 5 lines) but logging/except lines remain active.

## Required Manual Edits in api/main_babyshield.py

Use VS Code's Find & Replace (Ctrl+H) with "Use Regular Expression" enabled.

### 1. Complete Recall Alert System Block (Lines 1273-1277)
**Find (regex):**
```
    #     app\.include_router\(recall_alert_router\)\n    logging\.info\(".*?Recall Alert System registered"\)\nexcept Exception as e:\n    logging\.error\(f"Failed to register recall alert system: \{e\}"\)
```

**Replace with:**
```
#     app.include_router(recall_alert_router)
#     logging.info("Recall Alert System registered")
# except Exception as e:
#     logging.error(f"Failed to register recall alert system: {e}")
```

### 2. Comment Out Recall Search System Block (Lines ~1278-1284)
**Find:**
```
# Include Recall Search System
try:
    from api.recalls_endpoints import router as recalls_router

    app.include_router(recalls_router)
    logging.info(".*?Recall Search System registered")
except Exception as e:
    logging.error(f"Failed to register recall search system: {e}")
```

**Replace with:**
```
# REMOVED FOR CROWN SAFE: Recall Search System is BabyShield-specific (baby product recalls)
# # Include Recall Search System
# try:
#     from api.recalls_endpoints import router as recalls_router
#
#     app.include_router(recalls_router)
#     logging.info("Recall Search System registered")
# except Exception as e:
#     logging.error(f"Failed to register recall search system: {e}")
```

### 3. Comment Out Recall Detail Endpoints Block (Line ~1537)
**Find:**
```
# Include recall detail endpoints
try:
    from api.recall_detail_endpoints import router as recall_detail_router

    app.include_router(recall_detail_router)
    logging.info(".*?Recall detail endpoints registered")
except Exception as e:
    logging.error(f"Failed to register recall detail endpoints: {e}")
```

**Replace with:**
```
# REMOVED FOR CROWN SAFE: Recall Detail endpoints are BabyShield-specific (baby product recalls)
# # Include recall detail endpoints
# try:
#     from api.recall_detail_endpoints import router as recall_detail_router
#
#     app.include_router(recall_detail_router)
#     logging.info("Recall detail endpoints registered")
# except Exception as e:
#     logging.error(f"Failed to register recall detail endpoints: {e}")
```

### 4. Comment Out Premium Features Block (Line ~1643)
**Find:**
```
# Include Premium Features (Pregnancy & Allergy) endpoints - LEGACY BABY CODE
try:
    from api.premium_features_endpoints import router as premium_router

    app.include_router(premium_router)
    logging.info("Premium Features endpoints registered")
except ImportError as e:
    logging.warning(f"Premium features (baby allergy checking) not available: {e}")
```

**Replace with:**
```
# REMOVED FOR CROWN SAFE: Premium Features are BabyShield-specific (pregnancy & baby allergy checking)
# # Include Premium Features (Pregnancy & Allergy) endpoints - LEGACY BABY CODE
# try:
#     from api.premium_features_endpoints import router as premium_router
#
#     app.include_router(premium_router)
#     logging.info("Premium Features endpoints registered")
# except ImportError as e:
#     logging.warning(f"Premium features (baby allergy checking) not available: {e}")
```

### 5. Comment Out Baby Safety Features Block (Line ~1653)
**Find:**
```
# Include Baby Safety Features (Alternatives, Notifications, Reports) endpoints
try:
    from api.baby_features_endpoints import router as baby_router

    app.include_router(baby_router)
    logging.info(".*?Baby Safety Features.*?registered")
except (ImportError, FileNotFoundError) as e:
    logging.warning(f"Baby Safety Features not available (missing dependency pylibdmtx): {e}")
    # Continue without baby features - they're optional
```

**Replace with:**
```
# REMOVED FOR CROWN SAFE: Baby Safety Features are BabyShield-specific (family members, pregnancy tracking)
# # Include Baby Safety Features (Alternatives, Notifications, Reports) endpoints
# try:
#     from api.baby_features_endpoints import router as baby_router
#
#     app.include_router(baby_router)
#     logging.info("Baby Safety Features endpoints registered")
# except (ImportError, FileNotFoundError) as e:
#     logging.warning(f"Baby Safety Features not available (missing dependency pylibdmtx): {e}")
#     # Continue without baby features - they're optional
```

## Verification

After making these changes, run:
```powershell
python -c "from api.main_babyshield import app; print('✅ Imports work')"
```

If successful, you should see no import errors and the message "✅ Imports work".

## Alternative: Line-by-Line Manual Edit

If regex replacement doesn't work, manually navigate to each line number and:
1. Add the "# REMOVED FOR CROWN SAFE" comment line above the block
2. Add "# " prefix to the comment line (e.g., "# # Include Recall Alert System")
3. Add "# " prefix to every line in the try/except block

## Next Steps After Completion

Once all 5 router registrations are commented out:
1. Verify server can import without errors
2. Move to Task 3: Gut RecallDB dead code in 6 functions
3. Run database migration (Task 9)
4. Test server startup (Task 10)

## Estimated Time
15 minutes for manual editing + verification

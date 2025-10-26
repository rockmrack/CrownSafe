# Crown Safe Code Cleanup Instructions
# =======================================

## Files to Delete (Once Unlocked)

### API Endpoints (5 files)
- api/recall_detail_endpoints.py
- api/recall_alert_system.py
- api/recalls_endpoints.py
- api/baby_features_endpoints.py
- api/premium_features_endpoints.py

### Scripts (7+ files)
- scripts/ingest_recalls.py
- scripts/seed_recall_db.py
- scripts/test_recall_connectors.py
- scripts/test_recall_data_agent.py
- scripts/test_recall_connectors_live.py
- scripts/test_live_recall_scenario.py
- scripts/test_baby_features_api.py

### Root Scripts
- verify_production_recalls.py
- test_recall_connectors_quick.py
- test_recall_agent_simple.py
- test_recall_agent_full.py
- find_recalls.py
- check_recalls.py
- check_uk_recalls_azure.py

### Workers
- workers/recall_tasks.py

### Database Models
- core_infra/enhanced_database_schema.py
- db/data_models/recall.py

### Documentation
- BABY_CODE_REMOVAL_PLAN.md

## Code to Comment Out in api/main_babyshield.py

### Lines 1269-1287 (Recall Alert & Search Systems)
```python
# ===== LEGACY BABY RECALL CODE - DISABLED FOR CROWN SAFE =====
# Include Recall Alert System
# try:
#     from api.recall_alert_system import recall_alert_router
#     app.include_router(recall_alert_router)
#     logging.info("✓ Recall Alert System registered")
# except Exception as e:
#     logging.error(f"Failed to register recall alert system: {e}")

# Include Recall Search System
# try:
#     from api.recalls_endpoints import router as recalls_router
#     app.include_router(recalls_router)
#     logging.info("✓ Recall Search System registered")
# except Exception as e:
#     logging.error(f"Failed to register recall search system: {e}")
# ===== END LEGACY BABY RECALL CODE =====
```

### Lines 1533-1541 (Recall Detail Endpoints)
```python
# ===== LEGACY BABY RECALL CODE - DISABLED FOR CROWN SAFE =====
# Include recall detail endpoints
# try:
#     from api.recall_detail_endpoints import router as recall_detail_router
#     app.include_router(recall_detail_router)
#     logging.info("✓ Recall detail endpoints registered")
# except Exception as e:
#     logging.error(f"Failed to register recall detail endpoints: {e}")
# ===== END LEGACY BABY RECALL CODE =====
```

### Lines 1639-1660 (Premium & Baby Features)
```python
# ===== LEGACY BABY CODE - DISABLED FOR CROWN SAFE =====
# Include Premium Features (Pregnancy & Allergy) endpoints
# try:
#     from api.premium_features_endpoints import router as premium_router
#     app.include_router(premium_router)
#     logging.info("Premium Features endpoints registered")
# except ImportError as e:
#     logging.warning(f"Premium features (baby allergy checking) not available: {e}")

# Include Baby Safety Features
# try:
#     from api.baby_features_endpoints import router as baby_router
#     app.include_router(baby_router)
#     logging.info("✓ Baby Safety Features endpoints registered")
# except (ImportError, FileNotFoundError) as e:
#     logging.warning(f"Baby Safety Features not available: {e}")
# ===== END LEGACY BABY CODE =====
```

## Code to Remove from core_infra/database.py

### Lines 113-148 (RecallDB Models)
- Remove LegacyRecallDB class
- Remove EnhancedRecallDB class

### Lines 177-220 (Family/Allergy Models - Already Commented)
- Delete the commented-out FamilyMember and Allergy classes entirely

### Lines 477-521 (Helper Functions - Already Commented)
- Delete the commented-out family/allergy helper functions entirely

## Next Steps After File Deletion

1. Close files in VS Code editor
2. Run: `Remove-Item api\recall*.py, api\baby*.py, api\premium*.py -Force`
3. Run: `Remove-Item scripts\*recall*.py, scripts\*baby*.py -Force`
4. Run: `Remove-Item workers\recall*.py -Force`
5. Clean core_infra/database.py (remove RecallDB models)
6. Run: `cd db ; python -m alembic upgrade head`
7. Run: `python scripts\seed_crown_safe_data.py`
8. Test: `python -m uvicorn api.main_babyshield:app --reload --port 8001`
9. Visit: http://localhost:8001/docs to verify Crown Safe endpoints only

## STATUS: IN PROGRESS
- Files locked by VS Code - cannot delete yet
- Need to manually close files or restart VS Code
- Then proceed with file deletion and code cleanup

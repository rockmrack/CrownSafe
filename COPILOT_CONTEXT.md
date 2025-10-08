# Quick Context for GitHub Copilot

**📋 USE THIS TO BRIEF COPILOT ON CURRENT STATE:**

---

## 🎯 Current Status (Oct 8, 2025)

**Production:** ✅ WORKING with PostgreSQL  
**Git Commits:** `d662085` (fixes) + `091f7e5` (docs)  
**Branches:** `main` and `development` - both updated

---

## ⚠️ CRITICAL: What Changed

### **Configuration System Completely Rewritten**

**OLD (DELETED):**
- ❌ `config/settings/__init__.py`
- ❌ `config/settings/base.py`
- ❌ `config/settings/development.py`
- ❌ `config/settings/production.py`

**NEW:**
- ✅ `config/settings.py` - Single unified config with Pydantic v2

**Import Changes:**
```python
# ❌ OLD - DO NOT USE:
from config.settings.base import Settings

# ✅ NEW - USE THIS:
from config.settings import get_config, Settings
config = get_config()
```

---

## 📝 For Fixing CI Tests

### **1. Database Configuration**

Tests MUST use PostgreSQL (not SQLite):

```yaml
# In .github/workflows/*.yml
env:
  DATABASE_URL: "postgresql://postgres:postgres@localhost:5432/postgres"
  # OR provide individual components:
  DB_USERNAME: "postgres"
  DB_PASSWORD: "postgres"
  DB_HOST: "localhost"
  DB_PORT: "5432"
  DB_NAME: "postgres"
```

### **2. New Endpoints to Test**

```
GET /              → 200 {"status": "ok", "service": "babyshield-backend"}
GET /api/v1/version → 200 {"service": "babyshield-backend", "version": "2.4.0"}
```

### **3. Database Schema Changes**

`recalls_enhanced` table now has:
- `severity` column (String(50), nullable=True)
- `risk_category` column (String(100), nullable=True)

### **4. Pydantic v2 Compatibility**

```python
# Use this import pattern:
try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings
```

---

## 🔧 Common Test Failures & Fixes

### **ImportError: cannot import Settings**

**Fix:** Update import:
```python
from config.settings import get_config
config = get_config()
```

### **SQLite errors in tests**

**Fix:** Set `DATABASE_URL` in test environment:
```python
os.environ["DATABASE_URL"] = "postgresql://localhost/test"
```

### **404 on `/` or `/api/v1/version`**

**Fix:** These endpoints now exist. Update expected status to 200.

### **Missing `severity` column**

**Fix:** Run Alembic migrations before tests:
```bash
alembic upgrade head
```

---

## 📖 Full Details

See `POSTGRESQL_MIGRATION_SUMMARY.md` for complete documentation.

---

## 🎯 When You Talk to Copilot

**Copy/paste this:**

> @copilot I need help fixing CI tests. Please read `POSTGRESQL_MIGRATION_SUMMARY.md` and `COPILOT_CONTEXT.md` first.
> 
> Key context:
> - We migrated from SQLite to PostgreSQL (commits d662085, 091f7e5)
> - `config/settings/` directory was DELETED, replaced with `config/settings.py`
> - New endpoints: `/` and `/api/v1/version`
> - New database columns: `severity`, `risk_category`
> - Tests MUST use PostgreSQL, not SQLite
> 
> Please help fix [SPECIFIC TEST NAME] based on these changes.

---

**Last Updated:** Oct 8, 2025, 15:30 UTC  
**Production Status:** ✅ HEALTHY (Task 159, PostgreSQL connected)


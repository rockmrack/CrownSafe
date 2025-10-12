# Alembic Migration Quick Start

## ✅ FIXED: Now Working!

**Latest Updates (October 12, 2025)**:
- ✅ Fixed `script_location` in `db/alembic.ini` to use `db/migrations` (relative to project root)
- ✅ Fixed `core_infra/database.py` to not pass `None` values for pool settings to SQLite
- ✅ Fixed pg_trgm migration to skip PostgreSQL-specific commands on SQLite
- ✅ Fixed migration chain: pg_trgm now depends on `bcef138c88a2` head

**Confirmed Working Commands**:
```powershell
cd C:\code\babyshield-backend
$env:DATABASE_URL="sqlite:///./babyshield_dev.db"
alembic -c db/alembic.ini upgrade head  # ✅ WORKS!
```

---

## Running Alembic Commands

**IMPORTANT**: Always run Alembic commands from the **project root directory** (where `core_infra/`, `api/`, `db/` folders are located), not from inside the `db/` folder.

### Correct Usage

```powershell
# Navigate to project root
cd C:\code\babyshield-backend

# OR from any subdirectory:
cd C:\Users\rossd\Downloads\RossNetAgents\babyshield-backend-clean

# Set DATABASE_URL (REQUIRED)
$env:DATABASE_URL="postgresql+psycopg://user:password@host:5432/babyshield"

# Run Alembic migrations
alembic -c db/alembic.ini upgrade head
```

### Common Commands

```powershell
# 1. Check current migration version
alembic -c db/alembic.ini current

# 2. Upgrade to latest migration
alembic -c db/alembic.ini upgrade head

# 3. Downgrade one migration
alembic -c db/alembic.ini downgrade -1

# 4. Show migration history
alembic -c db/alembic.ini history

# 5. Create a new migration (auto-detect changes)
alembic -c db/alembic.ini revision --autogenerate -m "description"

# 6. Create empty migration (manual)
alembic -c db/alembic.ini revision -m "description"
```

### Troubleshooting

#### Error: "Path doesn't exist: '...\migrations'"

**Cause**: You're running Alembic from the wrong directory.

**Solution**: Navigate to the project root directory first:
```powershell
cd C:\Users\rossd\Downloads\RossNetAgents\babyshield-backend-clean
alembic -c db/alembic.ini upgrade head
```

#### Error: "FAILED: Can't locate revision identified by 'head'"

**Cause**: Alembic can't find migration files.

**Solution**: 
1. Check that `db/migrations/versions/` folder exists and contains `.py` files
2. Ensure you're in the project root directory
3. Verify `db/alembic.ini` has `script_location = migrations` (relative path)

#### Error: "sqlalchemy.url is not set"

**Cause**: DATABASE_URL environment variable not set.

**Solution**:
```powershell
# For PostgreSQL (production/staging)
$env:DATABASE_URL="postgresql+psycopg://user:password@host:5432/babyshield"

# For SQLite (local development only)
$env:DATABASE_URL="sqlite:///./babyshield_dev.db"
```

#### Error: "could not connect to server"

**Cause**: PostgreSQL server not running or credentials incorrect.

**Solution**:
1. Verify PostgreSQL is running: `pg_isready`
2. Test connection: `psql "$env:DATABASE_URL"`
3. Check credentials in DATABASE_URL
4. Verify network connectivity to database host

### Directory Structure

Your project should look like this:
```
babyshield-backend-clean/          ← Run Alembic from here!
├── api/
├── core_infra/
├── db/
│   ├── alembic.ini                ← Config file
│   ├── migrations/                ← Migrations folder
│   │   ├── env.py
│   │   └── versions/              ← Migration files
│   │       ├── 2025_10_12_*.py
│   │       └── ...
│   └── ...
├── tests/
├── alembic.ini (symlink optional)
└── ...
```

### Setting Up for the First Time

If this is a **new database** (never had migrations run):

```powershell
# 1. Navigate to project root
cd C:\Users\rossd\Downloads\RossNetAgents\babyshield-backend-clean

# 2. Set DATABASE_URL
$env:DATABASE_URL="postgresql+psycopg://user:password@host:5432/babyshield"

# 3. Test database connection
python verify_postgres_migration.py

# 4. Run ALL migrations to create tables
alembic -c db/alembic.ini upgrade head

# 5. Verify tables were created
python verify_postgres_migration.py
```

### Creating New Migrations

```powershell
# 1. Make changes to your SQLAlchemy models
# Edit files in core_infra/ or db/models/

# 2. Generate migration automatically
cd C:\Users\rossd\Downloads\RossNetAgents\babyshield-backend-clean
alembic -c db/alembic.ini revision --autogenerate -m "add new column to users"

# 3. Review the generated migration file
# Check db/migrations/versions/YYYY_MM_DD_HHMM_*_add_new_column_to_users.py

# 4. Test migration
alembic -c db/alembic.ini upgrade head

# 5. If something goes wrong, rollback
alembic -c db/alembic.ini downgrade -1
```

### PostgreSQL Migration Workflow

```powershell
# Full workflow for PostgreSQL migration

# Step 1: Set DATABASE_URL
$env:DATABASE_URL="postgresql+psycopg://babyshield_user:password@localhost:5432/babyshield"

# Step 2: Navigate to project root
cd C:\Users\rossd\Downloads\RossNetAgents\babyshield-backend-clean

# Step 3: Verify connection
python verify_postgres_migration.py

# Step 4: Run migrations
alembic -c db/alembic.ini upgrade head

# Expected output:
# INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
# INFO  [alembic.runtime.migration] Will assume transactional DDL.
# INFO  [alembic.runtime.migration] Running upgrade -> 2025_10_12_create_pg_trgm_extension
# INFO  [alembic.runtime.migration] Running upgrade 2025_10_12_create_pg_trgm_extension -> head

# Step 5: Verify pg_trgm extension was created
python -c "from sqlalchemy import create_engine, text; import os; engine = create_engine(os.getenv('DATABASE_URL')); conn = engine.connect(); result = conn.execute(text('SELECT extname FROM pg_extension WHERE extname=\'pg_trgm\'')); print('pg_trgm installed:', bool(list(result)))"

# Step 6: Start application
python core/startup.py
```

### Quick Reference Card

| Command                                                      | What it does                   |
| ------------------------------------------------------------ | ------------------------------ |
| `alembic -c db/alembic.ini current`                          | Show current migration version |
| `alembic -c db/alembic.ini upgrade head`                     | Run all pending migrations     |
| `alembic -c db/alembic.ini downgrade -1`                     | Undo last migration            |
| `alembic -c db/alembic.ini history`                          | Show all migrations            |
| `alembic -c db/alembic.ini revision --autogenerate -m "msg"` | Create new migration           |

### Environment Variables

| Variable            | Required | Example                                       |
| ------------------- | -------- | --------------------------------------------- |
| `DATABASE_URL`      | ✅ Yes    | `postgresql+psycopg://user:pass@host:5432/db` |
| `TEST_DATABASE_URL` | ❌ No     | `sqlite:///:memory:` (tests only)             |
| `TEST_MODE`         | ❌ No     | `true` or `false`                             |

### Need Help?

See full documentation:
- `POSTGRESQL_MIGRATION_COMPLETE.md` - Complete migration guide
- `verify_postgres_migration.py` - Automated verification script
- `db/migrations/README.md` - Alembic-specific documentation

---

**Last Updated**: October 12, 2025  
**Maintainer**: BabyShield Development Team

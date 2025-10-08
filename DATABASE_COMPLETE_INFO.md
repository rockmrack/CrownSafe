# BabyShield Database - Complete Information

**Last Updated:** October 8, 2025  
**Status:** ✅ Production Active (PostgreSQL)

---

## 📊 Production Database Instance

### **AWS RDS PostgreSQL Configuration**

| Property | Value |
|----------|-------|
| **Engine** | PostgreSQL 17.4 |
| **Endpoint** | `babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com` |
| **Port** | `5432` |
| **Database Name** | `postgres` (default database) |
| **Master Username** | `babyshield_user` |
| **Master Password** | `MandarunLabadiena25!` |
| **Instance Class** | `db.t3.large` |
| **Allocated Storage** | 20 GB |
| **Availability Zone** | `eu-north-1a` (Europe - Stockholm) |
| **Status** | Available |
| **Region** | `eu-north-1` |

### **Connection String**
```
postgresql://babyshield_user:MandarunLabadiena25!@babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com:5432/postgres
```

---

## 🗂️ Database Schema

### **Core Tables**

#### **1. `recalls_enhanced` (Primary Recall Table)**

**Purpose:** Comprehensive recall storage supporting 39 international agencies with complete product identification.

**Primary Identifiers:**
- `id` (Integer, Primary Key)
- `recall_id` (String, Unique, Indexed)

**Product Identifiers:**
- `product_name` (String, Indexed, Required)
- `brand` (String, Indexed)
- `manufacturer` (String)
- `model_number` (String, Indexed)

**Retail Identifiers (Global Barcodes):**
- `upc` (String, Indexed) - US/Canada Universal Product Code
- `ean_code` (String, Indexed) - European Article Number
- `gtin` (String, Indexed) - Global Trade Item Number
- `article_number` (String, Indexed) - Style/Article codes

**Batch/Lot Identifiers (Food/Pharma Critical):**
- `lot_number` (String, Indexed) - For food agencies
- `batch_number` (String, Indexed) - For pharmaceuticals
- `serial_number` (String, Indexed) - Electronics/devices
- `part_number` (String, Indexed) - Vehicle parts/components

**Date Identifiers:**
- `recall_date` (Date, Indexed, Required)
- `expiry_date` (Date, Indexed) - Food/drugs
- `best_before_date` (Date, Indexed) - Food products
- `production_date` (Date, Indexed) - Manufacturing date

**Pharmaceutical Identifiers:**
- `ndc_number` (String, Indexed) - US National Drug Code
- `din_number` (String, Indexed) - Canada Drug Identification Number

**Vehicle Identifiers:**
- `vehicle_make` (String, Indexed) - Car manufacturer
- `vehicle_model` (String, Indexed) - Car model
- `model_year` (String, Indexed) - Manufacturing year
- `vin_range` (String) - VIN number ranges

**Geographic/Distribution:**
- `country` (String)
- `regions_affected` (JSON) - Distribution regions
- `source_agency` (String, Indexed)

**Recall Metadata:**
- `hazard` (Text) - Hazard description
- `hazard_category` (String, Indexed) - Structured hazard type
- `severity` (String(50)) - Severity level (low, medium, high, critical) **🆕**
- `risk_category` (String(100)) - Risk category (general, food, vehicle, etc.) **🆕**
- `recall_reason` (Text)
- `remedy` (Text)
- `recall_class` (String) - Class I/II/III for FDA
- `description` (Text)
- `url` (String)

**Search Optimization:**
- `search_keywords` (Text) - Pre-computed search terms
- `registry_codes` (JSON) - Regional registry numbers
- `agency_specific_data` (JSON) - Raw agency data for fallback

**Supported Agencies (39 Total):**
- **US:** CPSC, FDA, NHTSA, USDA FSIS
- **Canada:** Health Canada, CFIA, Transport Canada
- **Europe:** EU RAPEX, UK OPSS, UK FSA
- **Latin America:** ANMAT (Argentina), ANVISA (Brazil), SENACON (Brazil)
- **And 26 more...**

---

#### **2. `recalls` (Legacy Table)**

**Purpose:** Backward compatibility for older integrations.

**Schema:** Simplified version of `recalls_enhanced` without advanced identifiers.

**Key Fields:**
- `id`, `recall_id`, `product_name`, `brand`, `country`
- `recall_date`, `hazard_description`, `manufacturer_contact`
- `upc`, `source_agency`, `description`, `hazard`, `remedy`, `url`

---

#### **3. `users`**

**Purpose:** User account management with subscription tracking.

**Schema:**
```sql
CREATE TABLE users (
    id                 INTEGER PRIMARY KEY,
    email              VARCHAR UNIQUE NOT NULL,
    stripe_customer_id VARCHAR UNIQUE,
    hashed_password    VARCHAR NOT NULL DEFAULT '',
    is_subscribed      BOOLEAN NOT NULL DEFAULT FALSE,  -- Single subscription status
    is_pregnant        BOOLEAN NOT NULL DEFAULT FALSE,
    is_active          BOOLEAN NOT NULL DEFAULT TRUE    -- Account status
);
```

**Relationships:**
- One-to-Many with `family_members`

---

#### **4. `family_members`**

**Purpose:** Store family profiles for multi-user household management.

**Schema:**
```sql
CREATE TABLE family_members (
    id      INTEGER PRIMARY KEY,
    name    VARCHAR NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id)
);
```

**Relationships:**
- Many-to-One with `users`
- One-to-Many with `allergies`

---

#### **5. `allergies`**

**Purpose:** Track allergies for each family member.

**Schema:**
```sql
CREATE TABLE allergies (
    id        INTEGER PRIMARY KEY,
    allergen  VARCHAR NOT NULL,
    member_id INTEGER NOT NULL REFERENCES family_members(id)
);
```

**Relationships:**
- Many-to-One with `family_members`

---

#### **6. `safety_articles`**

**Purpose:** Educational safety articles and campaigns from trusted agencies.

**Schema:**
```sql
CREATE TABLE safety_articles (
    id               INTEGER PRIMARY KEY,
    article_id       VARCHAR UNIQUE NOT NULL,
    title            VARCHAR NOT NULL,
    summary          TEXT NOT NULL,
    source_agency    VARCHAR NOT NULL,
    publication_date DATE NOT NULL,
    image_url        VARCHAR,
    article_url      VARCHAR NOT NULL,
    is_featured      BOOLEAN DEFAULT FALSE
);
```

---

### **Additional Tables (Imported Models)**

The following tables are created from imported models:

- **Chat & Conversation:**
  - `user_profiles` - User profile data for chat context
  - `conversations` - Chat conversation history
  - `conversation_messages` - Individual messages

- **Monitoring:**
  - `monitored_products` - Products being actively monitored
  - `monitoring_runs` - Execution logs for monitoring jobs

- **Privacy & Compliance:**
  - `privacy_requests` - GDPR/CCPA data requests
  - `scan_history` - User product scan history
  - `ingestion_runs` - Data ingestion tracking

- **Risk Assessment:**
  - Risk assessment models (if available)

---

## 🔍 Database Indexes

### **PostgreSQL pg_trgm Extension**

**Status:** ✅ Enabled  
**Purpose:** Fuzzy text search and similarity matching

**Extension Installation:**
```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

---

### **GIN Indexes (Trigram Search)**

Optimized for fuzzy text search using `pg_trgm`:

```sql
-- Product name (primary search field)
CREATE INDEX ix_recalls_enhanced_product_name_trgm 
ON recalls_enhanced USING gin (lower(product_name) gin_trgm_ops);

-- Brand (commonly searched)
CREATE INDEX ix_recalls_enhanced_brand_trgm 
ON recalls_enhanced USING gin (lower(brand) gin_trgm_ops);

-- Description (comprehensive search)
CREATE INDEX ix_recalls_enhanced_description_trgm 
ON recalls_enhanced USING gin (lower(description) gin_trgm_ops);

-- Hazard (safety searches)
CREATE INDEX ix_recalls_enhanced_hazard_trgm 
ON recalls_enhanced USING gin (lower(hazard) gin_trgm_ops);
```

---

### **BTREE Indexes (Filtering & Sorting)**

```sql
-- Agency filter
CREATE INDEX ix_recalls_enhanced_agency 
ON recalls_enhanced (source_agency);

-- Date sorting (DESC for most recent first)
CREATE INDEX ix_recalls_enhanced_recalldate 
ON recalls_enhanced (recall_date DESC);

-- Composite index for common query pattern
CREATE INDEX ix_recalls_enhanced_agency_date 
ON recalls_enhanced (source_agency, recall_date DESC);

-- Risk/severity filters
CREATE INDEX ix_recalls_enhanced_severity 
ON recalls_enhanced (severity);

CREATE INDEX ix_recalls_enhanced_riskcategory 
ON recalls_enhanced (risk_category);

-- Barcode lookups
CREATE INDEX ix_recalls_enhanced_upc 
ON recalls_enhanced (upc) WHERE upc IS NOT NULL;

-- Model number lookups
CREATE INDEX ix_recalls_enhanced_model_number 
ON recalls_enhanced (model_number) WHERE model_number IS NOT NULL;
```

---

## 📝 Alembic Migrations

### **Migration History**

**Location:** `db/alembic/versions/`

**Key Migrations:**

1. **`fix_missing_columns.py`** (Revision: `fix_missing_columns`)
   - **Purpose:** Add `severity` and `risk_category` columns to `recalls_enhanced`
   - **Changes:**
     - `severity` VARCHAR(50)
     - `risk_category` VARCHAR(100)
   - **Defaults:** `severity='medium'`, `risk_category='general'`

2. **`20250826_search_trgm_indexes.py`** (Revision: `20250826_search_trgm`)
   - **Purpose:** Enable `pg_trgm` extension and create comprehensive search indexes
   - **Changes:**
     - Enable `pg_trgm` extension
     - Create GIN trigram indexes for fuzzy search
     - Create BTREE indexes for filtering and sorting
     - Run `ANALYZE` for query optimization
   - **Compatibility:** Checks for both `recalls_enhanced` and `recalls` tables

3. **Other Migrations:**
   - `20250105_monitoring_notifications.py` - Monitoring and notifications
   - `20250108_scan_history_safety_reports.py` - User scan tracking
   - `20250109_incident_reports.py` - Incident reporting
   - `20250109_safety_articles.py` - Safety article storage
   - `20250827_privacy_requests.py` - Privacy compliance
   - `20250924_chat_memory.py` - Chat conversation tracking
   - `add_subscription_tables.py` - Subscription management
   - `add_oauth_fields.py` - OAuth integration

**Running Migrations:**
```bash
# Upgrade to latest
alembic upgrade head

# Check current version
alembic current

# View migration history
alembic history --verbose
```

---

## 🔧 Configuration Management

### **Environment Variables (Production)**

**Current ECS Task Definition (Revision 159):**

```json
{
  "DB_USERNAME": "babyshield_user",
  "DB_PASSWORD": "MandarunLabadiena25!",
  "DB_HOST": "babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com",
  "DB_PORT": "5432",
  "DB_NAME": "postgres",
  "ENVIRONMENT": "production",
  "IS_PRODUCTION": "true",
  "ENABLE_AGENTS": "true"
}
```

**How `DATABASE_URL` is Constructed:**

1. **Pydantic Settings (`config/settings.py`):**
   ```python
   # Automatically constructs DATABASE_URL from DB_* components
   database_url = f"postgresql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
   ```

2. **Production Validation:**
   ```python
   # Enforces PostgreSQL in production (rejects SQLite)
   if is_production and 'sqlite' in database_url.lower():
       raise ValueError("Production requires PostgreSQL, not SQLite")
   ```

3. **Startup Integration (`api/main_babyshield.py`):**
   ```python
   from config.settings import get_config, validate_production_config
   config = get_config()
   validate_production_config()  # Validates PostgreSQL requirement
   
   # Sets DATABASE_URL in environment for core_infra/database.py
   os.environ["DATABASE_URL"] = config.database_url
   ```

---

## 🚀 Database Operations

### **Connection Management**

**SQLAlchemy Engine:**
```python
# Production (PostgreSQL)
engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=int(os.getenv("DB_POOL_SIZE", 10)),
    max_overflow=int(os.getenv("DB_MAX_OVERFLOW", 20)),
    pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", 30)),
    future=True
)
```

**Session Management:**
```python
# Context manager for safe database operations
from core_infra.database import get_db_session

with get_db_session() as db:
    # Perform database operations
    users = db.query(User).all()
    # Automatically commits and closes
```

**FastAPI Dependency:**
```python
from core_infra.database import get_db
from fastapi import Depends

@app.get("/users")
def get_users(db: Session = Depends(get_db)):
    return db.query(User).all()
```

---

### **Table Creation**

**Method 1: Alembic Migrations (Recommended)**
```bash
alembic upgrade head
```

**Method 2: Programmatic (Development)**
```python
from core_infra.database import create_tables
create_tables()  # Creates all tables from Base.metadata
```

**What `create_tables()` Does:**
1. Creates tables from `Base` class (User, FamilyMember, Allergy)
2. Creates tables from `EnhancedBase` class (recalls_enhanced)
3. Imports and registers additional models (chat, monitoring, privacy)
4. Runs `Base.metadata.create_all(bind=engine)`

---

### **Database Verification Queries**

**Check Tables Exist:**
```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_name IN ('recalls_enhanced', 'users', 'family_members', 'allergies');
```

**Verify Columns:**
```sql
-- Check severity column exists
SELECT column_name, data_type, is_nullable
FROM information_schema.columns 
WHERE table_name = 'recalls_enhanced' 
  AND column_name IN ('severity', 'risk_category');
```

**Verify Extensions:**
```sql
-- Check pg_trgm extension
SELECT * FROM pg_extension WHERE extname = 'pg_trgm';
```

**Check Indexes:**
```sql
-- List all indexes on recalls_enhanced
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'recalls_enhanced';
```

**Check Record Count:**
```sql
SELECT 
    (SELECT COUNT(*) FROM recalls_enhanced) AS recalls_count,
    (SELECT COUNT(*) FROM users) AS users_count,
    (SELECT COUNT(*) FROM family_members) AS family_members_count;
```

---

## 🔒 Security & Access

### **Master Credentials**

**⚠️ CRITICAL:** These credentials are currently stored in **plain environment variables** in the ECS task definition.

**Recommendation:** Migrate to AWS Secrets Manager for enhanced security.

---

### **AWS Secrets Manager (Recommended)**

**Secret Name:** `babyshield/prod/database`  
**Region:** `eu-north-1`

**Secret Structure (JSON):**
```json
{
  "username": "babyshield_user",
  "password": "MandarunLabadiena25!",
  "host": "babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com",
  "port": "5432",
  "dbname": "postgres"
}
```

**ECS Task Definition with Secrets Manager:**
```json
{
  "secrets": [
    {
      "name": "DB_USERNAME",
      "valueFrom": "arn:aws:secretsmanager:eu-north-1:180703226577:secret:babyshield/prod/database:username::"
    },
    {
      "name": "DB_PASSWORD",
      "valueFrom": "arn:aws:secretsmanager:eu-north-1:180703226577:secret:babyshield/prod/database:password::"
    }
  ]
}
```

---

### **IAM Roles**

**Execution Role:** `arn:aws:iam::180703226577:role/ecsTaskExecutionRole`  
**Task Role:** `arn:aws:iam::180703226577:role/babyshield-task-role`

**Required Permissions:**
- `secretsmanager:GetSecretValue` (if using Secrets Manager)
- `rds:DescribeDBInstances` (read-only)
- `logs:CreateLogStream`, `logs:PutLogEvents` (CloudWatch)

---

### **Network Security**

**RDS Security Group:**
- Must allow inbound connections on port `5432` from ECS task security group
- Should restrict access to only application subnets
- **NO public accessibility** (private subnet only)

**VPC Configuration:**
- RDS and ECS tasks should be in the same VPC
- Use private subnets for database access
- NAT Gateway for ECS tasks to reach internet (ECR, CloudWatch)

---

## 📊 Monitoring & Maintenance

### **Health Checks**

**Database Connectivity Check:**
```python
# In api/main_babyshield.py
from core_infra.database import engine

def check_database_health():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "healthy"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

**API Health Endpoint:**
```bash
curl https://babyshield-backend-alb-1130876534.eu-north-1.elb.amazonaws.com/readyz
```

---

### **CloudWatch Metrics**

**Key Metrics to Monitor:**
- RDS CPU Utilization
- RDS Database Connections
- RDS Free Storage Space
- RDS Read/Write IOPS
- RDS Read/Write Latency

**Alarms:**
- CPU > 80% for 5 minutes
- Free Storage < 2 GB
- Database Connections > 80% of max

---

### **Regular Maintenance**

**Weekly Tasks:**
```sql
-- Analyze tables for query optimization
ANALYZE recalls_enhanced;
ANALYZE users;

-- Vacuum to reclaim space
VACUUM ANALYZE recalls_enhanced;
```

**Monthly Tasks:**
- Review and rotate database credentials
- Check for unused indexes
- Review slow query logs
- Update PostgreSQL minor version if available

---

## 🐛 Troubleshooting

### **Common Issues**

#### **1. Connection Refused**

**Symptoms:**
```
psycopg2.OperationalError: could not connect to server
```

**Checks:**
- Is RDS instance running? (`Status: available`)
- Are security groups configured correctly?
- Is ECS task in correct VPC/subnet?
- Is `DB_HOST` correct in environment variables?

---

#### **2. Password Authentication Failed**

**Symptoms:**
```
FATAL: password authentication failed for user "babyshield"
```

**Checks:**
- Is `DB_USERNAME` correct? (Should be `babyshield_user`, not `babyshield`)
- Is `DB_PASSWORD` correct? (Check Secrets Manager or task definition)
- Has password been changed in RDS console?

**Fix:**
```bash
aws rds describe-db-instances \
  --db-instance-identifier babyshield-prod-db \
  --query 'DBInstances[0].MasterUsername'
```

---

#### **3. Database Does Not Exist**

**Symptoms:**
```
FATAL: database "babyshield_prod" does not exist
```

**Checks:**
- What is `DB_NAME` set to? (Currently: `postgres`)
- Does the target database exist in RDS?

**Fix:**
```sql
-- Connect to default database
psql -h babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com \
     -U babyshield_user -d postgres

-- Create production database
CREATE DATABASE babyshield_prod;
GRANT ALL PRIVILEGES ON DATABASE babyshield_prod TO babyshield_user;
```

---

#### **4. Missing Columns (severity, risk_category)**

**Symptoms:**
```
sqlite3.OperationalError: no such column: recalls_enhanced.severity
```

**Cause:** Alembic migrations not run or using SQLite instead of PostgreSQL.

**Fix:**
```bash
# Verify database type
echo $DATABASE_URL  # Should start with postgresql://

# Run migrations
alembic upgrade head

# Verify columns exist
psql -h $DB_HOST -U $DB_USERNAME -d $DB_NAME \
  -c "SELECT column_name FROM information_schema.columns WHERE table_name='recalls_enhanced' AND column_name IN ('severity', 'risk_category');"
```

---

#### **5. pg_trgm Extension Missing**

**Symptoms:**
```
ERROR: type "gin_trgm_ops" does not exist
```

**Fix:**
```sql
-- Connect as superuser or master user
psql -h babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com \
     -U babyshield_user -d postgres

-- Enable extension
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Verify
SELECT * FROM pg_extension WHERE extname = 'pg_trgm';
```

---

## 📚 References

### **Documentation Files**

- `POSTGRESQL_MIGRATION_SUMMARY.md` - Complete migration details
- `DEPLOYMENT_RUNBOOK.md` - Deployment procedures
- `DOCKER_BUILD_AND_DEPLOY_GUIDE.md` - Docker & ECS deployment
- `COPILOT_CONTEXT.md` - Quick reference for AI assistants

### **Code Files**

- `config/settings.py` - Configuration management with PostgreSQL validation
- `core_infra/database.py` - SQLAlchemy engine and session management
- `core_infra/enhanced_database_schema.py` - Complete schema for 39 agencies
- `api/main_babyshield.py` - Application startup with database initialization
- `db/alembic/versions/` - All database migrations

### **AWS Resources**

- **Account ID:** `180703226577`
- **Region:** `eu-north-1`
- **RDS Instance:** `babyshield-prod-db`
- **ECS Cluster:** `babyshield-cluster`
- **ECS Service:** `babyshield-backend-task-service-0l41s2a9`
- **ECR Repository:** `180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend`

---

## ✅ Current Status Summary

| Component | Status | Notes |
|-----------|--------|-------|
| **RDS Instance** | ✅ Available | PostgreSQL 17.4, db.t3.large |
| **Database** | ✅ Connected | Using `postgres` database |
| **Schema** | ✅ Current | `recalls_enhanced` with `severity` and `risk_category` |
| **Extensions** | ✅ Enabled | `pg_trgm` for fuzzy search |
| **Indexes** | ✅ Created | GIN (trigram) + BTREE (filtering) |
| **Migrations** | ✅ Applied | All migrations up to date |
| **Production App** | ✅ Running | ECS Task 159, HEALTHY |
| **SQLite Errors** | ✅ ZERO | No more SQLite issues |
| **Search API** | ✅ Working | `/api/v1/search/advanced` returns 200 |

---

**Last Verified:** October 8, 2025  
**Verified By:** Cursor AI + Human Collaboration  
**Production Image:** `180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:production-fixed-20251008-final3`


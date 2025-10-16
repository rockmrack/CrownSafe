# ================================================
# BABYSHIELD AWS DEPLOYMENT GUIDE - COMPLETE REFERENCE
# ================================================
# LAST UPDATED: October 16, 2025
# STATUS: ✅ PRODUCTION OPERATIONAL - Search fully working with 33,964+ records

# SYSTEM DETAILS
# --------------
# AWS Account: 180703226577
# Region: eu-north-1
# ECS Cluster: babyshield-cluster
# ECS Service: babyshield-backend-task-service-0l41s2a9
# Task Definition Family: babyshield-backend-task
# ECR Repository: 180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend
# Current Working Task: :186+ (updated Oct 16, 2025)
# Latest Docker Image: main-20251016-1533-88a7d36

# DATABASE
# ---------
# RDS PostgreSQL: babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com
# RDS IP Address: 51.20.20.233 (DO NOT USE - use hostname for SSL)
# Database Name: babyshield_db (CORRECT - contains all data)
# Wrong Database: postgres (empty, 0 records - DO NOT USE)
# Username: babyshield_user
# Password: MandarunLabadiena25!
# Total Recalls: 131,743+ records in babyshield_db
# Search Results: 33,964+ records returned
# pg_trgm Extension: ✅ Enabled (v1.6) with 4 GIN indexes
# GIN Indexes: idx_recalls_product_trgm, idx_recalls_brand_trgm, idx_recalls_description_trgm, idx_recalls_hazard_trgm

# VPC CONFIGURATION
# -----------------
# VPC ID: vpc-00ec1a4f2e0523413
# DNS Resolution: ✅ Enabled
# DNS Hostnames: ✅ Enabled
# Security Group: sg-0e2aed27cbf2213ed (allows VPC-only access)
# IMPORTANT: Always use RDS hostname, NOT IP address (SSL certificate validation requires hostname)

# REDIS CACHE
# -----------
# ElastiCache Endpoint: babyshield-redis.h4xvut.0001.eun1.cache.amazonaws.com:6379

# LOAD BALANCER
# -------------
# Target Group ARN: arn:aws:elasticloadbalancing:eu-north-1:180703226577:targetgroup/babyshield-backend-tg/7cdeb9f904292be1
# API URL: https://babyshield.cureviax.ai
# Health Check: /healthz

# ================================================
# CRITICAL ENVIRONMENT VARIABLES
# ================================================
# REQUIRED for task definition - ALL must be set correctly:

DATABASE_URL=postgresql://babyshield_user:MandarunLabadiena25!@babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com:5432/babyshield_db

# Individual DB components (used by config/settings.py to construct DATABASE_URL):
DB_HOST=babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com
DB_NAME=babyshield_db  # CRITICAL: Must be "babyshield_db" NOT "postgres"
DB_USERNAME=babyshield_user
DB_PASSWORD=MandarunLabadiena25!
DB_PORT=5432

# Other required env vars:
API_HOST=0.0.0.0
API_PORT=8001
ENVIRONMENT=production
IS_PRODUCTION=true
ENABLE_AGENTS=true
BS_FEATURE_CHAT_ENABLED=true
BS_FEATURE_CHAT_ROLLOUT_PCT=1.0
OPENAI_API_KEY=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

# ================================================
# DEPLOYMENT COMMANDS (RUN IN ORDER)
# ================================================

# 0. SET VARIABLES (from project root: c:\code\babyshield-backend)
$TAG = "main-$(Get-Date -Format 'yyyyMMdd-HHmm')-$(git rev-parse --short HEAD)"
$ECR_REPO = "180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend"

# 1. BUILD DOCKER IMAGE LOCALLY
docker build --platform linux/amd64 -f Dockerfile.final -t $ECR_REPO:$TAG -t $ECR_REPO:latest .

# 2. LOGIN TO ECR
aws ecr get-login-password --region eu-north-1 | docker login --username AWS --password-stdin 180703226577.dkr.ecr.eu-north-1.amazonaws.com

# 3. PUSH TO ECR
docker push $ECR_REPO:$TAG
docker push $ECR_REPO:latest

# 4. CREATE NEW TASK DEFINITION IN AWS CONSOLE
#    Go to: ECS → Task Definitions → babyshield-backend-task → Create new revision
#    - Update image: 180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:$TAG
#    - Verify ALL environment variables are correct (especially DB_NAME=babyshield_db)
#    - CRITICAL: Click "Create" button at bottom to SAVE (don't just view!)

# 5. UPDATE ECS SERVICE WITH NEW REVISION
#    Go to: ECS → Clusters → babyshield-cluster → Services → babyshield-backend-task-service-0l41s2a9
#    - Click "Update"
#    - Select latest task definition revision
#    - Click "Update" button
#    - Wait 2-3 minutes for deployment

# 6. VERIFY DEPLOYMENT
curl.exe -X GET "https://babyshield.cureviax.ai/healthz"
# Should return: {"status":"ok"}

# 7. TEST SEARCH FUNCTIONALITY
curl.exe -X POST "https://babyshield.cureviax.ai/api/v1/search/advanced" -H "Content-Type: application/json" -d '{\"query\":\"baby\",\"limit\":5}'
# Should return: {"ok":true,"data":{"items":[...],"total":33964,...}}

# ================================================
# TROUBLESHOOTING COMMANDS
# ================================================

# Check current task definition in use
aws ecs describe-services --cluster babyshield-cluster --services babyshield-backend-task-service-0l41s2a9 --region eu-north-1 --query 'services[0].taskDefinition'

# Check service events for errors
aws ecs describe-services --cluster babyshield-cluster --services babyshield-backend-task-service-0l41s2a9 --region eu-north-1 --query 'services[0].events[0:5].[createdAt,message]' --output table

# Check CloudWatch logs
aws logs tail /ecs/babyshield-backend --since 10m --region eu-north-1

# Check if task is running
aws ecs describe-services --cluster babyshield-cluster --services babyshield-backend-task-service-0l41s2a9 --region eu-north-1 --query 'services[0].deployments[*].{Status:status,TaskDef:taskDefinition,Running:runningCount}' --output table

# Force new deployment (restarts tasks)
aws ecs update-service --cluster babyshield-cluster --service babyshield-backend-task-service-0l41s2a9 --force-new-deployment --region eu-north-1

# Test database connection directly (requires CloudShell with security group access)
psql -h babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com -U babyshield_user -d babyshield_db -c "SELECT COUNT(*) FROM recalls;"

# ================================================
# COMMON ISSUES AND SOLUTIONS
# ================================================

## Issue 1: Search returns 0 results
**Cause:** DB_NAME set to "postgres" instead of "babyshield_db"
**Solution:** 
1. Edit task definition
2. Change DB_NAME to "babyshield_db"
3. Click "Create" to save (CRITICAL - must actually save!)
4. Update service with new revision

## Issue 2: "could not translate host name" error
**Cause:** Using IP address instead of hostname
**Solution:**
1. Change DB_HOST back to: babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com
2. Change DATABASE_URL to use hostname (not IP)
3. Reason: RDS requires hostname for SSL certificate validation

## Issue 3: Task fails health checks after deployment
**Cause:** Invalid environment variables or database connection issues
**Solution:**
1. Check CloudWatch logs for specific error
2. Verify all environment variables are correct
3. Ensure DATABASE_URL and DB_* variables match
4. Revert to last working task definition if needed

## Issue 4: pg_trgm warnings in logs
**Cause:** PostgreSQL pg_trgm extension not enabled
**Solution:** Already fixed - pg_trgm v1.6 is enabled with GIN indexes

## Issue 5: AWS Console changes not taking effect
**Cause:** Forgot to click "Create" button after editing task definition
**Solution:** Always click "Create" at bottom of page to save changes!

# ================================================
# DATABASE MAINTENANCE
# ================================================

# Check pg_trgm extension status
psql -h babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com -U babyshield_user -d babyshield_db -c "SELECT * FROM pg_extension WHERE extname = 'pg_trgm';"

# Check GIN indexes
psql -h babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com -U babyshield_user -d babyshield_db -c "SELECT indexname, tablename FROM pg_indexes WHERE indexname LIKE '%trgm%';"

# Count records in each database
psql -h babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com -U babyshield_user -d postgres -c "SELECT COUNT(*) FROM recalls;"  # Returns 0
psql -h babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com -U babyshield_user -d babyshield_db -c "SELECT COUNT(*) FROM recalls;"  # Returns 131,743+

# ================================================
# IMPORTANT NOTES
# ================================================
# - Dockerfile.final must have: CMD ["uvicorn", "api.main_babyshield:app", "--host", "0.0.0.0", "--port", "8001"]
# - Always use task-service-0l41s2a9 (NOT bv5v69zq - that was deleted)
# - Database has severity and risk_category columns (added manually)
# - Redis is required for auth, rate limiting, and visual processing
# - ECS auto-rollback is enabled (failures roll back to last working version)
# - config/settings.py constructs DATABASE_URL from DB_* env vars (overrides DATABASE_URL if all DB_* are present)
# - ALWAYS use hostname, NEVER use IP address for RDS connection (SSL certificate validation)
# - VPC DNS resolution and hostnames are both enabled (vpc-00ec1a4f2e0523413)
# - Two databases exist on same RDS instance: "postgres" (empty) and "babyshield_db" (production data)
# - Search functionality requires pg_trgm extension with GIN indexes (already enabled)
# - Latest working image: main-20251016-1533-88a7d36
# - Latest working task definition: :186+ (October 16, 2025)

# ================================================
# VERIFICATION CHECKLIST
# ================================================
# After every deployment, verify:
# ✅ Health check: curl https://babyshield.cureviax.ai/healthz returns {"status":"ok"}
# ✅ Search works: curl POST /api/v1/search/advanced returns results (not empty)
# ✅ Total count: Search response shows total > 30,000
# ✅ Task running: ECS service shows 1/1 tasks running
# ✅ No errors: CloudWatch logs show no database connection errors
# ✅ DB_NAME: Task definition has DB_NAME=babyshield_db (NOT postgres)
# ✅ DB_HOST: Task definition uses hostname (NOT IP address)

# ================================================
# CONTACT
# ================================================
# For issues or questions, check:
# - CloudWatch Logs: /ecs/babyshield-backend
# - ECS Console: https://eu-north-1.console.aws.amazon.com/ecs/v2/clusters/babyshield-cluster
# - Session Reports: See SESSION_REPORT_SEARCH_FIX.md for complete troubleshooting history

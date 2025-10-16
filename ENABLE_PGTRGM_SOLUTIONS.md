# How to Enable pg_trgm on Production Database

**Status**: Production search is broken (returns 0 results). Need to enable pg_trgm extension.

**Problem**: CloudShell cannot connect directly to RDS (security group blocks access).

---

## ✅ RECOMMENDED SOLUTION: Python Script in CloudShell

This is the **simplest and safest** approach.

### Step 1: Upload the script to CloudShell

```bash
# In CloudShell, create the script
cat > enable_pg_trgm_emergency.py << 'EOF'
[Copy the entire content of scripts/enable_pg_trgm_emergency.py here]
EOF

chmod +x enable_pg_trgm_emergency.py
```

### Step 2: Run the script

```bash
python3 enable_pg_trgm_emergency.py
```

**Expected Output (if security group allows)**:
```
✓ Connected successfully!
✓ Extension enabled
✓ pg_trgm version 1.6 is installed
✓ similarity('baby', 'baby') = 1.0
✓ Created index: product_trgm
✓ Created index: brand_trgm
✓ Created index: description_trgm
✓ Created index: hazard_trgm

✓ SUCCESS - pg_trgm is now enabled!
```

**Expected Output (if security group blocks)**:
```
❌ Connection failed: could not connect to server...
This means CloudShell cannot reach the RDS database.
```

---

## 🔧 ALTERNATIVE 1: Modify Security Group Temporarily

If the Python script fails due to security group, do this:

### Step 1: Get your CloudShell IP

```bash
MY_IP=$(curl -s https://checkip.amazonaws.com)
echo "My CloudShell IP: $MY_IP"
```

### Step 2: Add IP to RDS Security Group

**Via AWS Console**:
1. Go to RDS → Databases → babyshield-prod-db
2. Click on the VPC security group
3. Edit inbound rules
4. Add rule: Type=PostgreSQL, Port=5432, Source=$MY_IP/32
5. Save

**Via AWS CLI**:
```bash
# Find security group ID
SG_ID=$(aws rds describe-db-instances \
  --db-instance-identifier babyshield-prod-db \
  --region eu-north-1 \
  --query 'DBInstances[0].VpcSecurityGroups[0].VpcSecurityGroupId' \
  --output text)

echo "Security Group: $SG_ID"

# Add your IP
MY_IP=$(curl -s https://checkip.amazonaws.com)

aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 5432 \
  --cidr $MY_IP/32 \
  --region eu-north-1

echo "✓ Added $MY_IP to security group"
```

### Step 3: Run the Python script

```bash
python3 enable_pg_trgm_emergency.py
```

### Step 4: REMOVE your IP (IMPORTANT!)

```bash
# Remove the IP for security
aws ec2 revoke-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 5432 \
  --cidr $MY_IP/32 \
  --region eu-north-1

echo "✓ Removed $MY_IP from security group"
```

---

## 🔧 ALTERNATIVE 2: Use Admin API via Curl

This requires an admin user (which may not exist yet).

### Step 1: Login and get token

```bash
# Set your credentials
EMAIL="your-admin-email@example.com"
PASSWORD="your-password"

# Get JWT token
TOKEN=$(curl -s -X POST https://babyshield.cureviax.ai/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" \
  | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
  echo "❌ Login failed - check credentials or user may not be admin"
  exit 1
fi

echo "✓ Got token: ${TOKEN:0:20}..."
```

### Step 2: Call admin endpoint

```bash
curl -X POST https://babyshield.cureviax.ai/api/v1/admin/database/enable-pg-trgm \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  | jq .
```

**Expected Success**:
```json
{
  "ok": true,
  "data": {
    "extension_status": "enabled",
    "extension_version": "1.6",
    "similarity_test": 1.0,
    "indexes_created": 4,
    "existing_indexes": [...]
  }
}
```

**Expected Error**:
```json
{
  "detail": "Admin access required"
}
```

This means the user is not an admin. You'll need to grant admin privileges first.

---

## 🔧 ALTERNATIVE 3: Create Admin User First

If you don't have an admin user, create one:

### Option A: Via Master DB User (if you have credentials)

```bash
# Connect as master user
PGPASSWORD='MASTER_PASSWORD' psql \
  -h babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com \
  -U postgres \
  -d postgres \
  -c "UPDATE users SET is_admin = true WHERE email = 'your-email@example.com';"
```

### Option B: Via Application Database

```bash
# Connect as application user
PGPASSWORD='MandarunLabadiena25!' psql \
  -h babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com \
  -U babyshield_user \
  -d postgres \
  -c "UPDATE users SET is_admin = true WHERE email = 'your-email@example.com';"
```

Then use Alternative 2 above.

---

## 🔧 ALTERNATIVE 4: ECS Exec (Most Complex)

Run the script from within the ECS container (which has VPC access).

### Step 1: Enable ECS Exec on the service

```bash
aws ecs update-service \
  --cluster babyshield-cluster \
  --service babyshield-backend-task-service-0l41s2a9 \
  --enable-execute-command \
  --region eu-north-1
```

### Step 2: Find running task

```bash
TASK_ARN=$(aws ecs list-tasks \
  --cluster babyshield-cluster \
  --service-name babyshield-backend-task-service-0l41s2a9 \
  --region eu-north-1 \
  --query 'taskArns[0]' \
  --output text)

echo "Task: $TASK_ARN"
```

### Step 3: Execute command in container

```bash
# Run the Python script
aws ecs execute-command \
  --cluster babyshield-cluster \
  --task $TASK_ARN \
  --container babyshield-backend \
  --command "python3 -c \"
import psycopg2
import os
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
conn.autocommit = True
cursor = conn.cursor()
cursor.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm;')
print('✓ pg_trgm enabled')
cursor.close()
conn.close()
\"" \
  --interactive \
  --region eu-north-1
```

---

## 📋 Verification

After enabling pg_trgm, test search:

```bash
# Test search endpoint
curl -X POST https://babyshield.cureviax.ai/api/v1/search/advanced \
  -H "Content-Type: application/json" \
  -d '{"query":"baby","limit":5}' \
  | jq .

# Expected: "total" > 0 (should be around 12,000+)
```

Check CloudWatch logs:
```bash
aws logs tail /ecs/babyshield-backend-task-definition \
  --follow \
  --region eu-north-1 \
  --filter-pattern "pg_trgm"
```

The warning about pg_trgm should disappear.

---

## 🎯 Recommendation

**Try solutions in this order**:

1. **Python Script** (enable_pg_trgm_emergency.py) - Simplest, try first
2. **If fails**: Temporarily add CloudShell IP to security group, run script, remove IP
3. **If no admin user**: Create admin user via database UPDATE, then use Admin API
4. **Last resort**: Use ECS exec (requires IAM permissions and task definition changes)

---

## 🔍 Troubleshooting

### Error: "could not connect to server"
- Security group is blocking CloudShell
- Use Alternative 1 to add your IP temporarily

### Error: "Admin access required"
- User is not admin
- Use Alternative 3 to grant admin privileges

### Error: "permission denied to create extension"
- User lacks permissions
- Need RDS master user or user with rds_superuser role

### Error: "extension 'pg_trgm' already exists"
- Good! Extension is already enabled
- Run verification step to confirm search works

---

**Last Updated**: 2025-10-16  
**Status**: Production search broken, pg_trgm not enabled  
**Priority**: CRITICAL - Search completely non-functional

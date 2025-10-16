# BabyShield AWS Deployment Runbook

## 📋 System Overview

### AWS Infrastructure
- **Account ID**: 180703226577
- **Region**: eu-north-1 (Stockholm)
- **ECS Cluster**: `babyshield-cluster`
- **ECS Service**: `babyshield-backend-task-service-0l41s2a9`
- **Task Definition Family**: `babyshield-backend-task`
- **Current Working Task**: `:183` (deployed Oct 16, 2025)
- **ECR Repository**: `180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend`
- **API URL**: https://babyshield.cureviax.ai

### Database (RDS PostgreSQL)
- **Endpoint**: `babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com`
- **Port**: 5432
- **Database**: `babyshield_db`
- **Username**: `babyshield_user`
- **Password**: `<REDACTED - stored in AWS Secrets Manager>`
- **Total Recalls**: 137,000+ records
- **Custom Columns**: `severity`, `risk_category` (added manually)

### Redis Cache (ElastiCache)
- **Endpoint**: `babyshield-redis.h4xvut.0001.eun1.cache.amazonaws.com:6379`
- **Used For**: Auth tokens, rate limiting, visual processing cache

### Load Balancer
- **Target Group ARN**: `arn:aws:elasticloadbalancing:eu-north-1:180703226577:targetgroup/babyshield-backend-tg/7cdeb9f904292be1`
- **Health Check**: `/healthz`

### IAM Roles
- **Task Role**: `arn:aws:iam::180703226577:role/babyshield-task-role`
- **Execution Role**: `arn:aws:iam::180703226577:role/ecsTaskExecutionRole`

---

## 🚀 Complete Deployment Process

### Prerequisites
- Docker Desktop running
- AWS CLI configured with credentials
- Git repository up to date on `main` branch
- Working directory: `C:\code\babyshield-backend`

---

### Step 1: Prepare the Code

```powershell
# Ensure you're on main branch
git checkout main
git pull origin main

# Verify latest commit
git log -1 --oneline
```

---

### Step 2: Build Docker Image

```powershell
# Get current commit hash for tagging
$commitHash = (git rev-parse --short HEAD)
$dateTag = Get-Date -Format "yyyyMMdd-HHmm"
$imageTag = "main-$dateTag-$commitHash"

# Build production image
docker build --platform linux/amd64 --no-cache -f Dockerfile.final -t babyshield-backend:$imageTag .

# Verify image was created
docker images babyshield-backend:$imageTag
```

**Expected Output**: Image size ~500-800MB, built successfully

---

### Step 3: Login to ECR

```powershell
aws ecr get-login-password --region eu-north-1 | docker login --username AWS --password-stdin 180703226577.dkr.ecr.eu-north-1.amazonaws.com
```

**Expected Output**: `Login Succeeded`

---

### Step 4: Tag and Push to ECR

```powershell
# Tag for ECR
docker tag babyshield-backend:$imageTag 180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:$imageTag

# Also tag as latest
docker tag babyshield-backend:$imageTag 180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:latest

# Push versioned tag
docker push 180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:$imageTag

# Push latest tag
docker push 180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:latest

# Display the image tag for next steps
Write-Host "`n✅ Image pushed successfully!" -ForegroundColor Green
Write-Host "Image Tag: $imageTag" -ForegroundColor Cyan
```

**Expected Output**: Multiple layer pushes, digest confirmation

---

### Step 5: Register New Task Definition

```powershell
# Store the image tag for the task definition
$imageUri = "180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:$imageTag"

# Create task definition JSON
$taskDefJson = @"
{
  "family": "babyshield-backend-task",
  "taskRoleArn": "arn:aws:iam::180703226577:role/babyshield-task-role",
  "executionRoleArn": "arn:aws:iam::180703226577:role/ecsTaskExecutionRole",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "containerDefinitions": [
    {
      "name": "babyshield-backend",
      "image": "$imageUri",
      "essential": true,
      "portMappings": [
        {
          "containerPort": 8001,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "DATABASE_URL",
          "value": "postgresql://babyshield_user:${DB_PASSWORD}@babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com:5432/babyshield_db"
          // NOTE: Inject the production database password securely at deployment time using environment variables or AWS Secrets Manager. Do NOT store plaintext passwords in documentation or version control.
        },
        {
          "name": "REDIS_URL",
          "value": "redis://babyshield-redis.h4xvut.0001.eun1.cache.amazonaws.com:6379/0"
        },
        {
          "name": "RATE_LIMIT_REDIS_URL",
          "value": "redis://babyshield-redis.h4xvut.0001.eun1.cache.amazonaws.com:6379/0"
        },
        {
          "name": "JWT_SECRET_KEY",
          "value": "{{RESOLVE:secretsmanager:jwt_secret_key:SecretString:JWT_SECRET_KEY}}"
          // NOTE: Do NOT store the JWT secret key in plaintext. Use AWS Secrets Manager or SSM Parameter Store.
          // Replace the above value with the appropriate reference for your secret management solution.
        },
        {
          "name": "JWT_ALGORITHM",
          "value": "HS256"
        },
        {
          "name": "ENVIRONMENT",
          "value": "production"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/babyshield-backend",
          "awslogs-region": "eu-north-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8001/healthz || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
"@

# Save to temp file
$taskDefJson | Out-File -FilePath "task-definition-temp.json" -Encoding UTF8

# Register the task definition
$taskDefArn = aws ecs register-task-definition `
  --cli-input-json file://task-definition-temp.json `
  --region eu-north-1 `
  --query 'taskDefinition.taskDefinitionArn' `
  --output text

# Clean up temp file
Remove-Item "task-definition-temp.json"

# Display the new task definition
Write-Host "`n✅ Task Definition registered!" -ForegroundColor Green
Write-Host "Task Definition ARN: $taskDefArn" -ForegroundColor Cyan

# Extract revision number
$revision = ($taskDefArn -split ':')[-1]
Write-Host "Revision: $revision" -ForegroundColor Cyan
```

**Expected Output**: Task definition ARN with new revision number

---

### Step 6: Update ECS Service

```powershell
# Update the service with new task definition
aws ecs update-service `
  --cluster babyshield-cluster `
  --service babyshield-backend-task-service-0l41s2a9 `
  --task-definition babyshield-backend-task:$revision `
  --force-new-deployment `
  --region eu-north-1 `
  --query 'service.{ServiceName:serviceName,Status:status,DesiredCount:desiredCount,RunningCount:runningCount}' `
  --output table

Write-Host "`n✅ Deployment initiated!" -ForegroundColor Green
Write-Host "Monitoring deployment..." -ForegroundColor Yellow
```

**Expected Output**: Service update confirmation with deployment status

---

### Step 7: Monitor Deployment

```powershell
# Watch deployment progress (run multiple times)
Write-Host "`n=== Deployment Status ===" -ForegroundColor Cyan
aws ecs describe-services `
  --cluster babyshield-cluster `
  --services babyshield-backend-task-service-0l41s2a9 `
  --region eu-north-1 `
  --query 'services[0].deployments[*].{Status:status,TaskDef:taskDefinition,Running:runningCount,Desired:desiredCount}' `
  --output table

# Check recent service events
Write-Host "`n=== Recent Events ===" -ForegroundColor Cyan
aws ecs describe-services `
  --cluster babyshield-cluster `
  --services babyshield-backend-task-service-0l41s2a9 `
  --region eu-north-1 `
  --query 'services[0].events[0:5].[createdAt,message]' `
  --output table
```

**Wait for**: `PRIMARY` deployment with `runningCount == desiredCount`

---

### Step 8: Verify Deployment

```powershell
# Test health endpoints
Write-Host "`n=== Testing Endpoints ===" -ForegroundColor Cyan

$baseUrl = "https://babyshield.cureviax.ai"

# Test /healthz
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/healthz"
    Write-Host "✅ /healthz - " -NoNewline -ForegroundColor Green
    Write-Host "OK" -ForegroundColor Green
} catch {
    Write-Host "❌ /healthz - FAILED" -ForegroundColor Red
}

# Test /readyz
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/readyz"
    Write-Host "✅ /readyz - " -NoNewline -ForegroundColor Green
    Write-Host "OK" -ForegroundColor Green
} catch {
    Write-Host "❌ /readyz - FAILED" -ForegroundColor Red
}

# Test /api/v1/agencies
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/api/v1/agencies"
    Write-Host "✅ /api/v1/agencies - " -NoNewline -ForegroundColor Green
    Write-Host "OK (Found $($response.data.Length) agencies)" -ForegroundColor Green
} catch {
    Write-Host "❌ /api/v1/agencies - FAILED" -ForegroundColor Red
}

# Test search
try {
    $body = @{ product = "baby"; limit = 1 } | ConvertTo-Json
    $response = Invoke-RestMethod -Uri "$baseUrl/api/v1/search/advanced" -Method POST -Body $body -ContentType "application/json"
    Write-Host "✅ /api/v1/search/advanced - " -NoNewline -ForegroundColor Green
    Write-Host "OK (Total records: $($response.data.total))" -ForegroundColor Green
} catch {
    Write-Host "❌ /api/v1/search/advanced - FAILED" -ForegroundColor Red
}

Write-Host "`n🎉 Deployment Complete!" -ForegroundColor Green
```

---

## 📊 View CloudWatch Logs

```powershell
# Last 10 minutes of logs (colored output)
$logGroup = '/ecs/babyshield-backend'
$tenMinAgo = [int64]((Get-Date).AddMinutes(-10).ToUniversalTime().Subtract((Get-Date "1970-01-01")).TotalMilliseconds)
$now = [int64]((Get-Date).ToUniversalTime().Subtract((Get-Date "1970-01-01")).TotalMilliseconds)

aws logs filter-log-events `
  --log-group-name $logGroup `
  --start-time $tenMinAgo `
  --end-time $now `
  --limit 1000 `
  --output json | ConvertFrom-Json | ForEach-Object { $_.events } | Sort-Object timestamp | ForEach-Object { 
    $ts = [DateTimeOffset]::FromUnixTimeMilliseconds($_.timestamp).ToLocalTime()
    $msg = $_.message
    
    $color = 'White'
    if ($msg -match 'ERROR|Exception|Failed|500|502|503|504') { $color = 'Red' }
    elseif ($msg -match 'WARNING|WARN|400|401|403|404') { $color = 'Yellow' }
    elseif ($msg -match '200 OK|201|202|204') { $color = 'Green' }
    elseif ($msg -match 'INFO|GET|POST|PUT|DELETE') { $color = 'Cyan' }
    
    Write-Host $ts.ToString("yyyy-MM-ddTHH:mm:ss.fff") -ForegroundColor Green -NoNewline
    Write-Host " " -NoNewline
    Write-Host $msg -ForegroundColor $color
}
```

---

## 🔍 Troubleshooting

### Deployment Failed or Stuck

```powershell
# Check service events for errors
aws ecs describe-services `
  --cluster babyshield-cluster `
  --services babyshield-backend-task-service-0l41s2a9 `
  --region eu-north-1 `
  --query 'services[0].events[0:10].[createdAt,message]' `
  --output table

# Check task exit codes
aws ecs describe-tasks `
  --cluster babyshield-cluster `
  --tasks (aws ecs list-tasks --cluster babyshield-cluster --service-name babyshield-backend-task-service-0l41s2a9 --region eu-north-1 --query 'taskArns[0]' --output text) `
  --region eu-north-1 `
  --query 'tasks[0].containers[0].{Name:name,ExitCode:exitCode,Reason:reason}' `
  --output table
```

### Check Container Logs Directly

```powershell
# Get the latest task ARN
$taskArn = aws ecs list-tasks `
  --cluster babyshield-cluster `
  --service-name babyshield-backend-task-service-0l41s2a9 `
  --region eu-north-1 `
  --query 'taskArns[0]' `
  --output text

# Get container logs from the task
aws logs tail /ecs/babyshield-backend --since 30m --region eu-north-1 --follow
```

### Rollback to Previous Version

```powershell
# Rollback to task definition :183 (last known good - Oct 16, 2025)
aws ecs update-service `
  --cluster babyshield-cluster `
  --service babyshield-backend-task-service-0l41s2a9 `
  --task-definition babyshield-backend-task:183 `
  --force-new-deployment `
  --region eu-north-1

Write-Host "✅ Rolled back to task definition :183" -ForegroundColor Yellow
```

### Test Database Connection

```powershell
# Test search endpoint to verify DB connectivity
$body = @{ product = "baby"; limit = 1 } | ConvertTo-Json
$response = Invoke-RestMethod `
  -Uri "https://babyshield.cureviax.ai/api/v1/search/advanced" `
  -Method POST `
  -Body $body `
  -ContentType "application/json"

if ($response.ok -and $response.data.total -gt 0) {
    Write-Host "✅ Database connection working - $($response.data.total) total records" -ForegroundColor Green
} else {
    Write-Host "❌ Database connection issue or no data" -ForegroundColor Red
}
```

### Test Redis Connection

```powershell
# Check monitoring endpoint for Redis status
$response = Invoke-RestMethod -Uri "https://babyshield.cureviax.ai/api/v1/monitoring/readyz"
$response | ConvertTo-Json -Depth 3
```

---

## 📝 Important Notes

### ⚠️ Critical Points
1. **Always use service**: `babyshield-backend-task-service-0l41s2a9` (NOT `bv5v69zq` - that was deleted)
2. **Current production task**: `:183` (deployed Oct 16, 2025 - image: main-20251016-1353-aff4f77)
3. **Database has custom columns**: `severity`, `risk_category` (added manually, not in migrations)
4. **Redis is required**: Auth, rate limiting, visual processing all depend on Redis
5. **ECS auto-rollback enabled**: Failed deployments automatically roll back to last working version
6. **Health check grace period**: 60 seconds - allow time for app startup

### 🐳 Dockerfile Requirements
- Must use `Dockerfile.final` for production builds
- CMD must be: `uvicorn api.main_babyshield:app --host 0.0.0.0 --port 8001`
- Platform: `linux/amd64` (required for AWS Fargate)
- Port: Container listens on `8001`

### 🔐 Security
- Database password is in task definition (consider moving to AWS Secrets Manager)
- JWT secret key is in task definition (consider rotating periodically)
- All credentials are in environment variables, not hardcoded

### 📈 Performance
- CPU: 1 vCPU (1024 units)
- Memory: 2 GB (2048 MB)
- Consider scaling if needed for high traffic

---

## 🎯 Quick Reference

### Service Details
```powershell
# Get all service info
aws ecs describe-services `
  --cluster babyshield-cluster `
  --services babyshield-backend-task-service-0l41s2a9 `
  --region eu-north-1 | ConvertFrom-Json | ConvertTo-Json -Depth 10
```

### List All Task Definitions
```powershell
aws ecs list-task-definitions `
  --family-prefix babyshield-backend-task `
  --region eu-north-1 `
  --sort DESC `
  --max-items 10
```

### List All Images in ECR
```powershell
aws ecr list-images `
  --repository-name babyshield-backend `
  --region eu-north-1 `
  --query 'imageIds[*].imageTag' `
  --output table
```

---

## 📞 Support Contacts

- **Development**: Ross Daniel
- **AWS Account**: 180703226577
- **Region**: eu-north-1 (Stockholm)

---

**Last Updated**: October 16, 2025  
**Current Production Task**: babyshield-backend-task:183  
**Current Production Image**: main-20251016-1353-aff4f77  
**Deployment Status**: ✅ Active and Healthy

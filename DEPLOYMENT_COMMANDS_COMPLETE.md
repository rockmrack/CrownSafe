# 🚀 COMPLETE DEPLOYMENT COMMANDS - BABYSHIELD BACKEND

## ✅ STEP-BY-STEP COMMANDS (COPY & PASTE READY)

### 📦 **STEP 1: BUILD THE FIXED DOCKER IMAGE**
```bash
docker build -f Dockerfile.final -t babyshield-backend:complete .
```

### 🔐 **STEP 2: LOGIN TO AWS ECR**
```bash
aws ecr get-login-password --region eu-north-1 | docker login --username AWS --password-stdin 180703226577.dkr.ecr.eu-north-1.amazonaws.com
```

### 🏷️ **STEP 3: TAG THE IMAGE FOR ECR**
```bash
docker tag babyshield-backend:complete 180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:production-20250831
```

### 📤 **STEP 4: PUSH TO ECR**
```bash
docker push 180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:production-20250831
```

### 📋 **STEP 5: REGISTER NEW ECS TASK DEFINITION**
```bash
aws ecs register-task-definition \
  --family babyshield-backend-task \
  --task-role-arn arn:aws:iam::180703226577:role/babyshield-task-role \
  --execution-role-arn arn:aws:iam::180703226577:role/ecsTaskExecutionRole \
  --network-mode awsvpc \
  --requires-compatibilities FARGATE \
  --cpu 1024 \
  --memory 2048 \
  --region eu-north-1 \
  --container-definitions '[{
    "name": "babyshield-backend",
    "image": "180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:production-20250831",
    "essential": true,
    "portMappings": [{"containerPort": 8001, "protocol": "tcp"}],
    "environment": [
      {"name": "DATABASE_URL", "value": "postgresql://your-db-connection-string"},
      {"name": "OPENAI_API_KEY", "value": "your-openai-api-key"},
      {"name": "JWT_SECRET_KEY", "value": "your-jwt-secret-key"},
      {"name": "SECRET_KEY", "value": "your-application-secret-key"},
      {"name": "ENCRYPTION_KEY", "value": "your-encryption-key"},
      {"name": "API_HOST", "value": "0.0.0.0"},
      {"name": "API_PORT", "value": "8001"},
      {"name": "DISABLE_REDIS_WARNING", "value": "true"}
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
      "command": ["CMD-SHELL", "curl -f http://localhost:8001/health || exit 1"],
      "interval": 30,
      "timeout": 10,
      "retries": 3,
      "startPeriod": 60
    }
  }]' \
  --query 'taskDefinition.taskDefinitionArn' \
  --output text
```

### 🔄 **STEP 6: UPDATE ECS SERVICE (OPTIONAL)**
If you have an existing service, update it to use the new task definition:
```bash
aws ecs update-service \
  --cluster your-cluster-name \
  --service babyshield-backend-service \
  --task-definition babyshield-backend-task \
  --region eu-north-1
```

---

## 🎯 **ALL COMMANDS IN ONE SCRIPT**

### **PowerShell Version (Windows)**
Save as `deploy.ps1`:
```powershell
# Complete Deployment Script
Write-Host "Starting BabyShield Backend Deployment..." -ForegroundColor Green

# Build
Write-Host "Building Docker image..." -ForegroundColor Yellow
docker build -f Dockerfile.final -t babyshield-backend:complete .

# Login to ECR
Write-Host "Logging into ECR..." -ForegroundColor Yellow
aws ecr get-login-password --region eu-north-1 | docker login --username AWS --password-stdin 180703226577.dkr.ecr.eu-north-1.amazonaws.com

# Tag
Write-Host "Tagging image..." -ForegroundColor Yellow
docker tag babyshield-backend:complete 180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:production-20250831

# Push
Write-Host "Pushing to ECR..." -ForegroundColor Yellow
docker push 180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:production-20250831

Write-Host "✅ Deployment complete! Now register the task definition in AWS Console or CloudShell." -ForegroundColor Green
```

### **Bash Version (Linux/Mac)**
Save as `deploy.sh`:
```bash
#!/bin/bash
echo "Starting BabyShield Backend Deployment..."

# Build
echo "Building Docker image..."
docker build -f Dockerfile.final -t babyshield-backend:complete .

# Login to ECR
echo "Logging into ECR..."
aws ecr get-login-password --region eu-north-1 | docker login --username AWS --password-stdin 180703226577.dkr.ecr.eu-north-1.amazonaws.com

# Tag
echo "Tagging image..."
docker tag babyshield-backend:complete 180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:production-20250831

# Push
echo "Pushing to ECR..."
docker push 180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:production-20250831

echo "✅ Deployment complete! Now register the task definition."
```

---

## ⚠️ **IMPORTANT NOTES**

1. **Replace these values in Step 5:**
   - `your-db-connection-string` → Your actual PostgreSQL connection string
   - `your-openai-api-key` → Your actual OpenAI API key
   - `your-jwt-secret-key` → A secure JWT secret
   - `your-application-secret-key` → A secure application secret
   - `your-encryption-key` → A secure encryption key

2. **Image tag format:**
   - Using date: `production-20250831`
   - You can also use: `production-v1.0.0` or any versioning scheme

3. **Verify before deployment:**
   ```bash
   # Test the image locally first
   docker run --rm -p 8001:8001 babyshield-backend:complete
   ```

---

## ✅ **EXPECTED RESULT**
- Docker build: SUCCESS
- ECR push: SUCCESS
- ECS task registration: SUCCESS
- API starts without errors
- All endpoints working
- Health checks passing

---

## 🆘 **TROUBLESHOOTING**

If you encounter issues:

1. **Build fails:** Check `Dockerfile.final` exists
2. **Login fails:** Check AWS CLI is configured
3. **Push fails:** Check ECR repository exists
4. **Task fails:** Check CloudWatch logs in `/ecs/babyshield-backend`

---

## 📞 **NEED HELP?**
If any command fails, share the error message for specific assistance.

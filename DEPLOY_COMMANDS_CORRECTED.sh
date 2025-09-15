#!/bin/bash

# CORRECTED DEPLOYMENT COMMANDS FOR BABYSHIELD BACKEND
# Date: 2025-08-31

echo "🚀 Starting BabyShield Backend Deployment"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 1. BUILD NEW IMAGE (with all fixes)
echo "📦 Step 1: Building Docker image..."
docker build -f Dockerfile.final -t babyshield-backend:complete .

# 2. LOGIN TO ECR (your command is correct)
echo "🔐 Step 2: Logging into ECR..."
aws ecr get-login-password --region eu-north-1 | docker login --username AWS --password-stdin 180703226577.dkr.ecr.eu-north-1.amazonaws.com

# 3. TAG with NEW version (using today's date)
echo "🏷️ Step 3: Tagging image..."
docker tag babyshield-backend:complete 180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:production-20250831

# 4. PUSH
echo "📤 Step 4: Pushing to ECR..."
docker push 180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:production-20250831

# 5. CREATE NEW TASK DEFINITION (CORRECTED)
echo "📋 Step 5: Registering ECS task definition..."
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
      {"name": "DATABASE_URL", "value": "YOUR_PRODUCTION_DB_URL"},
      {"name": "OPENAI_API_KEY", "value": "YOUR_OPENAI_KEY"},
      {"name": "JWT_SECRET_KEY", "value": "YOUR_JWT_SECRET"},
      {"name": "SECRET_KEY", "value": "YOUR_SECRET_KEY"},
      {"name": "ENCRYPTION_KEY", "value": "YOUR_ENCRYPTION_KEY"},
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

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Deployment complete!"

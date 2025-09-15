#!/bin/bash
# BabyShield API - AWS Deployment Script
# This script builds and deploys the BabyShield API to AWS ECS/Fargate

set -e  # Exit on error

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-$(aws sts get-caller-identity --query Account --output text)}"
ECR_REPOSITORY="babyshield-api"
ECS_CLUSTER="babyshield-cluster"
ECS_SERVICE="babyshield-api-service"
ECS_TASK_FAMILY="babyshield-api-task"
IMAGE_TAG="${IMAGE_TAG:-latest}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 BabyShield API Deployment to AWS${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Step 1: Check AWS CLI is installed
echo -e "${YELLOW}Checking AWS CLI...${NC}"
if ! command -v aws &> /dev/null; then
    echo -e "${RED}AWS CLI is not installed. Please install it first.${NC}"
    exit 1
fi

# Step 2: Authenticate Docker to ECR
echo -e "${YELLOW}Authenticating Docker with ECR...${NC}"
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Step 3: Create ECR repository if it doesn't exist
echo -e "${YELLOW}Creating ECR repository if needed...${NC}"
aws ecr describe-repositories --repository-names $ECR_REPOSITORY --region $AWS_REGION 2>/dev/null || \
aws ecr create-repository --repository-name $ECR_REPOSITORY --region $AWS_REGION

# Step 4: Build Docker image
echo -e "${YELLOW}Building Docker image...${NC}"
docker build -t $ECR_REPOSITORY:$IMAGE_TAG .

# Step 5: Tag image for ECR
echo -e "${YELLOW}Tagging image for ECR...${NC}"
docker tag $ECR_REPOSITORY:$IMAGE_TAG $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:$IMAGE_TAG

# Step 6: Push image to ECR
echo -e "${YELLOW}Pushing image to ECR...${NC}"
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:$IMAGE_TAG

# Step 7: Register new task definition
echo -e "${YELLOW}Registering new task definition...${NC}"
cat > task-definition.json <<EOF
{
  "family": "$ECS_TASK_FAMILY",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "containerDefinitions": [
    {
      "name": "babyshield-api",
      "image": "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:$IMAGE_TAG",
      "portMappings": [
        {
          "containerPort": 8001,
          "protocol": "tcp"
        }
      ],
      "essential": true,
      "environment": [
        {"name": "API_HOST", "value": "0.0.0.0"},
        {"name": "API_PORT", "value": "8001"},
        {"name": "ENABLE_CACHE", "value": "true"},
        {"name": "ENABLE_BACKGROUND_TASKS", "value": "true"}
      ],
      "secrets": [
        {"name": "DATABASE_URL", "valueFrom": "arn:aws:secretsmanager:$AWS_REGION:$AWS_ACCOUNT_ID:secret:babyshield/database-url"},
        {"name": "REDIS_URL", "valueFrom": "arn:aws:secretsmanager:$AWS_REGION:$AWS_ACCOUNT_ID:secret:babyshield/redis-url"},
        {"name": "SECRET_KEY", "valueFrom": "arn:aws:secretsmanager:$AWS_REGION:$AWS_ACCOUNT_ID:secret:babyshield/secret-key"},
        {"name": "JWT_SECRET_KEY", "valueFrom": "arn:aws:secretsmanager:$AWS_REGION:$AWS_ACCOUNT_ID:secret:babyshield/jwt-secret"},
        {"name": "OPENAI_API_KEY", "valueFrom": "arn:aws:secretsmanager:$AWS_REGION:$AWS_ACCOUNT_ID:secret:babyshield/openai-api-key"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/babyshield-api",
          "awslogs-region": "$AWS_REGION",
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
    }
  ],
  "executionRoleArn": "arn:aws:iam::$AWS_ACCOUNT_ID:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::$AWS_ACCOUNT_ID:role/ecsTaskRole"
}
EOF

TASK_DEFINITION_ARN=$(aws ecs register-task-definition \
    --cli-input-json file://task-definition.json \
    --query 'taskDefinition.taskDefinitionArn' \
    --output text \
    --region $AWS_REGION)

echo -e "${GREEN}Task definition registered: $TASK_DEFINITION_ARN${NC}"

# Step 8: Update ECS service
echo -e "${YELLOW}Updating ECS service...${NC}"
aws ecs update-service \
    --cluster $ECS_CLUSTER \
    --service $ECS_SERVICE \
    --task-definition $TASK_DEFINITION_ARN \
    --force-new-deployment \
    --region $AWS_REGION

# Step 9: Wait for service to stabilize
echo -e "${YELLOW}Waiting for service to stabilize...${NC}"
aws ecs wait services-stable \
    --cluster $ECS_CLUSTER \
    --services $ECS_SERVICE \
    --region $AWS_REGION

# Step 10: Get service status
echo -e "${YELLOW}Getting service status...${NC}"
aws ecs describe-services \
    --cluster $ECS_CLUSTER \
    --services $ECS_SERVICE \
    --query 'services[0].{Status:status,RunningCount:runningCount,DesiredCount:desiredCount}' \
    --output table \
    --region $AWS_REGION

# Clean up temporary files
rm -f task-definition.json

echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}Your API should be accessible at your ALB endpoint.${NC}"
echo -e "${YELLOW}Check the AWS console for the exact URL.${NC}"
#!/bin/bash
# Deploy Task 11 to AWS

echo "========================================"
echo "DEPLOYING TASK 11 - App Integration QA"
echo "========================================"

# Build Docker image
echo "Step 1: Building Docker image..."
docker build --no-cache -f Dockerfile.final -t babyshield-backend:task11 .

if [ $? -ne 0 ]; then
    echo "Build failed! Trying alternative Dockerfile..."
    docker build --no-cache -f Dockerfile.final -t babyshield-backend:task11 .
fi

# Login to ECR
echo "Step 2: Logging into ECR..."
aws ecr get-login-password --region eu-north-1 | docker login --username AWS --password-stdin 180703226577.dkr.ecr.eu-north-1.amazonaws.com

# Tag image
echo "Step 3: Tagging image..."
docker tag babyshield-backend:task11 180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:latest
docker tag babyshield-backend:task11 180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:task11

# Push to ECR
echo "Step 4: Pushing to ECR..."
docker push 180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:latest
docker push 180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:task11

# Update ECS service
echo "Step 5: Updating ECS service..."
aws ecs update-service \
    --cluster babyshield-cluster \
    --service babyshield-backend \
    --force-new-deployment \
    --region eu-north-1

echo ""
echo "========================================"
echo "DEPLOYMENT INITIATED!"
echo "========================================"
echo ""
echo "Wait 2-3 minutes for ECS to update, then run:"
echo "python verify_task11_deployment.py"

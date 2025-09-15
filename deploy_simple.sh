#!/bin/bash
# Simplified BabyShield Deployment Script
# Focuses on building and pushing the Docker image correctly

set -e

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
ECR_REPOSITORY="babyshield-api"
IMAGE_TAG="${IMAGE_TAG:-latest}"

echo "🚀 BabyShield Deployment Script"
echo "================================"

# Get AWS account ID
echo "Getting AWS account ID..."
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null)
if [ -z "$AWS_ACCOUNT_ID" ]; then
    echo "❌ Failed to get AWS account ID. Check your AWS credentials."
    exit 1
fi
echo "✅ AWS Account: $AWS_ACCOUNT_ID"

# Authenticate Docker with ECR
echo "Authenticating with ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
echo "✅ Docker authenticated"

# Create repository if needed
echo "Checking ECR repository..."
if ! aws ecr describe-repositories --repository-names $ECR_REPOSITORY --region $AWS_REGION 2>/dev/null; then
    echo "Creating ECR repository..."
    aws ecr create-repository --repository-name $ECR_REPOSITORY --region $AWS_REGION
    echo "✅ Repository created"
else
    echo "✅ Repository exists"
fi

# Build Docker image
echo "Building Docker image..."
docker build -t $ECR_REPOSITORY:$IMAGE_TAG . --no-cache
echo "✅ Image built"

# Tag for ECR
echo "Tagging image..."
docker tag $ECR_REPOSITORY:$IMAGE_TAG $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:$IMAGE_TAG
echo "✅ Image tagged"

# Push to ECR
echo "Pushing to ECR..."
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:$IMAGE_TAG
echo "✅ Image pushed successfully!"

echo ""
echo "================================"
echo "✅ DEPLOYMENT COMPLETE"
echo "Image: $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:$IMAGE_TAG"
echo ""
echo "Next steps:"
echo "1. Update your ECS task definition to use this image"
echo "2. Deploy the new task definition to your ECS service"
echo "================================"

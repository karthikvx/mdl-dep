#!/bin/bash

set -e

echo "=== Building and Pushing Docker Images ==="

# Configuration
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=${AWS_DEFAULT_REGION:-us-east-1}
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
IMAGE_TAG=${1:-latest}

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY

# Build and push each service
services=("loan-pricing-service" "default-prediction-service" "main-orchestrator")

for service in "${services[@]}"; do
    echo "Building $service..."
    
    # Build image
    docker build -f docker/Dockerfile.$service -t $service:$IMAGE_TAG .
    
    # Tag for ECR
    docker tag $service:$IMAGE_TAG $ECR_REGISTRY/mortgage-app/$service:$IMAGE_TAG
    
    # Push to ECR
    docker push $ECR_REGISTRY/mortgage-app/$service:$IMAGE_TAG
    
    echo "✓ $service built and pushed"
done

# Update Kubernetes manifests with new image tags
sed -i "s|IMAGE_TAG|$IMAGE_TAG|g" k8s/*.yaml

echo "=== Build and push complete ==="
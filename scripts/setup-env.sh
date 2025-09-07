#!/bin/bash

set -e

echo "=== Mortgage Application Environment Setup ==="

# Check prerequisites
check_prerequisites() {
    echo "Checking prerequisites..."
    
    commands=("docker" "kubectl" "aws" "helm")
    for cmd in "${commands[@]}"; do
        if ! command -v $cmd &> /dev/null; then
            echo "Error: $cmd is not installed"
            exit 1
        fi
    done
    
    echo "✓ All prerequisites met"
}

# Setup AWS resources
setup_aws_resources() {
    echo "Setting up AWS resources..."
    
    # Create ECR repositories
    aws ecr create-repository --repository-name mortgage-app/loan-pricing-service || true
    aws ecr create-repository --repository-name mortgage-app/default-prediction-service || true
    aws ecr create-repository --repository-name mortgage-app/main-orchestrator || true
    
    # Create EventBridge custom bus
    aws events create-event-bus --name mortgage-application-bus || true
    
    # Create DynamoDB table
    aws dynamodb create-table \
        --table-name loan-pricing \
        --attribute-definitions \
            AttributeName=loan_id,AttributeType=S \
        --key-schema \
            AttributeName=loan_id,KeyType=HASH \
        --provisioned-throughput \
            ReadCapacityUnits=5,WriteCapacityUnits=5 || true
    
    # Create S3 bucket for ML models
    aws s3 mb s3://mortgage-app-ml-models-$(date +%s) || true
    
    echo "✓ AWS resources created"
}

# Setup Kubernetes namespace and secrets
setup_k8s_namespace() {
    echo "Setting up Kubernetes namespace..."
    
    kubectl create namespace mortgage-app || true
    
    # Create AWS credentials secret
    kubectl create secret generic aws-credentials \
        --from-literal=aws-access-key-id=$AWS_ACCESS_KEY_ID \
        --from-literal=aws-secret-access-key=$AWS_SECRET_ACCESS_KEY \
        --from-literal=aws-region=$AWS_DEFAULT_REGION \
        -n mortgage-app || true
    
    # Create application secrets
    kubectl create secret generic app-secrets \
        --from-literal=redis-password=$(openssl rand -base64 32) \
        --from-literal=jwt-secret=$(openssl rand -base64 32) \
        -n mortgage-app || true
    
    echo "✓ Kubernetes namespace and secrets configured"
}

# Install monitoring stack
install_monitoring() {
    echo "Installing monitoring stack..."
    
    # Add Helm repositories
    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
    helm repo add grafana https://grafana.github.io/helm-charts
    helm repo update
    
    # Install Prometheus
    helm install prometheus prometheus-community/kube-prometheus-stack \
        --namespace monitoring \
        --create-namespace \
        --set grafana.adminPassword=admin123 \
        --wait || true
    
    echo "✓ Monitoring stack installed"
}

main() {
    check_prerequisites
    setup_aws_resources
    setup_k8s_namespace
    install_monitoring
    
    echo "=== Environment setup complete ==="
    echo "Next steps:"
    echo "1. Run ./build-images.sh to build and push Docker images"
    echo "2. Run ./deploy.sh to deploy the application"
}

main "$@"
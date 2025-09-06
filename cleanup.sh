#!/bin/bash

set -e

echo "=== Cleaning Up Mortgage Application ==="

NAMESPACE="mortgage-app"
FORCE=${1:-false}

cleanup_k8s() {
    echo "Cleaning up Kubernetes resources..."
    
    if [ "$FORCE" = "true" ]; then
        kubectl delete namespace $NAMESPACE --force --grace-period=0 || true
    else
        kubectl delete namespace $NAMESPACE || true
    fi
    
    echo "✓ Kubernetes resources cleaned up"
}

cleanup_aws() {
    echo "Cleaning up AWS resources..."
    
    read -p "Do you want to delete AWS resources? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Delete ECR repositories
        aws ecr delete-repository --repository-name mortgage-app/loan-pricing-service --force || true
        aws ecr delete-repository --repository-name mortgage-app/default-prediction-service --force || true
        aws ecr delete-repository --repository-name mortgage-app/main-orchestrator --force || true
        
        # Delete EventBridge bus
        aws events delete-event-bus --name mortgage-application-bus || true
        
        # Delete DynamoDB table
        aws dynamodb delete-table --table-name loan-pricing || true
        
        echo "✓ AWS resources cleaned up"
    else
        echo "Skipping AWS cleanup"
    fi
}

main() {
    cleanup_k8s
    cleanup_aws
    
    echo "=== Cleanup complete ==="
}

main "$@"
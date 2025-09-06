#!/bin/bash

set -e

echo "=== Deploying Mortgage Application ==="

# Configuration
NAMESPACE="mortgage-app"
ENVIRONMENT=${1:-staging}

deploy_infrastructure() {
    echo "Deploying infrastructure components..."
    
    # Deploy Redis
    kubectl apply -f k8s/redis-deployment.yaml -n $NAMESPACE
    kubectl apply -f k8s/redis-service.yaml -n $NAMESPACE
    
    # Wait for Redis to be ready
    kubectl wait --for=condition=available --timeout=300s deployment/redis -n $NAMESPACE
    
    echo "✓ Infrastructure deployed"
}

deploy_applications() {
    echo "Deploying application services..."
    
    # Deploy services in order
    services=("loan-pricing-service" "default-prediction-service" "main-orchestrator")
    
    for service in "${services[@]}"; do
        echo "Deploying $service..."
        
        kubectl apply -f k8s/$service-deployment.yaml -n $NAMESPACE
        kubectl apply -f k8s/$service-service.yaml -n $NAMESPACE
        
        # Wait for deployment to be ready
        kubectl wait --for=condition=available --timeout=300s deployment/$service -n $NAMESPACE
        
        echo "✓ $service deployed"
    done
}

deploy_networking() {
    echo "Deploying networking components..."
    
    # Apply network policies
    kubectl apply -f k8s/network-policy.yaml -n $NAMESPACE
    
    # Deploy ingress
    kubectl apply -f k8s/nginx-ingress.yaml -n $NAMESPACE
    
    echo "✓ Networking configured"
}

deploy_monitoring() {
    echo "Deploying monitoring configuration..."
    
    # Apply ServiceMonitor for Prometheus
    kubectl apply -f k8s/service-monitor.yaml -n $NAMESPACE
    
    # Apply HPA
    kubectl apply -f k8s/hpa.yaml -n $NAMESPACE
    
    echo "✓ Monitoring and autoscaling configured"
}

verify_deployment() {
    echo "Verifying deployment..."
    
    # Check pod status
    kubectl get pods -n $NAMESPACE
    
    # Check services
    kubectl get svc -n $NAMESPACE
    
    # Run health checks
    services=("loan-pricing-service" "default-prediction-service" "main-orchestrator")
    
    for service in "${services[@]}"; do
        echo "Checking $service health..."
        
        pod=$(kubectl get pods -n $NAMESPACE -l app=$service -o jsonpath='{.items[0].metadata.name}')
        
        if kubectl exec $pod -n $NAMESPACE -- wget -q --spider http://localhost:8080/health; then
            echo "✓ $service is healthy"
        else
            echo "✗ $service health check failed"
        fi
    done
}

main() {
    echo "Deploying to environment: $ENVIRONMENT"
    
    deploy_infrastructure
    deploy_applications
    deploy_networking
    deploy_monitoring
    verify_deployment
    
    echo "=== Deployment complete ==="
    echo "Access the application at: https://$(kubectl get ingress -n $NAMESPACE -o jsonpath='{.items[0].spec.rules[0].host}')"
    echo "Grafana dashboard: http://$(kubectl get svc -n monitoring prometheus-grafana -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'):3000"
}

main "$@"
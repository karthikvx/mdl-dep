#!/bin/bash

set -e

echo "=== Rolling Back Mortgage Application ==="

NAMESPACE="mortgage-app"
REVISION=${1:-1}

rollback_service() {
    local service=$1
    local revision=${2:-1}
    
    echo "Rolling back $service to revision $revision..."
    
    kubectl rollout undo deployment/$service --to-revision=$revision -n $NAMESPACE
    kubectl rollout status deployment/$service -n $NAMESPACE
    
    echo "✓ $service rolled back"
}

main() {
    if [ -z "$1" ]; then
        echo "Usage: $0 <revision-number>"
        echo "Available revisions:"
        kubectl rollout history deployment/main-orchestrator -n $NAMESPACE
        exit 1
    fi
    
    services=("main-orchestrator" "default-prediction-service" "loan-pricing-service")
    
    for service in "${services[@]}"; do
        rollback_service $service $REVISION
    done
    
    echo "=== Rollback complete ==="
}

main "$@"
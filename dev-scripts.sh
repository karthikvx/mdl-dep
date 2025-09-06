#!/bin/bash

# Development helper functions

# Port forward to services for local development
port_forward() {
    echo "Setting up port forwarding for development..."
    
    kubectl port-forward -n mortgage-app svc/loan-pricing-service 8081:8080 &
    kubectl port-forward -n mortgage-app svc/default-prediction-service 8082:8080 &
    kubectl port-forward -n mortgage-app svc/main-orchestrator 8083:8080 &
    kubectl port-forward -n mortgage-app svc/redis 6379:6379 &
    kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80 &
    
    echo "Port forwarding active:"
    echo "- Loan Pricing Service: http://localhost:8081"
    echo "- Default Prediction Service: http://localhost:8082"
    echo "- Main Orchestrator: http://localhost:8083"
    echo "- Redis: localhost:6379"
    echo "- Grafana: http://localhost:3000"
    echo ""
    echo "Press Ctrl+C to stop all port forwards"
    wait
}

# View logs from all services
view_logs() {
    echo "Streaming logs from all services..."
    
    kubectl logs -f -l app=loan-pricing-service -n mortgage-app --prefix=true &
    kubectl logs -f -l app=default-prediction-service -n mortgage-app --prefix=true &
    kubectl logs -f -l app=main-orchestrator -n mortgage-app --prefix=true &
    
    wait
}

# Run integration tests
run_tests() {
    echo "Running integration tests..."
    
    # Test loan pricing service
    curl -X POST http://localhost:8081/api/v1/pricing \
        -H "Content-Type: application/json" \
        -d '{"loan_amount": 300000, "credit_score": 750, "loan_term": 30}'
    
    # Test default prediction service
    curl -X POST http://localhost:8082/api/v1/predict \
        -H "Content-Type: application/json" \
        -d '{"loan_amount": 300000, "credit_score": 750, "income": 80000}'
    
    # Test main orchestrator
    curl -X POST http://localhost:8083/api/v1/process-application \
        -H "Content-Type: application/json" \
        -d '{"applicant_id": "test123", "loan_amount": 300000, "credit_score": 750}'
    
    echo "✓ Integration tests completed"
}

# Show application status
show_status() {
    echo "=== Mortgage Application Status ==="
    
    echo "Pods:"
    kubectl get pods -n mortgage-app
    
    echo -e "\nServices:"
    kubectl get svc -n mortgage-app
    
    echo -e "\nIngress:"
    kubectl get ingress -n mortgage-app
    
    echo -e "\nHPA Status:"
    kubectl get hpa -n mortgage-app
    
    echo -e "\nResource Usage:"
    kubectl top pods -n mortgage-app
}

# Menu system
show_menu() {
    echo "=== Development Helper Menu ==="
    echo "1. Port Forward Services"
    echo "2. View Logs"
    echo "3. Run Integration Tests"
    echo "4. Show Application Status"
    echo "5. Exit"
    echo
}

main() {
    while true; do
        show_menu
        read -p "Select an option (1-5): " choice
        
        case $choice in
            1) port_forward ;;
            2) view_logs ;;
            3) run_tests ;;
            4) show_status ;;
            5) exit 0 ;;
            *) echo "Invalid option" ;;
        esac
        
        echo
        read -p "Press Enter to continue..."
    done
}

# Check if script is being sourced or executed
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
import os

def main():
    """Main entry point - determines which service to run"""
    service_type = os.getenv('SERVICE_TYPE', 'orchestrator')
    port = int(os.getenv('PORT', 5000))
    
    if service_type == 'pricing':
        from app.api.pricing_api import pricing_app
        print(f"Starting Pricing Service on port {port}")
        pricing_app.run(host='0.0.0.0', port=port, debug=False)
        
    elif service_type == 'prediction':
        from app.api.prediction_api import prediction_app
        print(f"Starting Prediction Service on port {port}")
        prediction_app.run(host='0.0.0.0', port=port, debug=False)
        
    elif service_type == 'orchestrator':
        from app.api.orchestrator_api import orchestrator_app
        print(f"Starting Orchestrator Service on port {port}")
        orchestrator_app.run(host='0.0.0.0', port=port, debug=False)
        
    elif service_type == 'training':  # NEW
        from app.api.training_api import training_app
        print(f"Starting Model Training Service on port {port}")
        training_app.run(host='0.0.0.0', port=port, debug=False)
        
    else:
        raise ValueError(f"Unknown service type: {service_type}")

if __name__ == '__main__':
    main()

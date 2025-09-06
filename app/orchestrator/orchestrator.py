from flask import Flask, request, jsonify
import threading
import time
import requests

class MortgageApplicationOrchestrator:
    def __init__(self):
        self.event_publisher = EventPublisher()
        self.dynamodb = boto3.resource('dynamodb')
        self.results_table = self.dynamodb.Table('loan-application-results')
        
        # Service endpoints (in real deployment, these would be service discovery URLs)
        self.pricing_service_url = "http://loan-pricing-service:5000"
        self.prediction_service_url = "http://default-prediction-service:5001"
    
    def submit_loan_application(self, loan_app: LoanApplication) -> str:
        """Submit loan application and trigger processing"""
        
        # Initialize result record
        self.results_table.put_item(
            Item={
                'application_id': loan_app.application_id,
                'application_data': loan_app.__dict__,
                'created_at': loan_app.timestamp,
                'processing_complete': False
            }
        )
        
        # Publish loan application event to EventBridge
        # This will trigger both microservices simultaneously
        self.event_publisher.publish_event(
            source='mortgage-application',
            detail_type='LoanApplicationSubmitted',
            detail=asdict(loan_app)
        )
        
        # Also make direct HTTP calls for immediate processing
        # (In production, services would listen to EventBridge events)
        def call_pricing_service():
            try:
                response = requests.post(
                    f"{self.pricing_service_url}/process",
                    json=asdict(loan_app),
                    timeout=10
                )
            except Exception as e:
                print(f"Error calling pricing service: {e}")
        
        def call_prediction_service():
            try:
                response = requests.post(
                    f"{self.prediction_service_url}/predict",
                    json=asdict(loan_app),
                    timeout=10
                )
            except Exception as e:
                print(f"Error calling prediction service: {e}")
        
        # Call services in parallel
        pricing_thread = threading.Thread(target=call_pricing_service)
        prediction_thread = threading.Thread(target=call_prediction_service)
        
        pricing_thread.start()
        prediction_thread.start()
        
        return loan_app.application_id
    
    def get_application_status(self, application_id: str) -> dict:
        """Get current status of loan application"""
        try:
            response = self.results_table.get_item(
                Key={'application_id': application_id}
            )
            
            if 'Item' not in response:
                return {"error": "Application not found"}
            
            item = response['Item']
            
            # Convert Decimal to float for JSON serialization
            def convert_decimals(obj):
                if isinstance(obj, dict):
                    return {k: convert_decimals(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_decimals(item) for item in obj]
                elif hasattr(obj, '__float__'):
                    return float(obj)
                return obj
            
            return convert_decimals(dict(item))
            
        except Exception as e:
            return {"error": str(e)}

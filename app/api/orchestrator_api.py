from flask import Flask, request, jsonify
from prometheus_flask_exporter import PrometheusMetrics
from app.services.pricing_service import LoanPricingService
from app.services.prediction_service import DefaultPredictionService
from app.models.schemas import LoanApplication
import logging
import threading
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Flask app
orchestrator_app = Flask(__name__)
metrics = PrometheusMetrics(orchestrator_app)

# Initialize services
pricing_service = LoanPricingService()
prediction_service = DefaultPredictionService()

@orchestrator_app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'mortgage-application-orchestrator',
        'version': '1.0.0'
    })

@orchestrator_app.route('/process_application', methods=['POST'])
def process_application():
    """Process complete loan application (pricing + risk prediction)"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['loan_amount', 'credit_score', 'dti_ratio']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Create loan application
        loan_app = LoanApplication(
            loan_amount=float(data['loan_amount']),
            credit_score=int(data['credit_score']),
            dti_ratio=float(data['dti_ratio']),
            application_id=data.get('application_id')
        )
        
        # Process both pricing and prediction in parallel
        pricing_result = None
        prediction_result = None
        errors = []
        
        def process_pricing():
            nonlocal pricing_result, errors
            try:
                pricing_result = pricing_service.process_loan_pricing(loan_app)
            except Exception as e:
                errors.append(f"Pricing error: {str(e)}")
        
        def process_prediction():
            nonlocal prediction_result, errors
            try:
                prediction_result = prediction_service.predict_default_risk(loan_app)
            except Exception as e:
                errors.append(f"Prediction error: {str(e)}")
        
        # Run both services in parallel
        pricing_thread = threading.Thread(target=process_pricing)
        prediction_thread = threading.Thread(target=process_prediction)
        
        pricing_thread.start()
        prediction_thread.start()
        
        pricing_thread.join(timeout=10)  # 10 second timeout
        prediction_thread.join(timeout=10)
        
        if errors:
            return jsonify({'errors': errors}), 500
        
        # Combine results
        response = {
            'application_id': loan_app.application_id,
            'pricing': {
                'interest_rate': pricing_result.interest_rate,
                'processing_time_ms': pricing_result.processing_time_ms
            },
            'risk_prediction': {
                'default_risk': prediction_result.default_risk,
                'risk_probability': prediction_result.risk_probability,
                'processing_time_ms': prediction_result.processing_time_ms
            },
            'timestamp': loan_app.timestamp
        }
        
        logger.info(f"Completed processing for application {loan_app.application_id}")
        
        return jsonify(response)
        
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return jsonify({'error': f'Invalid input: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Processing error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@orchestrator_app.route('/metrics')
def metrics_endpoint():
    """Prometheus metrics endpoint"""
    return metrics.registry.collect()

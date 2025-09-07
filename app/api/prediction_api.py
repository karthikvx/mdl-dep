from flask import Flask, request, jsonify
from prometheus_flask_exporter import PrometheusMetrics
from app.services.prediction_service import DefaultPredictionService
from app.models.schemas import LoanApplication
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Flask app
prediction_app = Flask(__name__)
metrics = PrometheusMetrics(prediction_app)

# Initialize service
prediction_service = DefaultPredictionService()

@prediction_app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'default-prediction-service',
        'version': '1.0.0'
    })

@prediction_app.route('/predict_default', methods=['POST'])
def predict_default():
    """Process default risk prediction request"""
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
        
        # Process prediction
        result = prediction_service.predict_default_risk(loan_app)
        
        logger.info(f"Processed prediction for application {result.application_id}")
        
        return jsonify({
            'application_id': result.application_id,
            'default_risk': result.default_risk,
            'risk_probability': result.risk_probability,
            'processing_time_ms': result.processing_time_ms,
            'timestamp': result.timestamp
        })
        
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return jsonify({'error': f'Invalid input: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Processing error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@prediction_app.route('/metrics')
def metrics_endpoint():
    """Prometheus metrics endpoint"""
    return metrics.registry.collect()

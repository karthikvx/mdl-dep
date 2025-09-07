from flask import Flask, request, jsonify
from prometheus_flask_exporter import PrometheusMetrics
from app.services.pricing_service import LoanPricingService
from app.models.schemas import LoanApplication
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Flask app
pricing_app = Flask(__name__)
metrics = PrometheusMetrics(pricing_app)

# Initialize service
pricing_service = LoanPricingService()

@pricing_app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'loan-pricing-service',
        'version': '1.0.0'
    })

@pricing_app.route('/price_loan', methods=['POST'])
def price_loan():
    """Process loan pricing request"""
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
        
        # Process pricing
        result = pricing_service.process_loan_pricing(loan_app)
        
        logger.info(f"Processed pricing for application {result.application_id}")
        
        return jsonify({
            'application_id': result.application_id,
            'interest_rate': result.interest_rate,
            'processing_time_ms': result.processing_time_ms,
            'timestamp': result.timestamp
        })
        
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return jsonify({'error': f'Invalid input: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Processing error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@pricing_app.route('/metrics')
def metrics_endpoint():
    """Prometheus metrics endpoint"""
    return metrics.registry.collect()

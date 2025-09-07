from flask import Flask, request, jsonify
from app.services.pricing_service import LoanPricingService
from app.services.prediction_service import DefaultPredictionService
from app.services.event_publisher import EventPublisher
import uuid
from datetime import datetime
import logging

app = Flask(__name__)
logger = logging.getLogger(__name__)

# Initialize services
pricing_service = LoanPricingService()
prediction_service = DefaultPredictionService()
event_publisher = EventPublisher()

@app.route('/mortgage/apply', methods=['POST'])
def process_mortgage_application():
    """
    Main endpoint for mortgage applications - UPDATED to use new service classes
    """
    try:
        application_data = request.get_json()
        
        # Validate required fields
        required_fields = ['applicant_income', 'loan_amount', 'credit_score', 'property_value']
        missing_fields = [field for field in required_fields if field not in application_data]
        
        if missing_fields:
            return jsonify({
                'error': 'Missing required fields',
                'missing_fields': missing_fields
            }), 400
        
        application_id = str(uuid.uuid4())
        application_data['application_id'] = application_id
        application_data['timestamp'] = datetime.now().isoformat()
        
        logger.info(f"Processing mortgage application {application_id}")
        
        # Step 1: Get loan pricing using new service
        pricing_response = pricing_service.calculate_loan_pricing(application_data)
        if 'error' in pricing_response:
            return jsonify({
                'application_id': application_id,
                'status': 'failed',
                'error': 'Pricing service failed',
                'details': pricing_response
            }), 500
        
        # Step 2: Get default prediction using new service
        # Combine application and pricing data for prediction
        prediction_input = {**application_data, **pricing_response}
        prediction_response = prediction_service.predict_default_risk(prediction_input)
        if 'error' in prediction_response:
            return jsonify({
                'application_id': application_id,
                'status': 'failed',
                'error': 'Prediction service failed',
                'details': prediction_response
            }), 500
        
        # Step 3: Make final decision
        final_decision = make_final_decision(application_data, pricing_response, prediction_response)
        
        # Step 4: Publish final application event
        event_publisher.publish_event(
            event_type='Mortgage Application Completed',
            detail={
                'application_id': application_id,
                'final_decision': final_decision,
                'pricing': pricing_response,
                'prediction': prediction_response
            }
        )
        
        return jsonify({
            'application_id': application_id,
            'status': 'completed',
            'pricing': pricing_response,
            'prediction': prediction_response,
            'final_decision': final_decision
        })
        
    except Exception as e:
        logger.error(f"Error processing mortgage application: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500

def make_final_decision(application_data, pricing_data, prediction_data):
    """Make final loan approval decision based on all factors - UNCHANGED"""
    # Business rules for loan approval
    max_default_probability = 0.15
    min_credit_score = 600
    max_debt_to_income = 0.43
    
    default_probability = prediction_data.get('default_probability', 1.0)
    credit_score = application_data.get('credit_score', 0)
    
    # Calculate debt-to-income ratio
    monthly_income = application_data.get('applicant_income', 0) / 12
    monthly_payment = pricing_data.get('monthly_payment', float('inf'))
    debt_to_income = monthly_payment / monthly_income if monthly_income > 0 else float('inf')
    
    # Decision logic
    if (default_probability <= max_default_probability and 
        credit_score >= min_credit_score and 
        debt_to_income <= max_debt_to_income):
        decision = 'approved'
        reason = 'Application meets all approval criteria'
    else:
        decision = 'rejected'
        reasons = []
        if default_probability > max_default_probability:
            reasons.append(f'High default risk: {default_probability:.3f}')
        if credit_score < min_credit_score:
            reasons.append(f'Low credit score: {credit_score}')
        if debt_to_income > max_debt_to_income:
            reasons.append(f'High debt-to-income ratio: {debt_to_income:.3f}')
        reason = '; '.join(reasons)
    
    return {
        'decision': decision,
        'reason': reason,
        'default_probability': default_probability,
        'debt_to_income_ratio': debt_to_income,
        'monthly_payment': monthly_payment
    }

if __name__ == '__main__':
    app.run(debug=True, port=5000)
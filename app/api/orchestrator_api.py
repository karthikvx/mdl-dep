"""
Main Orchestrator Service - Routes mortgage applications through the system
"""

from flask import Flask, request, jsonify
import requests
import os
import boto3
import json
from datetime import datetime
import uuid
import logging

app = Flask(__name__)
logger = logging.getLogger(__name__)

# AWS EventBridge client
eventbridge = boto3.client('eventbridge')

@app.route('/mortgage/apply', methods=['POST'])
def process_mortgage_application():
    """
    Main endpoint for mortgage applications
    Orchestrates the entire process: pricing -> prediction -> decision
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
        
        # Step 1: Get loan pricing
        pricing_response = call_pricing_service(application_data)
        if not pricing_response or 'error' in pricing_response:
            return jsonify({
                'application_id': application_id,
                'status': 'failed',
                'error': 'Pricing service failed',
                'details': pricing_response
            }), 500
        
        # Step 2: Get default prediction
        prediction_response = call_prediction_service(application_data, pricing_response)
        if not prediction_response or 'error' in prediction_response:
            return jsonify({
                'application_id': application_id,
                'status': 'failed',
                'error': 'Prediction service failed',
                'details': prediction_response
            }), 500
        
        # Step 3: Make final decision
        final_decision = make_final_decision(application_data, pricing_response, prediction_response)
        
        # Step 4: Publish event to EventBridge
        publish_application_event(application_id, final_decision)
        
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

def call_pricing_service(application_data):
    """Call the loan pricing microservice"""
    try:
        pricing_url = app.config.get('PRICING_SERVICE_URL', 'http://localhost:5001')
        response = requests.post(
            f"{pricing_url}/pricing/calculate",
            json=application_data,
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Pricing service call failed: {e}")
        return {'error': str(e)}

def call_prediction_service(application_data, pricing_data):
    """Call the default prediction microservice"""
    try:
        prediction_url = app.config.get('PREDICTION_SERVICE_URL', 'http://localhost:5002')
        
        # Combine application and pricing data
        prediction_input = {**application_data, **pricing_data}
        
        response = requests.post(
            f"{prediction_url}/prediction/default-risk",
            json=prediction_input,
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Prediction service call failed: {e}")
        return {'error': str(e)}

def make_final_decision(application_data, pricing_data, prediction_data):
    """Make final loan approval decision based on all factors"""
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

def publish_application_event(application_id, decision_data):
    """Publish mortgage application event to EventBridge"""
    try:
        event_detail = {
            'application_id': application_id,
            'decision': decision_data['decision'],
            'timestamp': datetime.now().isoformat()
        }
        
        eventbridge.put_events(
            Entries=[
                {
                    'Source': 'mortgage.application',
                    'DetailType': 'Mortgage Decision',
                    'Detail': json.dumps(event_detail),
                    'EventBusName': 'default'
                }
            ]
        )
        logger.info(f"Published event for application {application_id}")
    except Exception as e:
        logger.error(f"Failed to publish event: {e}")

@app.route('/status/<application_id>', methods=['GET'])
def get_application_status(application_id):
    """Get status of a mortgage application"""
    # In a real implementation, this would query a database
    return jsonify({
        'application_id': application_id,
        'status': 'This endpoint would query application status from database'
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)

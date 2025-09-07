"""
Loan Pricing Service - Calculates loan terms and pricing
"""

from flask import Flask, request, jsonify
import joblib
import numpy as np
import pandas as pd
import boto3
import os
from datetime import datetime
import logging

app = Flask(__name__)
logger = logging.getLogger(__name__)

# Global model cache
pricing_model = None
scaler = None

def load_pricing_model():
    """Load the pricing model from S3 or local cache"""
    global pricing_model, scaler
    
    if pricing_model is None:
        try:
            # Try to load from S3 first
            s3_client = boto3.client('s3')
            bucket_name = os.getenv('MODEL_BUCKET', 'mortgage-ml-models')
            model_path = 'models/loan_pricing/latest/'
            
            # Load model
            s3_client.download_file(bucket_name, f'{model_path}model.pkl', 'pricing_model.pkl')
            pricing_model = joblib.load('pricing_model.pkl')
            
            # Load scaler
            s3_client.download_file(bucket_name, f'{model_path}scaler.pkl', 'pricing_scaler.pkl')
            scaler = joblib.load('pricing_scaler.pkl')
            
            logger.info("Pricing model loaded from S3")
        except Exception as e:
            logger.warning(f"Could not load model from S3: {e}")
            # Fallback: create a simple rule-based pricing model
            pricing_model = 'rule_based'
            scaler = None
            logger.info("Using rule-based pricing model")

@app.route('/pricing/calculate', methods=['POST'])
def calculate_loan_pricing():
    """Calculate loan pricing based on application data"""
    try:
        application_data = request.get_json()
        
        # Validate required fields
        required_fields = ['loan_amount', 'credit_score', 'applicant_income', 'property_value']
        missing_fields = [field for field in required_fields if field not in application_data]
        
        if missing_fields:
            return jsonify({
                'error': 'Missing required fields',
                'missing_fields': missing_fields
            }), 400
        
        # Load model if not already loaded
        load_pricing_model()
        
        # Calculate pricing
        pricing_result = calculate_pricing(application_data)
        
        return jsonify(pricing_result)
        
    except Exception as e:
        logger.error(f"Error calculating loan pricing: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Pricing calculation failed',
            'message': str(e)
        }), 500

def calculate_pricing(data):
    """Calculate loan pricing using ML model or business rules"""
    loan_amount = float(data['loan_amount'])
    credit_score = int(data['credit_score'])
    income = float(data['applicant_income'])
    property_value = float(data['property_value'])
    
    if pricing_model == 'rule_based':
        # Rule-based pricing
        base_rate = 3.5  # Base interest rate
        
        # Adjust rate based on credit score
        if credit_score >= 750:
            rate_adjustment = -0.5
        elif credit_score >= 700:
            rate_adjustment = 0.0
        elif credit_score >= 650:
            rate_adjustment = 0.75
        else:
            rate_adjustment = 1.5
        
        # Adjust rate based on LTV ratio
        ltv_ratio = loan_amount / property_value
        if ltv_ratio > 0.8:
            rate_adjustment += 0.5
        elif ltv_ratio > 0.9:
            rate_adjustment += 1.0
        
        interest_rate = base_rate + rate_adjustment
        
        # Calculate monthly payment (30-year fixed)
        monthly_rate = interest_rate / 100 / 12
        num_payments = 30 * 12
        
        if monthly_rate > 0:
            monthly_payment = loan_amount * (monthly_rate * (1 + monthly_rate) ** num_payments) / ((1 + monthly_rate) ** num_payments - 1)
        else:
            monthly_payment = loan_amount / num_payments
        
    else:
        # ML model prediction
        features = prepare_features(data)
        scaled_features = scaler.transform([features]) if scaler else [features]
        
        predictions = pricing_model.predict(scaled_features)
        interest_rate = predictions[0]
        
        # Calculate monthly payment
        monthly_rate = interest_rate / 100 / 12
        num_payments = 30 * 12
        monthly_payment = loan_amount * (monthly_rate * (1 + monthly_rate) ** num_payments) / ((1 + monthly_rate) ** num_payments - 1)
    
    return {
        'interest_rate': round(interest_rate, 3),
        'monthly_payment': round(monthly_payment, 2),
        'loan_amount': loan_amount,
        'loan_to_value_ratio': round(loan_amount / property_value, 3),
        'debt_to_income_ratio': round((monthly_payment * 12) / income, 3),
        'model_type': 'ml' if pricing_model != 'rule_based' else 'rule_based',
        'calculation_timestamp': datetime.now().isoformat()
    }

def prepare_features(data):
    """Prepare features for ML model prediction"""
    return [
        float(data['loan_amount']),
        int(data['credit_score']),
        float(data['applicant_income']),
        float(data['property_value']),
        float(data['loan_amount']) / float(data['property_value'])  # LTV ratio
    ]

@app.route('/pricing/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    model_status = 'loaded' if pricing_model is not None else 'not_loaded'
    return jsonify({
        'status': 'healthy',
        'model_status': model_status,
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    app.run(debug=True, port=5001)

"""
Default Prediction Service - Predicts loan default probability
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
prediction_model = None
scaler = None

def load_prediction_model():
    """Load the default prediction model from S3 or local cache"""
    global prediction_model, scaler
    
    if prediction_model is None:
        try:
            # Try to load from S3 first
            s3_client = boto3.client('s3')
            bucket_name = os.getenv('MODEL_BUCKET', 'mortgage-ml-models')
            model_path = 'models/default_prediction/latest/'
            
            # Load model
            s3_client.download_file(bucket_name, f'{model_path}model.pkl', 'prediction_model.pkl')
            prediction_model = joblib.load('prediction_model.pkl')
            
            # Load scaler
            s3_client.download_file(bucket_name, f'{model_path}scaler.pkl', 'prediction_scaler.pkl')
            scaler = joblib.load('prediction_scaler.pkl')
            
            logger.info("Prediction model loaded from S3")
        except Exception as e:
            logger.warning(f"Could not load model from S3: {e}")
            # Fallback: create a simple rule-based model
            prediction_model = 'rule_based'
            scaler = None
            logger.info("Using rule-based prediction model")

@app.route('/prediction/default-risk', methods=['POST'])
def predict_default_risk():
    """Predict default probability for a loan application"""
    try:
        application_data = request.get_json()
        
        # Validate required fields
        required_fields = ['credit_score', 'debt_to_income_ratio', 'loan_to_value_ratio']
        missing_fields = [field for field in required_fields if field not in application_data]
        
        if missing_fields:
            return jsonify({
                'error': 'Missing required fields',
                'missing_fields': missing_fields
            }), 400
        
        # Load model if not already loaded
        load_prediction_model()
        
        # Make prediction
        prediction_result = predict_default(application_data)
        
        return jsonify(prediction_result)
        
    except Exception as e:
        logger.error(f"Error predicting default risk: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Default prediction failed',
            'message': str(e)
        }), 500

def predict_default(data):
    """Predict default probability using ML model or business rules"""
    credit_score = int(data['credit_score'])
    dti_ratio = float(data.get('debt_to_income_ratio', 0))
    ltv_ratio = float(data.get('loan_to_value_ratio', 0))
    
    if prediction_model == 'rule_based':
        # Rule-based default prediction
        default_probability = 0.05  # Base probability
        
        # Adjust based on credit score
        if credit_score < 600:
            default_probability += 0.15
        elif credit_score < 650:
            default_probability += 0.08
        elif credit_score < 700:
            default_probability += 0.03
        
        # Adjust based on debt-to-income ratio
        if dti_ratio > 0.43:
            default_probability += 0.10
        elif dti_ratio > 0.36:
            default_probability += 0.05
        
        # Adjust based on loan-to-value ratio
        if ltv_ratio > 0.95:
            default_probability += 0.08
        elif ltv_ratio > 0.80:
            default_probability += 0.03
        
        # Cap at reasonable maximum
        default_probability = min(default_probability, 0.95)
        
        risk_category = categorize_risk(default_probability)
        
    else:
        # ML model prediction
        features = prepare_prediction_features(data)
        scaled_features = scaler.transform([features]) if scaler else [features]
        
        # Get probability for positive class (default)
        probabilities = prediction_model.predict_proba(scaled_features)
        default_probability = probabilities[0][1]  # Probability of default (class 1)
        
        risk_category = categorize_risk(default_probability)
    
    return {
        'default_probability': round(default_probability, 4),
        'risk_category': risk_category,
        'credit_score': credit_score,
        'debt_to_income_ratio': dti_ratio,
        'loan_to_value_ratio': ltv_ratio,
        'model_type': 'ml' if prediction_model != 'rule_based' else 'rule_based',
        'prediction_timestamp': datetime.now().isoformat()
    }

def prepare_prediction_features(data):
    """Prepare features for ML model prediction"""
    return [
        int(data['credit_score']),
        float(data.get('debt_to_income_ratio', 0)),
        float(data.get('loan_to_value_ratio', 0)),
        float(data.get('applicant_income', 50000)),
        float(data.get('loan_amount', 200000))
    ]

def categorize_risk(probability):
    """Categorize risk based on default probability"""
    if probability < 0.05:
        return 'low'
    elif probability < 0.15:
        return 'medium'
    elif probability < 0.30:
        return 'high'
    else:
        return 'very_high'

@app.route('/prediction/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    model_status = 'loaded' if prediction_model is not None else 'not_loaded'
    return jsonify({
        'status': 'healthy',
        'model_status': model_status,
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    app.run(debug=True, port=5002)
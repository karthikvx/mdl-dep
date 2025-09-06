prediction_app = Flask(__name__)
prediction_service = DefaultPredictionService()

@prediction_app.route('/health')
def health_check_pred():
    return jsonify({"status": "healthy", "service": "default-prediction"})

@prediction_app.route('/metrics')
def metrics_pred():
    return generate_latest()

@prediction_app.route('/predict', methods=['POST'])
def predict_default():
    """HTTP endpoint for predicting default risk"""
    try:
        data = request.get_json()
        loan_app = LoanApplication(**data)
        
        result = prediction_service.predict_default_risk(loan_app)
        
        # Publish result event
        prediction_service.event_publisher.publish_event(
            source='default-prediction-service',
            detail_type='RiskResult',
            detail=asdict(result)
        )
        
        return jsonify(asdict(result))
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

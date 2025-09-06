pricing_app = Flask(__name__)
pricing_service = LoanPricingService()

@pricing_app.route('/health')
def health_check():
    return jsonify({"status": "healthy", "service": "loan-pricing"})

@pricing_app.route('/metrics')
def metrics():
    return generate_latest()

@pricing_app.route('/process', methods=['POST'])
def process_loan_pricing():
    """HTTP endpoint for processing loan pricing"""
    try:
        data = request.get_json()
        loan_app = LoanApplication(**data)
        
        result = pricing_service.process_pricing(loan_app)
        
        # Publish result event
        pricing_service.event_publisher.publish_event(
            source='loan-pricing-service',
            detail_type='PricingResult',
            detail=asdict(result)
        )
        
        return jsonify(asdict(result))
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

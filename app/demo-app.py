
def create_sample_loan_application():
    """Create a sample loan application for testing"""
    return LoanApplication(
        application_id=str(uuid.uuid4()),
        loan_amount=350000.0,
        credit_score=720,
        debt_to_income_ratio=0.35,
        loan_term=30,
        property_value=450000.0,
        down_payment=100000.0,
        employment_years=5,
        annual_income=85000.0
    )

def test_services():
    """Test all services with sample data"""
    sample_app = create_sample_loan_application()
    
    print("Testing Loan Pricing Service...")
    pricing_service = LoanPricingService()
    pricing_result = pricing_service.process_pricing(sample_app)
    print(f"Pricing Result: {pricing_result}")
    
    print("\nTesting Default Prediction Service...")
    prediction_service = DefaultPredictionService()
    risk_result = prediction_service.predict_default_risk(sample_app)
    print(f"Risk Result: {risk_result}")
    
    print("\nTesting Event Publishing...")
    publisher = EventPublisher()
    publisher.publish_event(
        source='test-application',
        detail_type='TestEvent',
        detail=asdict(sample_app)
    )
    
    return sample_app

if __name__ == "__main__":
    # Run test
    sample_app = test_services()
    
    # Start the main orchestrator service
    print(f"\nStarting Mortgage Application Orchestrator on port 5002...")
    main_app.run(host='0.0.0.0', port=5002, debug=True)
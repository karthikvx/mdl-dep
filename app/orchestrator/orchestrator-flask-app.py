main_app = Flask(__name__)
orchestrator = MortgageApplicationOrchestrator()

@main_app.route('/health')
def health_check_main():
    return jsonify({"status": "healthy", "service": "mortgage-application-orchestrator"})

@main_app.route('/submit-application', methods=['POST'])
def submit_application():
    """Submit a new loan application"""
    try:
        data = request.get_json()
        
        # Generate application ID if not provided
        if 'application_id' not in data:
            data['application_id'] = str(uuid.uuid4())
        
        loan_app = LoanApplication(**data)
        application_id = orchestrator.submit_loan_application(loan_app)
        
        return jsonify({
            "application_id": application_id,
            "status": "submitted",
            "message": "Application submitted for processing"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@main_app.route('/application-status/<application_id>')
def get_status(application_id):
    """Get status of loan application"""
    result = orchestrator.get_application_status(application_id)
    return jsonify(result)

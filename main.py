import os
import sys
import logging
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mortgage_app.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def import_service_app(service_type):
    """
    Dynamically import the correct Flask application based on service type
    """
    try:
        if service_type == 'orchestrator':
            from app.api.orchestrator import app as orchestrator_app
            return orchestrator_app
        
        elif service_type == 'pricing':
            from app.api.loan_pricing import app as pricing_app
            return pricing_app
        
        elif service_type == 'prediction':
            from app.api.default_prediction import app as prediction_app
            return prediction_app
        
        elif service_type == 'model_training':
            from app.api.model_training import app as training_app
            return training_app
        
        elif service_type == 'dashboard':
            from app.api.model_dashboard import dashboard_bp
            from flask import Flask
            app = Flask(__name__)
            app.register_blueprint(dashboard_bp)
            return app
        
        else:
            raise ValueError(f"Unknown service type: {service_type}")
    
    except ImportError as e:
        logger.error(f"Failed to import service '{service_type}': {e}")
        logger.info("Available service types: orchestrator, pricing, prediction, model_training, dashboard")
        sys.exit(1)

def validate_environment():
    """
    Validate required environment variables and configurations
    """
    required_env_vars = [
        'AWS_REGION',
        'SERVICE_TYPE'
    ]
    
    missing_vars = []
    for var in required_env_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        logger.info("Please set the following environment variables:")
        logger.info("  AWS_REGION: AWS region (e.g., us-east-1)")
        logger.info("  SERVICE_TYPE: orchestrator|pricing|prediction|model_training|dashboard")
        logger.info("  PORT: Port number (optional, defaults to 5000)")
        sys.exit(1)
    
    # Validate service type
    valid_services = ['orchestrator', 'pricing', 'prediction', 'model_training', 'dashboard']
    service_type = os.getenv('SERVICE_TYPE')
    if service_type not in valid_services:
        logger.error(f"Invalid SERVICE_TYPE: {service_type}")
        logger.info(f"Valid service types: {', '.join(valid_services)}")
        sys.exit(1)

def setup_health_checks(app):
    """
    Add health check endpoints to any Flask app
    """
    @app.route('/health')
    def health_check():
        return {
            'status': 'healthy',
            'service': os.getenv('SERVICE_TYPE', 'unknown'),
            'version': os.getenv('APP_VERSION', '1.0.0'),
            'timestamp': str(os.times())
        }
    
    @app.route('/ready')
    def readiness_check():
        # Add any readiness checks here (DB connections, etc.)
        return {
            'status': 'ready',
            'service': os.getenv('SERVICE_TYPE', 'unknown')
        }

def main():
    """
    Main application entry point
    """
    try:
        # Validate environment
        validate_environment()
        
        # Get configuration
        service_type = os.getenv('SERVICE_TYPE')
        port = int(os.getenv('PORT', 5000))
        debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
        host = os.getenv('HOST', '0.0.0.0')
        
        logger.info(f"Starting {service_type} service on {host}:{port}")
        logger.info(f"Debug mode: {debug}")
        logger.info(f"AWS Region: {os.getenv('AWS_REGION')}")
        
        # Import and configure the appropriate Flask app
        app = import_service_app(service_type)
        
        # Add health checks
        setup_health_checks(app)
        
        # Configure Flask app
        app.config['DEBUG'] = debug
        app.config['SERVICE_TYPE'] = service_type
        app.config['AWS_REGION'] = os.getenv('AWS_REGION')
        
        # Additional configuration based on service type
        if service_type == 'orchestrator':
            app.config['PRICING_SERVICE_URL'] = os.getenv('PRICING_SERVICE_URL', 'http://localhost:5001')
            app.config['PREDICTION_SERVICE_URL'] = os.getenv('PREDICTION_SERVICE_URL', 'http://localhost:5002')
        
        # Start the application
        logger.info(f"Service {service_type} started successfully")
        app.run(host=host, port=port, debug=debug)
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()

# Alternative entry points for different services (for Docker/Kubernetes)
def run_orchestrator():
    """Entry point for orchestrator service"""
    os.environ['SERVICE_TYPE'] = 'orchestrator'
    main()

def run_pricing():
    """Entry point for pricing service"""
    os.environ['SERVICE_TYPE'] = 'pricing'
    main()

def run_prediction():
    """Entry point for prediction service"""
    os.environ['SERVICE_TYPE'] = 'prediction'
    main()

def run_model_training():
    """Entry point for model training service"""
    os.environ['SERVICE_TYPE'] = 'model_training'
    main()

def run_dashboard():
    """Entry point for dashboard service"""
    os.environ['SERVICE_TYPE'] = 'dashboard'
    main()
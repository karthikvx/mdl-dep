"""
Model Training API - Connects the enhanced model training to web interface
"""

from flask import Flask, request, jsonify
from app.services.enhanced_model_service import EnhancedModelService
from app.services.event_publisher import EventPublisher
import logging

app = Flask(__name__)
logger = logging.getLogger(__name__)

model_service = EnhancedModelService()
event_publisher = EventPublisher()

@app.route('/training/start', methods=['POST'])
def start_model_training():
    """Start model training process"""
    try:
        training_config = request.get_json()
        
        # Validate required parameters
        required_fields = ['model_type', 'data_path']
        missing_fields = [field for field in required_fields if field not in training_config]
        
        if missing_fields:
            return jsonify({
                'error': 'Missing required fields',
                'missing_fields': missing_fields
            }), 400
        
        # Start training
        model_version = model_service.train_enhanced_model(
            model_type=training_config['model_type'],
            data_path=training_config['data_path'],
            hyperparameters=training_config.get('hyperparameters')
        )
        
        # Publish training event
        event_publisher.publish_event(
            event_type='Model Training Started',
            detail={
                'model_version': model_version.version,
                'model_type': model_version.model_type,
                'training_config': training_config
            }
        )
        
        return jsonify({
            'status': 'training_started',
            'model_version': model_version.version,
            'model_type': model_version.model_type,
            'metrics': {
                'accuracy': model_version.metrics.accuracy,
                'training_time': model_version.metrics.training_time
            }
        })
        
    except Exception as e:
        logger.error(f"Training start failed: {e}")
        return jsonify({
            'error': 'Training failed to start',
            'message': str(e)
        }), 500

@app.route('/training/deploy', methods=['POST'])
def deploy_model():
    """Deploy model with A/B testing"""
    try:
        deploy_config = request.get_json()
        
        model_version = deploy_config.get('model_version')
        traffic_percentage = deploy_config.get('traffic_percentage', 10.0)
        
        if not model_version:
            return jsonify({'error': 'model_version required'}), 400
        
        # Get model version object
        model_info = model_service._get_model_info(model_version)
        model_version_obj = model_service._create_model_version_from_info(model_info)
        
        # Deploy with A/B testing
        experiment_id = model_service.deploy_model_with_ab_testing(
            model_version_obj,
            traffic_percentage=traffic_percentage
        )
        
        return jsonify({
            'status': 'deployed_for_testing',
            'experiment_id': experiment_id,
            'traffic_percentage': traffic_percentage
        })
        
    except Exception as e:
        logger.error(f"Model deployment failed: {e}")
        return jsonify({
            'error': 'Deployment failed',
            'message': str(e)
        }), 500

@app.route('/training/experiments/<experiment_id>/analyze', methods=['GET'])
def analyze_experiment(experiment_id):
    """Analyze A/B test results"""
    try:
        analysis = model_service.analyze_experiment_results(experiment_id)
        return jsonify(analysis)
    except Exception as e:
        logger.error(f"Experiment analysis failed: {e}")
        return jsonify({
            'error': 'Analysis failed',
            'message': str(e)
        }), 500

@app.route('/training/models/<model_version>/promote', methods=['POST'])
def promote_model(model_version):
    """Promote model to production"""
    try:
        promote_config = request.get_json() or {}
        experiment_id = promote_config.get('experiment_id')
        
        model_service.promote_model_to_production(model_version, experiment_id)
        
        return jsonify({
            'status': 'promoted',
            'model_version': model_version
        })
        
    except Exception as e:
        logger.error(f"Model promotion failed: {e}")
        return jsonify({
            'error': 'Promotion failed',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True, port=5003)

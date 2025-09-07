from flask import Flask, request, jsonify
from app.services.model_training_service import ModelTrainingService
import logging

logger = logging.getLogger(__name__)

training_app = Flask(__name__)
training_service = ModelTrainingService()

@training_app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'service': 'model-training-service'
    })

@training_app.route('/train-model', methods=['POST'])
def train_model():
    """Trigger model training pipeline"""
    try:
        logger.info("Starting model training pipeline...")
        result = training_service.train_and_deploy()
        
        if result['success']:
            return jsonify({
                'status': 'success',
                'model_version': result['model_version'],
                'metrics': result['metrics']
            })
        else:
            return jsonify({
                'status': 'error',
                'error': result['error']
            }), 500
            
    except Exception as e:
        logger.error(f"Training API error: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@training_app.route('/model-status')
def model_status():
    """Get current model information"""
    try:
        metadata = training_service.load_model_metadata()
        if metadata:
            return jsonify({
                'status': 'available',
                'model_version': metadata.get('model_version'),
                'training_timestamp': metadata.get('training_timestamp'),
                'performance_metrics': metadata.get('performance_metrics'),
                's3_paths': metadata.get('s3_paths')
            })
        else:
            return jsonify({
                'status': 'no_model',
                'message': 'No trained model found'
            })
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

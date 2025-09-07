from flask import Blueprint, jsonify, request
from app.services.enhanced_model_service import EnhancedModelService

dashboard_bp = Blueprint('model_dashboard', __name__)
model_service = EnhancedModelService()

@dashboard_bp.route('/dashboard/models', methods=['GET'])
def get_model_overview():
    """Get overview of all models and their status"""
    model_types = ['default_prediction', 'loan_pricing']
    overview = {}
    
    for model_type in model_types:
        models = model_service._get_models_by_type(model_type)
        overview[model_type] = {
            'active_version': model_service._get_current_active_version(model_type),
            'total_versions': len(models),
            'models': models
        }
    
    return jsonify(overview)

@dashboard_bp.route('/dashboard/experiments', methods=['GET'])
def get_active_experiments():
    """Get all active A/B test experiments"""
    experiments = model_service._get_all_active_experiments()
    return jsonify(experiments)

@dashboard_bp.route('/dashboard/performance/<model_version>', methods=['GET'])
def get_model_performance(model_version):
    """Get performance metrics for a specific model version"""
    days = request.args.get('days', 7, type=int)
    performance_data = model_service._get_performance_history(model_version, days)
    return jsonify(performance_data)

@dashboard_bp.route('/dashboard/lineage/<model_version>', methods=['GET'])
def get_model_lineage(model_version):
    """Get complete model lineage"""
    lineage = model_service.get_model_lineage(model_version)
    return jsonify(lineage)
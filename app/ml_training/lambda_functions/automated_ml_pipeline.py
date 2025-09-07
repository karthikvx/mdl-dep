
import json
import boto3
from datetime import datetime, timedelta

def lambda_handler(event, context):
    """
    Automated ML pipeline orchestrator
    Triggers: CloudWatch Events (scheduled), EventBridge (data updates)
    """
    
    pipeline_type = event.get('pipeline_type', 'scheduled_training')
    model_service = EnhancedModelService()
    
    try:
        if pipeline_type == 'scheduled_training':
            # Weekly model retraining
            results = handle_scheduled_training(model_service, event)
            
        elif pipeline_type == 'performance_triggered':
            # Performance degradation triggered retraining
            results = handle_performance_triggered_training(model_service, event)
            
        elif pipeline_type == 'data_drift_triggered':
            # Data drift triggered retraining
            results = handle_drift_triggered_training(model_service, event)
            
        elif pipeline_type == 'experiment_analysis':
            # Automated A/B test analysis
            results = handle_experiment_analysis(model_service, event)
            
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Pipeline executed successfully',
                'results': results
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'pipeline_type': pipeline_type
            })
        }

def handle_scheduled_training(model_service, event):
    """Handle scheduled model retraining"""
    results = []
    
    model_types = ['default_prediction', 'loan_pricing']
    
    for model_type in model_types:
        # Train new model
        new_model = model_service.train_enhanced_model(
            model_type=model_type,
            data_path=f's3://mortgage-data/training/{model_type}/latest/',
            hyperparameters=event.get('hyperparameters', {})
        )
        
        # Validate model
        if model_service.automated_model_validation(new_model.version):
            # Start A/B test with 10% traffic
            experiment_id = model_service.deploy_model_with_ab_testing(
                new_model, 
                traffic_percentage=10.0,
                experiment_name=f"scheduled_training_{model_type}_{datetime.now().strftime('%Y%m%d')}"
            )
            
            results.append({
                'model_type': model_type,
                'model_version': new_model.version,
                'experiment_id': experiment_id,
                'status': 'deployed_for_testing'
            })
        else:
            results.append({
                'model_type': model_type,
                'model_version': new_model.version,
                'status': 'validation_failed'
            })
    
    return results

def handle_experiment_analysis(model_service, event):
    """Analyze running A/B tests and make promotion decisions"""
    experiment_id = event.get('experiment_id')
    if not experiment_id:
        return {'error': 'No experiment_id provided'}
    
    # Analyze experiment results
    analysis = model_service.analyze_experiment_results(experiment_id)
    
    # Auto-promote if conditions are met
    if (analysis['statistical_significance']['p_value'] < 0.05 and 
        analysis['improvement']['performance'] > 0.02 and
        analysis['duration_days'] >= 7):
        
        model_service.promote_model_to_production(
            analysis['test_performance']['model_version'],
            experiment_id
        )
        
        return {
            'experiment_id': experiment_id,
            'action': 'promoted',
            'analysis': analysis
        }
    
    return {
        'experiment_id': experiment_id,
        'action': 'continue_monitoring',
        'analysis': analysis
    }
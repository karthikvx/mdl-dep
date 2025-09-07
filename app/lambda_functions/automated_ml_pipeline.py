"""
Complete Automated ML Pipeline that connects all services
This handles the full ML lifecycle automation
"""

import json
import boto3
from datetime import datetime, timedelta
from app.services.enhanced_model_service import EnhancedModelService
from app.services.event_publisher import EventPublisher
import logging

logger = logging.getLogger(__name__)

def lambda_handler(event, context):
    """
    Main Lambda handler for ML pipeline automation
    Connects: Model Training -> A/B Testing -> Performance Monitoring -> Auto-promotion
    """
    
    pipeline_type = event.get('pipeline_type', 'scheduled_training')
    model_service = EnhancedModelService()
    event_publisher = EventPublisher()
    
    try:
        if pipeline_type == 'scheduled_training':
            results = handle_scheduled_training(model_service, event_publisher, event)
            
        elif pipeline_type == 'performance_triggered':
            results = handle_performance_triggered_training(model_service, event_publisher, event)
            
        elif pipeline_type == 'data_drift_triggered':
            results = handle_drift_triggered_training(model_service, event_publisher, event)
            
        elif pipeline_type == 'experiment_analysis':
            results = handle_experiment_analysis(model_service, event_publisher, event)
            
        elif pipeline_type == 'model_monitoring':
            results = handle_model_monitoring(model_service, event_publisher, event)
            
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'ML Pipeline executed successfully',
                'pipeline_type': pipeline_type,
                'results': results
            })
        }
        
    except Exception as e:
        logger.error(f"ML Pipeline failed: {e}", exc_info=True)
        
        # Publish failure event
        event_publisher.publish_event(
            event_type='ML Pipeline Failed',
            detail={
                'pipeline_type': pipeline_type,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            },
            source='mortgage.ml.pipeline'
        )
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'pipeline_type': pipeline_type
            })
        }

def handle_scheduled_training(model_service, event_publisher, event):
    """Handle scheduled model retraining - connects to training service"""
    results = []
    model_types = ['default_prediction', 'loan_pricing']
    
    for model_type in model_types:
        try:
            # Step 1: Train new model
            logger.info(f"Starting scheduled training for {model_type}")
            
            new_model = model_service.train_enhanced_model(
                model_type=model_type,
                data_path=f's3://mortgage-data/training/{model_type}/latest/',
                hyperparameters=event.get('hyperparameters', {})
            )
            
            # Step 2: Validate model
            validation_passed = model_service.automated_model_validation(new_model.version)
            
            if validation_passed:
                # Step 3: Deploy for A/B testing
                experiment_id = model_service.deploy_model_with_ab_testing(
                    new_model, 
                    traffic_percentage=10.0,
                    experiment_name=f"scheduled_training_{model_type}_{datetime.now().strftime('%Y%m%d')}"
                )
                
                # Step 4: Publish success event
                event_publisher.publish_event(
                    event_type='Model Deployed for Testing',
                    detail={
                        'model_type': model_type,
                        'model_version': new_model.version,
                        'experiment_id': experiment_id,
                        'metrics': {
                            'accuracy': new_model.metrics.accuracy,
                            'training_time': new_model.metrics.training_time
                        }
                    },
                    source='mortgage.ml.training'
                )
                
                results.append({
                    'model_type': model_type,
                    'model_version': new_model.version,
                    'experiment_id': experiment_id,
                    'status': 'deployed_for_testing',
                    'metrics': new_model.metrics.__dict__
                })
                
            else:
                # Publish validation failure event
                event_publisher.publish_event(
                    event_type='Model Validation Failed',
                    detail={
                        'model_type': model_type,
                        'model_version': new_model.version,
                        'reason': 'Failed automated validation checks'
                    },
                    source='mortgage.ml.training'
                )
                
                results.append({
                    'model_type': model_type,
                    'model_version': new_model.version,
                    'status': 'validation_failed'
                })
                
        except Exception as e:
            logger.error(f"Training failed for {model_type}: {e}")
            results.append({
                'model_type': model_type,
                'status': 'training_failed',
                'error': str(e)
            })
    
    return results

def handle_experiment_analysis(model_service, event_publisher, event):
    """Analyze running A/B tests and make auto-promotion decisions"""
    experiment_id = event.get('experiment_id')
    if not experiment_id:
        # Get all active experiments
        active_experiments = model_service._get_all_active_experiments()
        experiment_id = active_experiments[0]['experiment_id'] if active_experiments else None
    
    if not experiment_id:
        return {'message': 'No active experiments found'}
    
    try:
        # Analyze experiment results
        analysis = model_service.analyze_experiment_results(experiment_id)
        
        # Auto-promotion logic
        should_promote = (
            analysis['statistical_significance']['p_value'] < 0.05 and 
            analysis['improvement']['performance'] > 0.02 and
            analysis['duration_days'] >= 7
        )
        
        if should_promote:
            # Promote model to production
            model_service.promote_model_to_production(
                analysis['test_performance']['model_version'],
                experiment_id
            )
            
            # Publish promotion event
            event_publisher.publish_event(
                event_type='Model Promoted to Production',
                detail={
                    'experiment_id': experiment_id,
                    'model_version': analysis['test_performance']['model_version'],
                    'improvement': analysis['improvement'],
                    'statistical_significance': analysis['statistical_significance']
                },
                source='mortgage.ml.promotion'
            )
            
            return {
                'experiment_id': experiment_id,
                'action': 'promoted',
                'analysis': analysis
            }
        else:
            # Continue monitoring
            event_publisher.publish_event(
                event_type='Experiment Continue Monitoring',
                detail={
                    'experiment_id': experiment_id,
                    'analysis': analysis,
                    'reason': 'Promotion criteria not met'
                },
                source='mortgage.ml.monitoring'
            )
            
            return {
                'experiment_id': experiment_id,
                'action': 'continue_monitoring',
                'analysis': analysis
            }
            
    except Exception as e:
        logger.error(f"Experiment analysis failed: {e}")
        raise

def handle_model_monitoring(model_service, event_publisher, event):
    """Monitor model performance and detect issues"""
    try:
        monitoring_results = []
        
        # Get all active models
        active_models = model_service._get_active_models()
        
        for model_info in active_models:
            model_version = model_info['version']
            model_type = model_info['model_type']
            
            # Get recent performance data
            performance_data = model_service._get_performance_history(model_version, days=1)
            
            if performance_data:
                # Analyze performance trends
                alerts = analyze_performance_trends(performance_data)
                
                if alerts:
                    # Publish performance alert
                    event_publisher.publish_event(
                        event_type='Model Performance Alert',
                        detail={
                            'model_version': model_version,
                            'model_type': model_type,
                            'alerts': alerts,
                            'performance_data': performance_data
                        },
                        source='mortgage.ml.monitoring'
                    )
                    
                    # Trigger retraining if severe degradation
                    if any(alert['severity'] == 'critical' for alert in alerts):
                        trigger_emergency_retraining(model_service, model_type, event_publisher)
                
                monitoring_results.append({
                    'model_version': model_version,
                    'model_type': model_type,
                    'alerts': alerts,
                    'status': 'monitored'
                })
        
        return monitoring_results
        
    except Exception as e:
        logger.error(f"Model monitoring failed: {e}")
        raise

def analyze_performance_trends(performance_data):
    """Analyze performance data and identify alerts"""
    alerts = []
    
    if not performance_data:
        return alerts
    
    # Calculate recent averages
    recent_accuracy = sum(d.get('prediction_accuracy', 0) for d in performance_data[-10:]) / min(len(performance_data), 10)
    recent_drift = sum(d.get('feature_drift', 0) for d in performance_data[-10:]) / min(len(performance_data), 10)
    
    # Check thresholds
    if recent_accuracy < 0.85:
        alerts.append({
            'type': 'low_accuracy',
            'severity': 'critical' if recent_accuracy < 0.80 else 'warning',
            'value': recent_accuracy,
            'threshold': 0.85
        })
    
    if recent_drift > 2.0:
        alerts.append({
            'type': 'feature_drift',
            'severity': 'critical' if recent_drift > 3.0 else 'warning',
            'value': recent_drift,
            'threshold': 2.0
        })
    
    return alerts

def trigger_emergency_retraining(model_service, model_type, event_publisher):
    """Trigger emergency retraining for degraded model"""
    try:
        # Publish emergency retraining event
        event_publisher.publish_event(
            event_type='Emergency Retraining Triggered',
            detail={
                'model_type': model_type,
                'reason': 'Critical performance degradation detected'
            },
            source='mortgage.ml.emergency'
        )
        
        # Trigger Lambda for emergency training
        lambda_client = boto3.client('lambda')
        lambda_client.invoke(
            FunctionName='automated-ml-pipeline',
            InvocationType='Event',
            Payload=json.dumps({
                'pipeline_type': 'performance_triggered',
                'model_type': model_type,
                'priority': 'emergency'
            })
        )
        
    except Exception as e:
        logger.error(f"Failed to trigger emergency retraining: {e}")

def handle_performance_triggered_training(model_service, event_publisher, event):
    """Handle performance-triggered retraining"""
    model_type = event.get('model_type')
    priority = event.get('priority', 'normal')
    
    if not model_type:
        raise ValueError("model_type required for performance-triggered training")
    
    try:
        # Use more recent data for emergency retraining
        data_path = f's3://mortgage-data/training/{model_type}/latest/'
        if priority == 'emergency':
            data_path = f's3://mortgage-data/training/{model_type}/realtime/'
        
        # Train new model with optimized parameters
        hyperparameters = event.get('hyperparameters', {})
        if priority == 'emergency':
            # Use faster training parameters for emergency
            hyperparameters.update({
                'n_estimators': 50,  # Reduced for speed
                'max_depth': 10
            })
        
        new_model = model_service.train_enhanced_model(
            model_type=model_type,
            data_path=data_path,
            hyperparameters=hyperparameters
        )
        
        # Fast validation for emergency
        validation_passed = model_service.automated_model_validation(new_model.version)
        
        if validation_passed:
            # Deploy with higher traffic for emergency
            traffic_percentage = 50.0 if priority == 'emergency' else 20.0
            
            experiment_id = model_service.deploy_model_with_ab_testing(
                new_model,
                traffic_percentage=traffic_percentage,
                experiment_name=f"performance_triggered_{model_type}_{priority}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            
            event_publisher.publish_event(
                event_type='Performance Triggered Model Deployed',
                detail={
                    'model_type': model_type,
                    'model_version': new_model.version,
                    'experiment_id': experiment_id,
                    'priority': priority,
                    'traffic_percentage': traffic_percentage
                },
                source='mortgage.ml.performance'
            )
            
            return {
                'model_type': model_type,
                'model_version': new_model.version,
                'experiment_id': experiment_id,
                'status': 'deployed_for_testing',
                'priority': priority
            }
        else:
            raise Exception("Model validation failed for performance-triggered training")
            
    except Exception as e:
        logger.error(f"Performance-triggered training failed: {e}")
        raise
# CloudWatch Events integration
def create_cloudwatch_rules():
    """Create CloudWatch Events rules for ML pipeline automation"""
    events_client = boto3.client('events')
    
    rules = [
        {
            'Name': 'mortgage-ml-scheduled-training',
            'ScheduleExpression': 'rate(7 days)',  # Weekly training
            'Description': 'Trigger weekly model retraining',
            'State': 'ENABLED',
            'Targets': [{
                'Id': '1',
                'Arn': 'arn:aws:lambda:us-east-1:123456789012:function:mortgage-ml-pipeline',
                'Input': json.dumps({
                    'action': 'retrain',
                    'model_type': 'all',
                    'trigger': 'scheduled'
                })
            }]
        },
        {
            'Name': 'mortgage-ml-performance-check',
            'ScheduleExpression': 'rate(1 day)',  # Daily performance monitoring
            'Description': 'Daily model performance evaluation',
            'State': 'ENABLED',
            'Targets': [{
                'Id': '1',
                'Arn': 'arn:aws:lambda:us-east-1:123456789012:function:mortgage-ml-pipeline',
                'Input': json.dumps({
                    'action': 'monitor_performance',
                    'trigger': 'scheduled'
                })
            }]
        },
        {
            'Name': 'mortgage-ml-drift-detection',
            'ScheduleExpression': 'rate(2 hours)',  # Frequent drift monitoring
            'Description': 'Monitor for feature and data drift',
            'State': 'ENABLED',
            'Targets': [{
                'Id': '1',
                'Arn': 'arn:aws:lambda:us-east-1:123456789012:function:mortgage-ml-pipeline',
                'Input': json.dumps({
                    'action': 'detect_drift',
                    'trigger': 'scheduled'
                })
            }]
        }
    ]
    
    # Create CloudWatch Events rules
    for rule in rules:
        try:
            # Create the rule
            events_client.put_rule(
                Name=rule['Name'],
                ScheduleExpression=rule['ScheduleExpression'],
                Description=rule['Description'],
                State=rule['State']
            )
            
            # Add targets to the rule
            events_client.put_targets(
                Rule=rule['Name'],
                Targets=rule['Targets']
            )
            
            logger.info(f"Created CloudWatch Events rule: {rule['Name']}")
            
        except Exception as e:
            logger.error(f"Failed to create CloudWatch rule {rule['Name']}: {str(e)}")
            raise
    
    return rules

def setup_cloudwatch_alarms():
    """Setup CloudWatch alarms for ML pipeline monitoring"""
    cloudwatch = boto3.client('cloudwatch')
    
    alarms = [
        {
            'AlarmName': 'MortgageML-HighErrorRate',
            'ComparisonOperator': 'GreaterThanThreshold',
            'EvaluationPeriods': 2,
            'MetricName': 'Errors',
            'Namespace': 'AWS/Lambda',
            'Period': 300,
            'Statistic': 'Sum',
            'Threshold': 10.0,
            'ActionsEnabled': True,
            'AlarmActions': [
                'arn:aws:sns:us-east-1:123456789012:mortgage-ml-alerts'
            ],
            'AlarmDescription': 'Alert when ML pipeline error rate is high',
            'Dimensions': [
                {
                    'Name': 'FunctionName',
                    'Value': 'mortgage-ml-pipeline'
                }
            ]
        },
        {
            'AlarmName': 'MortgageML-LowAccuracy',
            'ComparisonOperator': 'LessThanThreshold',
            'EvaluationPeriods': 3,
            'MetricName': 'ModelAccuracy',
            'Namespace': 'MortgageML/Performance',
            'Period': 3600,
            'Statistic': 'Average',
            'Threshold': 0.85,
            'ActionsEnabled': True,
            'AlarmActions': [
                'arn:aws:sns:us-east-1:123456789012:mortgage-ml-alerts'
            ],
            'AlarmDescription': 'Alert when model accuracy drops below threshold'
        },
        {
            'AlarmName': 'MortgageML-DataDrift',
            'ComparisonOperator': 'GreaterThanThreshold',
            'EvaluationPeriods': 1,
            'MetricName': 'DataDriftScore',
            'Namespace': 'MortgageML/DataQuality',
            'Period': 3600,
            'Statistic': 'Maximum',
            'Threshold': 0.3,
            'ActionsEnabled': True,
            'AlarmActions': [
                'arn:aws:sns:us-east-1:123456789012:mortgage-ml-alerts'
            ],
            'AlarmDescription': 'Alert when significant data drift is detected'
        }
    ]
    
    for alarm in alarms:
        try:
            cloudwatch.put_metric_alarm(**alarm)
            logger.info(f"Created CloudWatch alarm: {alarm['AlarmName']}")
        except Exception as e:
            logger.error(f"Failed to create alarm {alarm['AlarmName']}: {str(e)}")
            raise
    
    return alarms

def publish_custom_metrics(metrics_data):
    """Publish custom metrics to CloudWatch"""
    cloudwatch = boto3.client('cloudwatch')
    
    try:
        metric_data = []
        for metric_name, value in metrics_data.items():
            metric_data.append({
                'MetricName': metric_name,
                'Value': value,
                'Unit': 'None',
                'Timestamp': datetime.utcnow()
            })
        
        cloudwatch.put_metric_data(
            Namespace='MortgageML/Custom',
            MetricData=metric_data
        )
        
        logger.info(f"Published {len(metric_data)} custom metrics to CloudWatch")
        
    except Exception as e:
        logger.error(f"Failed to publish custom metrics: {str(e)}")
        raise
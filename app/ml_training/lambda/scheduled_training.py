import json
import boto3
import requests
from datetime import datetime

def lambda_handler(event, context):
    """
    AWS Lambda function for scheduled model retraining
    Triggered by CloudWatch Events (e.g., weekly)
    """
    
    try:
        # Get training service endpoint from environment
        import os
        training_service_url = os.environ.get(
            'TRAINING_SERVICE_URL', 
            'http://model-training-service.mortgage-application.svc.cluster.local'
        )
        
        print(f"Starting scheduled training at {datetime.utcnow().isoformat()}")
        
        # Trigger training
        response = requests.post(
            f"{training_service_url}/train-model",
            headers={'Content-Type': 'application/json'},
            timeout=300  # 5 minutes timeout
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"Training completed successfully:")
            print(f"Model version: {result.get('model_version')}")
            print(f"Metrics: {result.get('metrics')}")
            
            # Optionally send notification to SNS
            sns = boto3.client('sns')
            sns.publish(
                TopicArn=os.environ.get('SNS_TOPIC_ARN'),
                Message=f"Model training completed. New version: {result.get('model_version')}",
                Subject="Mortgage ML Model Training Complete"
            )
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Training completed successfully',
                    'model_version': result.get('model_version')
                })
            }
        else:
            print(f"Training failed with status {response.status_code}")
            print(f"Response: {response.text}")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'Training failed',
                    'details': response.text
                })
            }
            
    except Exception as e:
        print(f"Scheduled training error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Lambda execution failed',
                'details': str(e)
            })
        }

import json
import boto3
from decimal import Decimal

def lambda_handler(event, context):
    """
    AWS Lambda function to aggregate pricing and risk results
    Triggered by EventBridge events
    """
    
    dynamodb = boto3.resource('dynamodb')
    results_table = dynamodb.Table('loan-application-results')
    
    try:
        # Parse the incoming event
        detail = event.get('detail', {})
        source = event.get('source', '')
        detail_type = event.get('detail-type', '')
        
        application_id = detail.get('application_id')
        
        if not application_id:
            return {
                'statusCode': 400,
                'body': json.dumps('Missing application_id')
            }
        
        # Convert floats to Decimal for DynamoDB
        def convert_floats(obj):
            if isinstance(obj, float):
                return Decimal(str(obj))
            elif isinstance(obj, dict):
                return {k: convert_floats(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_floats(item) for item in obj]
            return obj
        
        detail_decimal = convert_floats(detail)
        
        # Store the result based on event type
        if detail_type == 'PricingResult':
            # Store pricing result
            results_table.update_item(
                Key={'application_id': application_id},
                UpdateExpression='SET pricing_result = :pr, updated_at = :ua',
                ExpressionAttributeValues={
                    ':pr': detail_decimal,
                    ':ua': detail_decimal['timestamp']
                }
            )
            
        elif detail_type == 'RiskResult':
            # Store risk result
            results_table.update_item(
                Key={'application_id': application_id},
                UpdateExpression='SET risk_result = :rr, updated_at = :ua',
                ExpressionAttributeValues={
                    ':rr': detail_decimal,
                    ':ua': detail_decimal['timestamp']
                }
            )
        
        # Check if we have both results
        response = results_table.get_item(
            Key={'application_id': application_id}
        )
        
        item = response.get('Item', {})
        if 'pricing_result' in item and 'risk_result' in item:
            # Both results available, make final decision
            risk_category = item['risk_result']['risk_category']
            default_prob = float(item['risk_result']['default_probability'])
            
            # Simple decision logic
            if risk_category == 'VERY_HIGH' or default_prob > 0.4:
                final_decision = 'REJECTED'
            elif risk_category == 'HIGH':
                final_decision = 'APPROVED_WITH_CONDITIONS'
            else:
                final_decision = 'APPROVED'
            
            # Update with final decision
            results_table.update_item(
                Key={'application_id': application_id},
                UpdateExpression='SET final_decision = :fd, processing_complete = :pc',
                ExpressionAttributeValues={
                    ':fd': final_decision,
                    ':pc': True
                }
            )
            
            print(f"Processing complete for application {application_id}: {final_decision}")
        
        return {
            'statusCode': 200,
            'body': json.dumps(f'Successfully processed {detail_type} for {application_id}')
        }
        
    except Exception as e:
        print(f"Error processing event: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error: {str(e)}')
        }

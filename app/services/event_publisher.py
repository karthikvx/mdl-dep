"""
Event Publisher Service - Handles EventBridge integration
This connects the orchestrator to AWS EventBridge
"""

import boto3
import json
from datetime import datetime
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class EventPublisher:
    def __init__(self):
        self.eventbridge = boto3.client('eventbridge')
        self.event_bus_name = 'mortgage-application-bus'
    
    def publish_event(self, event_type: str, detail: Dict[Any, Any], source: str = 'mortgage.application'):
        """Publish event to EventBridge"""
        try:
            event_detail = {
                **detail,
                'timestamp': datetime.now().isoformat(),
                'event_id': f"{event_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            }
            
            response = self.eventbridge.put_events(
                Entries=[
                    {
                        'Source': source,
                        'DetailType': event_type,
                        'Detail': json.dumps(event_detail),
                        'EventBusName': self.event_bus_name
                    }
                ]
            )
            
            logger.info(f"Published event {event_type}: {response}")
            return response
            
        except Exception as e:
            logger.error(f"Failed to publish event {event_type}: {e}")
            raise

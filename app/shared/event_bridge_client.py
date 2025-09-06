import boto3
import json
from typing import Dict, Any

class EventPublisher:
    def __init__(self, event_bus_name: str = "mortgage-application-bus"):
        self.client = boto3.client('events')
        self.event_bus_name = event_bus_name
    
    def publish_event(self, source: str, detail_type: str, detail: Dict[Any, Any]):
        """Publish event to EventBridge"""
        try:
            response = self.client.put_events(
                Entries=[
                    {
                        'Source': source,
                        'DetailType': detail_type,
                        'Detail': json.dumps(detail, default=str),
                        'EventBusName': self.event_bus_name
                    }
                ]
            )
            print(f"Event published: {response}")
            return response
        except Exception as e:
            print(f"Error publishing event: {e}")
            raise

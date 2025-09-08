import pytest
from moto import mock_aws
import os
import boto3
from app.services.event_publisher import EventPublisher

@pytest.fixture
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"

@mock_aws
def test_event_publisher(aws_credentials):
    """Test that the EventPublisher can be initialized and can publish an event."""
    # Create the event bus
    client = boto3.client("events", region_name="us-east-1")
    client.create_event_bus(Name="mortgage-application-bus")

    publisher = EventPublisher()
    response = publisher.publish_event(
        event_type='TestEvent',
        detail={'message': 'Hello, World!'}
    )
    assert response['ResponseMetadata']['HTTPStatusCode'] == 200

from unittest.mock import Mock, MagicMock
from google.cloud import pubsub_v1, bigquery

def get_logger(name: str):
    """Factory para criar mock do logger."""
    mock_logger = Mock()
    mock_logger.info = Mock()
    mock_logger.error = Mock()
    mock_logger.warning = Mock()
    mock_logger.debug = Mock()
    return mock_logger

def get_telemetry(service_name: str):
    """Factory para criar mock do telemetry."""
    mock_telemetry = Mock()
    mock_telemetry.create_span = Mock(return_value=MagicMock())
    return mock_telemetry

def get_pubsub_publisher():
    """Factory para criar mock do PubSub Publisher."""
    mock_publisher = Mock()
    mock_publisher.publish = Mock(return_value=Mock())
    return mock_publisher

def get_pubsub_subscriber():
    """Factory para criar mock do PubSub Subscriber."""
    mock_subscriber = Mock()
    mock_subscriber.subscribe = Mock(return_value=Mock())
    return mock_subscriber

def get_bigquery_client():
    """Factory para criar mock do BigQuery."""
    mock_client = Mock()
    mock_client.query = Mock(return_value=Mock())
    return mock_client

def get_topic_path(publisher, project_id: str = None, topic_id: str = None):
    """Factory para criar mock do path do tópico PubSub."""
    return f"projects/{project_id or 'test-project'}/topics/{topic_id or 'test-topic'}"

def get_subscription_path(subscriber, project_id: str = None, subscription_id: str = None):
    """Factory para criar mock do path da subscription PubSub."""
    return f"projects/{project_id or 'test-project'}/subscriptions/{subscription_id or 'test-subscription'}" 
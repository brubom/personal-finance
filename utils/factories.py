import os
from typing import Optional
from google.cloud import pubsub_v1, bigquery
from utils.logging_config import setup_logging
from utils.telemetry import setup_telemetry

def get_logger(name: str):
    """Factory para criar instância do logger."""
    return setup_logging(name)

def get_telemetry(service_name: str):
    """Factory para criar instância do telemetry."""
    return setup_telemetry(service_name)

def get_pubsub_publisher():
    """Factory para criar cliente do PubSub Publisher."""
    return pubsub_v1.PublisherClient()

def get_pubsub_subscriber():
    """Factory para criar cliente do PubSub Subscriber."""
    return pubsub_v1.SubscriberClient()

def get_bigquery_client():
    """Factory para criar cliente do BigQuery."""
    return bigquery.Client()

def get_topic_path(publisher, project_id: Optional[str] = None, topic_id: Optional[str] = None):
    """Factory para criar path do tópico PubSub."""
    project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
    topic_id = topic_id or os.getenv("PUBSUB_TOPIC")
    return publisher.topic_path(project_id, topic_id)

def get_subscription_path(subscriber, project_id: Optional[str] = None, subscription_id: Optional[str] = None):
    """Factory para criar path da subscription PubSub."""
    project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
    subscription_id = subscription_id or os.getenv("PUBSUB_SUBSCRIPTION")
    return subscriber.subscription_path(project_id, subscription_id) 
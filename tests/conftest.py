import os
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from tests.factories import (
    get_logger,
    get_telemetry,
    get_pubsub_publisher,
    get_pubsub_subscriber,
    get_bigquery_client,
    get_topic_path,
    get_subscription_path
)

@pytest.fixture(autouse=True)
def setup_test_env():
    """Configura variáveis de ambiente para os testes."""
    os.environ['TRANSACTIONS_FUNCTION_ITAU_CARD'] = 'http://test-url.com'
    os.environ['TRANSACTIONS_TOPIC'] = 'projects/test-project/topics/test-topic'
    yield
    # Limpa as variáveis de ambiente após os testes
    os.environ.pop('TRANSACTIONS_FUNCTION_ITAU_CARD', None)
    os.environ.pop('TRANSACTIONS_TOPIC', None)

@pytest.fixture(autouse=True)
def mock_google_cloud_credentials():
    """Mock Google Cloud credentials for all tests."""
    with patch('google.auth.default') as mock_auth:
        mock_credentials = MagicMock()
        mock_credentials.before_request = MagicMock()
        mock_auth.return_value = (mock_credentials, 'test-project')
        yield

@pytest.fixture(autouse=True)
def mock_cloud_trace():
    """Mock Cloud Trace Exporter for all tests."""
    with patch('opentelemetry.exporter.cloud_trace.CloudTraceSpanExporter') as mock_exporter:
        mock_exporter.return_value = MagicMock()
        yield

@pytest.fixture(autouse=True)
def mock_factories():
    """Mock all factories for tests."""
    with patch('utils.factories.get_logger', get_logger), \
         patch('utils.factories.get_telemetry', get_telemetry), \
         patch('utils.factories.get_pubsub_publisher', get_pubsub_publisher), \
         patch('utils.factories.get_pubsub_subscriber', get_pubsub_subscriber), \
         patch('utils.factories.get_bigquery_client', get_bigquery_client), \
         patch('utils.factories.get_topic_path', get_topic_path), \
         patch('utils.factories.get_subscription_path', get_subscription_path):
        yield

@pytest.fixture(autouse=True)
def mock_environment_variables():
    """Set up test environment variables."""
    os.environ['GOOGLE_CLOUD_PROJECT'] = 'test-project'
    os.environ['BIGQUERY_DATASET'] = 'test_dataset'
    os.environ['BIGQUERY_TABLE'] = 'test_table'
    os.environ['PUBSUB_TOPIC'] = 'test-topic'
    os.environ['PUBSUB_SUBSCRIPTION'] = 'test-subscription'
    yield 

def setup_telemetry_if_not_testing(service_name: str):
    """Setup telemetry only if not running tests."""
    if not any(x in os.environ.get("PYTEST_CURRENT_TEST", "") for x in ["test_", "pytest"]):
        from utils.telemetry import setup_telemetry
        setup_telemetry(service_name)

@pytest.fixture(autouse=True)
def setup_telemetry():
    """Setup telemetry for tests."""
    setup_telemetry_if_not_testing("azul_visa_reader")
    yield 

@pytest.fixture(autouse=True)
def mock_telemetry():
    """Mock telemetry setup for all tests."""
    with patch('utils.telemetry.setup_telemetry') as mock_setup:
        yield mock_setup 
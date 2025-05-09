import os
import pytest

@pytest.fixture(autouse=True)
def setup_test_env():
    """Configura variáveis de ambiente para os testes."""
    os.environ['TRANSACTIONS_FUNCTION_ITAU_CARD'] = 'http://test-url.com'
    os.environ['TRANSACTIONS_TOPIC'] = 'projects/test-project/topics/test-topic'
    yield
    # Limpa as variáveis de ambiente após os testes
    os.environ.pop('TRANSACTIONS_FUNCTION_ITAU_CARD', None)
    os.environ.pop('TRANSACTIONS_TOPIC', None) 
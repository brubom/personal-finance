import os
import sys
from pathlib import Path

# Adiciona o diretório raiz ao PYTHONPATH
project_root = str(Path(__file__).parent)
sys.path.insert(0, project_root)

# Configura variáveis de ambiente para testes
os.environ["GCP_PROJECT_ID"] = "test-project"
os.environ["BIGQUERY_DATASET"] = "test_dataset"
os.environ["BIGQUERY_TABLE"] = "test_table"
os.environ["PUBSUB_SUBSCRIPTION_ID"] = "test-subscription"
os.environ["TRANSACTIONS_TOPIC"] = "test-topic"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "test-credentials.json" 
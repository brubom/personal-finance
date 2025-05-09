import os
import json
import logging
from google.cloud import bigquery
from google.cloud import pubsub_v1
from dotenv import load_dotenv

# Carrega as variáveis de ambiente
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s | %(asctime)s | %(name)s | %(message)s'
)
logger = logging.getLogger(__name__)

def check_credentials():
    """
    Verifica se as credenciais do Google Cloud estão configuradas.
    """
    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    if not credentials_path:
        raise ValueError("Variável GOOGLE_APPLICATION_CREDENTIALS não configurada")
    if not os.path.exists(credentials_path):
        raise ValueError(f"Arquivo de credenciais não encontrado: {credentials_path}")

def write_to_bigquery(transactions):
    """
    Escreve as transações no BigQuery.
    """
    try:
        # Configuração do BigQuery
        project_id = os.getenv('GCP_PROJECT_ID')
        dataset_id = os.getenv('BIGQUERY_DATASET')
        table_id = os.getenv('BIGQUERY_TABLE')
        
        if not all([project_id, dataset_id, table_id]):
            raise ValueError("Variáveis de ambiente do BigQuery não configuradas")
        
        # Verifica credenciais
        check_credentials()
        
        # Inicializa o cliente do BigQuery
        client = bigquery.Client(project=project_id)
        table_ref = f"{project_id}.{dataset_id}.{table_id}"
        
        # Insere os dados
        errors = client.insert_rows_json(table_ref, transactions)
        if errors:
            logger.error(f"Erros ao inserir no BigQuery: {errors}")
            raise Exception("Erro ao inserir dados no BigQuery")
        
        logger.info(f"{len(transactions)} transações inseridas com sucesso")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao escrever no BigQuery: {e}", exc_info=True)
        raise

def process_message(message):
    """
    Processa uma mensagem do Pub/Sub.
    """
    try:
        # Decodifica a mensagem
        data = json.loads(message.data.decode('utf-8'))
        logger.info(f"Mensagem recebida: {len(data)} blocos de transações")
        
        # Flatten a lista de blocos em uma única lista de transações
        transactions = [transaction for block in data for transaction in block]
        
        # Escreve no BigQuery
        write_to_bigquery(transactions)
        
        # Confirma o recebimento da mensagem
        message.ack()
        logger.info("Mensagem processada com sucesso")
        
    except Exception as e:
        logger.error(f"Erro ao processar mensagem: {e}", exc_info=True)
        message.nack()

def main():
    """
    Função principal que configura o subscriber e processa mensagens.
    """
    try:
        # Configuração do Pub/Sub
        project_id = os.getenv('GCP_PROJECT_ID')
        subscription_id = os.getenv('PUBSUB_SUBSCRIPTION_ID')
        
        if not all([project_id, subscription_id]):
            raise ValueError("Variáveis de ambiente do Pub/Sub não configuradas")
        
        # Verifica credenciais
        check_credentials()
        
        # Inicializa o subscriber
        subscriber = pubsub_v1.SubscriberClient()
        subscription_path = subscriber.subscription_path(project_id, subscription_id)
        
        # Configura o callback e inicia a escuta
        streaming_pull_future = subscriber.subscribe(
            subscription_path,
            callback=process_message
        )
        
        logger.info(f"Iniciando escuta na subscription: {subscription_path}")
        
        # Mantém o processo rodando
        try:
            streaming_pull_future.result()
        except Exception as e:
            streaming_pull_future.cancel()
            logger.error(f"Erro na escuta do Pub/Sub: {e}", exc_info=True)
            raise
            
    except Exception as e:
        logger.error(f"Erro fatal: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    main() 
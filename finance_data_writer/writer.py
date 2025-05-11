import os
import json
import logging
import time
from typing import Dict, Any, List, Optional

import functions_framework
from flask import Request
from google.cloud import bigquery
from google.cloud import pubsub_v1

from utils.logging_config import setup_logging, log_structured
from utils.telemetry import create_span, get_current_trace_id
from utils.factories import get_logger, get_telemetry, get_bigquery_client, get_pubsub_subscriber, get_subscription_path

# Setup logger
logger = get_logger(__name__)
# Removido: setup_telemetry_if_not_testing("writer")

def check_credentials(telemetry=None):
    """Verifica se as credenciais do Google Cloud estão configuradas."""
    telemetry = telemetry or get_telemetry("writer")
    with create_span("check_credentials") as span:
        try:
            # Verifica se a variável de ambiente GOOGLE_APPLICATION_CREDENTIALS está definida
            credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            if not credentials_path:
                error_msg = "Missing GOOGLE_APPLICATION_CREDENTIALS environment variable"
                logger.error(error_msg)
                span.set_attribute("error", error_msg)
                raise ValueError(error_msg)
            if not os.path.exists(credentials_path):
                error_msg = f"Credentials file not found: {credentials_path}"
                logger.error(error_msg)
                span.set_attribute("error", error_msg)
                raise FileNotFoundError(error_msg)
            # Tenta criar um cliente do BigQuery
            client = get_bigquery_client()
            # Se chegou aqui, as credenciais estão ok
            logger.info("Google Cloud credentials are valid")
            return True
        except Exception as e:
            error_msg = f"Error checking credentials: {str(e)}"
            logger.error(error_msg)
            span.set_attribute("error", error_msg)
            raise

def write_to_bigquery(rows: List[Dict[str, Any]], telemetry=None):
    """Escreve dados no BigQuery."""
    telemetry = telemetry or get_telemetry("writer")
    with create_span("write_to_bigquery", {"rows_count": len(rows)}) as span:
        try:
            # Obter cliente do BigQuery
            client = get_bigquery_client()
            # Obter configurações do ambiente
            dataset_id = os.getenv("BIGQUERY_DATASET")
            table_id = os.getenv("BIGQUERY_TABLE")
            if not dataset_id or not table_id:
                error_msg = "Missing BigQuery configuration"
                logger.error(error_msg)
                span.set_attribute("error", error_msg)
                raise ValueError(error_msg)
            # Preparar dados para inserção
            table_ref = f"{client.project}.{dataset_id}.{table_id}"
            # Registrar início da escrita
            logger.info("Starting BigQuery write",
                       extra={"rows_count": len(rows),
                             "table": table_ref})
            # Medir tempo de escrita
            start_time = time.monotonic()
            # Inserir dados
            errors = client.insert_rows_json(table_ref, rows)
            # Calcular duração
            duration = time.monotonic() - start_time
            # Registrar métricas
            logger.info("SLI: bigquery_write_duration",
                       extra={"duration": duration,
                             "rows_count": len(rows)})
            if errors:
                error_msg = f"Errors writing to BigQuery: {errors}"
                logger.error(error_msg)
                span.set_attribute("error", error_msg)
                raise RuntimeError(error_msg)
            # Registrar sucesso
            logger.info("BigQuery write completed successfully",
                       extra={"rows_count": len(rows),
                             "duration": duration})
            return True
        except Exception as e:
            error_msg = f"Error writing to BigQuery: {str(e)}"
            logger.error(error_msg)
            span.set_attribute("error", error_msg)
            raise

def process_message(message: pubsub_v1.types.PubsubMessage, telemetry=None):
    """Processa uma mensagem do Pub/Sub."""
    telemetry = telemetry or get_telemetry("writer")
    with create_span("process_message", {
        "message_id": message.message_id,
        "publish_time": message.publish_time.isoformat()
    }) as span:
        try:
            # Decodificar mensagem
            data = json.loads(message.data.decode("utf-8"))
            
            # Extrair dados
            rows = data.get("rows", [])
            file_path = data.get("file_path")
            trace_id = data.get("trace_id")
            
            # Registrar início do processamento
            logger.info("Processing message",
                       extra={"message_id": message.message_id,
                             "file_path": file_path,
                             "rows_count": len(rows),
                             "trace_id": trace_id})
            
            # Medir tempo de processamento
            start_time = time.monotonic()
            
            # Escrever no BigQuery
            write_to_bigquery(rows)
            
            # Calcular duração
            duration = time.monotonic() - start_time
            
            # Registrar métricas
            logger.info("SLI: message_processing_duration",
                       extra={"duration": duration,
                             "rows_count": len(rows)})
            
            # Registrar sucesso
            logger.info("Message processed successfully",
                       extra={"message_id": message.message_id,
                             "rows_count": len(rows),
                             "duration": duration})
            
            message.ack()
            return True
            
        except Exception as e:
            error_msg = f"Error processing message: {str(e)}"
            logger.error(error_msg)
            span.set_attribute("error", error_msg)
            message.nack()
            return False

@functions_framework.http
def main(request: Request, telemetry=None):
    """HTTP Cloud Function para processar mensagens do Pub/Sub."""
    telemetry = telemetry or get_telemetry("writer")
    with create_span("main") as span:
        try:
            # Verificar credenciais
            if not check_credentials():
                error_msg = "Invalid Google Cloud credentials"
                logger.error(error_msg)
                span.set_attribute("error", error_msg)
                raise ValueError(error_msg)
            
            # Obter subscriber
            subscriber = get_pubsub_subscriber()
            subscription_path = get_subscription_path(subscriber)
            
            # Registrar início do processamento
            logger.info("Starting message processing",
                       extra={"subscription": subscription_path})
            
            # Medir tempo de processamento
            start_time = time.monotonic()
            
            # Processar mensagens
            def callback(message):
                success = process_message(message)
                if success:
                    message.ack()
                else:
                    message.nack()
            
            # Iniciar subscriber
            streaming_pull_future = subscriber.subscribe(
                subscription_path,
                callback=callback
            )
            
            # Aguardar mensagens
            try:
                streaming_pull_future.result()
            except Exception as e:
                streaming_pull_future.cancel()
                raise e
            
            # Calcular duração
            duration = time.monotonic() - start_time
            
            # Registrar métricas
            logger.info("SLI: total_processing_duration",
                       extra={"duration": duration})
            
            # Registrar sucesso
            logger.info("Message processing completed successfully",
                       extra={"duration": duration})
            
            return ("OK", 200)
            
        except Exception as e:
            error_msg = f"Error processing messages: {str(e)}"
            logger.error(error_msg)
            span.set_attribute("error", error_msg)
            return (error_msg, 500)

if __name__ == "__main__":
    main() 
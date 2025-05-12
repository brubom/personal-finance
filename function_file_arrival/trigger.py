import os
import json
import logging
import requests
import time
from dotenv import load_dotenv
import functions_framework

from utils.logging_config import setup_logging, log_structured
from utils.telemetry import create_span, get_current_trace_id
from utils.factories import get_logger, get_telemetry

# Load environment variables
load_dotenv()

# Setup logger
logger = get_logger(__name__)

# Mapeamento de pastas para contas
FOLDER_TO_ACCOUNT = {
    "azul-visa": "azul-visa",
    "itau-card": "itau-card",
}

@functions_framework.cloud_event
def storage_trigger_function(cloud_event, telemetry=None):
    """Cloud Function triggered by a change to a Cloud Storage bucket.
    
    Args:
        cloud_event: The CloudEvent that triggered this function.
        telemetry: Optional telemetry instance for testing.
    """
    telemetry = telemetry or get_telemetry("trigger")
    data = cloud_event.data
    try:
        bucket_name = data["bucket"]
        file_name = data["name"]
    except KeyError as e:
        missing = e.args[0]
        log_structured(logger, logging.ERROR, f"Missing required fields in event: {missing}", **data)
        return f"Missing required fields in event: {missing}"

    # Criar span para o processamento do arquivo
    with create_span("process_file", {
        "file_name": file_name,
        "bucket": bucket_name,
        "event_type": "storage.trigger"
    }) as span:
        try:
            # Extrair nome da pasta do arquivo
            folder_name = file_name.split("/")[0]
            
            # Verificar se a pasta é válida
            if folder_name not in FOLDER_TO_ACCOUNT:
                error_msg = f"Invalid folder name: {folder_name}"
                log_structured(logger, logging.ERROR, error_msg,
                             folder_name=folder_name,
                             file_name=file_name)
                span.set_attribute("error", error_msg)
                return "Invalid folder name in file path"
            
            account = FOLDER_TO_ACCOUNT[folder_name]
            env_var = f"TRANSACTIONS_FUNCTION_ITAU_CARD_{account.upper()}"
            function_url = os.environ.get(env_var)
            if not function_url:
                log_structured(logger, logging.ERROR, f"Missing environment variable: {env_var}",
                                 file_name=file_name)
                span.set_attribute("error", f"Missing environment variable: {env_var}")
                return f"Missing environment variable: {env_var}"
            
            # Preparar payload
            payload = {
                "file_path": file_name,
                "bucket": bucket_name,
                "account": account,
                "trace_id": get_current_trace_id()
            }
            
            # Registrar início do processamento
            log_structured(logger, logging.INFO, "Sending request to processing function",
                          function_url=function_url, payload=payload)
            
            # Enviar requisição para a função HTTP
            start_time = time.monotonic()
            response = requests.post(function_url, json=payload)
            duration = time.monotonic() - start_time
            
            # Registrar métricas de tempo
            log_structured(logger, logging.INFO, "SLI: request_duration",
                          duration=duration,
                          file_name=file_name,
                          account=account)
            
            # Verificar resposta
            response.raise_for_status()
            
            # Registrar sucesso
            log_structured(logger, logging.INFO, "File processed successfully",
                          file_name=file_name,
                          account=account,
                          duration=duration,
                          status_code=response.status_code)
            
            return "File processed successfully"
        except Exception as e:
            error_msg = f"Error processing file: {str(e)}"
            log_structured(logger, logging.ERROR, error_msg,
                         file_name=file_name,
                         bucket=bucket_name)
            span.set_attribute("error", error_msg)
            return f"Error processing file: {e}"

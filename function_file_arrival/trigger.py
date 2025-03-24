import os
import logging
import requests

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s | %(asctime)s | %(name)s | %(message)s'
)
logger = logging.getLogger(__name__)

def storage_trigger_function(event, context):

    file_name   = event.get('name')
    bucket_name = event.get('bucket')
    if not file_name or not bucket_name:
        logger.warning("Nome do arquivo ou bucket não encontrados no evento.")
        return

    folder_name = file_name.split('/')[0] if '/' in file_name else ''
    logger.info(f"Arquivo recebido: bucket={bucket_name}, file={file_name}, folder={folder_name}")

    folder_to_account_map = {
        'finance_transactions/azul': 'itau_card',
        'pastaY': 'account_Y',
        'pastaZ': 'account_Z'
    }
    account_value = folder_to_account_map.get(folder_name, 'account_default').upper()
    logger.info(f"Account derivada: {account_value}")


    env_var_key = f"TRANSACTIONS_FUNCTION_{account_value}"
    second_function_url = os.environ.get(env_var_key)

    if not second_function_url:
        logger.error(f"A variável de ambiente '{env_var_key}' não foi encontrada. Abortando.")
        return

    payload = {
        "bucket": bucket_name,
        "file_path": file_name,
        "account": account_value
    }
    logger.info(f"Enviando payload para {second_function_url}: {payload}")

    try:
        response = requests.post(second_function_url, json=payload)
        response.raise_for_status()
        logger.info(f"Chamada à segunda função bem-sucedida. Status code={response.status_code}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro ao chamar a segunda função ({second_function_url}): {e}", exc_info=True)
        return

    logger.info(f"storage_trigger_function concluída para file={file_name}")

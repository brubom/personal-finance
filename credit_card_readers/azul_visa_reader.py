import os
import re
import json
import hashlib
import logging
import pandas as pd
from datetime import datetime
from openpyxl import load_workbook
from google.cloud import pubsub_v1

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s | %(asctime)s | %(name)s | %(message)s'
)
logger = logging.getLogger(__name__)

def converter_data_br(valor):
    """Converte datas em formato brasileiro (dd/mm/aaaa) para iso (yyyy-mm-dd)."""
    if isinstance(valor, str):
        valor = valor.strip()
        for fmt in ["%d/%m/%Y", "%d/%m/%y"]:
            try:
                dt = datetime.strptime(valor, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                pass
    return valor

def converter_valor_br(valor):
    if isinstance(valor, str):
        limpo = re.sub(r"[R$\s]", "", valor)
        limpo = limpo.replace(".", "")  
        limpo = limpo.replace(",", ".") 
        try:
            return float(limpo)
        except ValueError:
            return None
    return valor

def compute_row_hash(row, current_columns, account):
    """
    Gera um hash MD5 de cada linha baseado em colunas relevantes + account.
    """
    parts = []
    parts.append(str(account))
    for col in current_columns:
        if col is not None:
            parts.append(str(row.get(col, "")))
    concatenated = "".join(parts)
    return hashlib.md5(concatenated.encode('utf-8')).hexdigest()

def convert_xls_to_xlsx(file_path):
    """
    Converte um arquivo .xls para .xlsx usando pandas.
    Retorna o caminho do novo arquivo .xlsx.
    """
    try:
        # Lê o arquivo .xls
        df = pd.read_excel(file_path, engine='xlrd')
        
        # Cria o nome do novo arquivo .xlsx
        xlsx_path = file_path.rsplit('.', 1)[0] + '.xlsx'
        
        # Salva como .xlsx
        df.to_excel(xlsx_path, index=False, engine='openpyxl')
        
        logger.info(f"Arquivo convertido de {file_path} para {xlsx_path}")
        return xlsx_path
    except Exception as e:
        logger.error(f"Erro ao converter arquivo {file_path}: {e}", exc_info=True)
        raise

def process_row(row, current_columns, account):
    """Processa uma linha de dados."""
    row_dict = {}
    for col_index, col_name in enumerate(current_columns):
        if col_name:
            valor_celula = row[col_index] if col_index < len(row) else None
            row_dict[col_name] = valor_celula
    
    if 'data' in row_dict:
        row_dict['data'] = converter_data_br(row_dict['data'])
    if 'valor' in row_dict:
        row_dict['valor'] = converter_valor_br(row_dict['valor'])
    
    row_dict['account'] = account
    row_dict['id'] = compute_row_hash(row_dict, current_columns, account)
    return row_dict

def process_header(row):
    """Processa o cabeçalho da planilha."""
    return [str(x).strip().lower() if x else None for x in row]

def convert_data(file_path, account):
    """Converte dados do arquivo Excel."""
    try:
        logger.info(f"Processando arquivo: {file_path}")
        
        if file_path.lower().endswith('.xls'):
            file_path = convert_xls_to_xlsx(file_path)
        
        wb = load_workbook(file_path, data_only=True)
        sheet = wb.active
        
        data_blocks = []
        current_block = []
        current_columns = []
        
        STATE_SEARCHING_HEADER = 0
        STATE_READING_DATA = 1
        STATE_SEARCHING_NEXT = 2

        state = STATE_SEARCHING_HEADER
        lines_without_header = 0
        
        for row in sheet.iter_rows(values_only=True):
            first_cell = row[0] if row else None
            if isinstance(first_cell, str):
                first_cell = first_cell.strip().lower()
            if not first_cell:
                first_cell = None
            
            if state == STATE_SEARCHING_HEADER and first_cell == 'data':
                current_columns = process_header(row)
                current_block = []
                state = STATE_READING_DATA
            elif state == STATE_READING_DATA:
                if first_cell is None:
                    if current_block:
                        data_blocks.append(current_block)
                    current_block = []
                    current_columns = []
                    state = STATE_SEARCHING_NEXT
                    lines_without_header = 0
                else:
                    current_block.append(process_row(row, current_columns, account))
            elif state == STATE_SEARCHING_NEXT:
                if first_cell == 'data':
                    current_columns = process_header(row)
                    current_block = []
                    state = STATE_READING_DATA
                else:
                    lines_without_header += 1
                    if lines_without_header >= 6:
                        break

        if state == STATE_READING_DATA and current_block:
            data_blocks.append(current_block)
        
        return data_blocks
    except Exception as e:
        logger.error(f"Erro ao processar arquivo: {e}", exc_info=True)
        raise

def parse_excel(request):
    """
    Função HTTP que:
      - Recebe via JSON um 'file_path' e um 'account' (ou assume default).
      - Lê o Excel e separa em blocos (listas).
      - Publica cada bloco no Pub/Sub.
    Retorna um JSON com contagem de mensagens publicadas, e logs no Cloud Logging.
    """
    try:
        request_json = request.get_json(silent=True)
        if not request_json:
            logger.warning("Nenhum JSON na requisição.")
            return ({"error": "JSON inválido ou inexistente"}, 400)

        file_path = request_json.get("file_path")
        account   = request_json.get("account", "Cartão Azul Visa")

        if not file_path:
            logger.warning("Parâmetro 'file_path' não informado.")
            return ({"error": "Parâmetro 'file_path' é obrigatório"}, 400)
        
        logger.info(f"Iniciando parse do arquivo: {file_path} para account={account}.")
        
        data_blocks = convert_data(file_path, account)
        total_blocos = len(data_blocks)
        logger.info(f"Foram identificados {total_blocos} bloco(s) no arquivo.")

        # Verifica se estamos em ambiente de produção (Cloud Functions)
        is_production = os.environ.get('K_SERVICE') is not None

        if is_production:
            # Configura Pub/Sub apenas em produção
            publisher = pubsub_v1.PublisherClient()
            topic_path = os.environ.get("TRANSACTIONS_TOPIC")

            if not topic_path:
                msg = "A variável de ambiente 'TRANSACTIONS_TOPIC' não foi definida."
                logger.error(msg)
                return ({"error": msg}, 500)
            
            total_mensagens = 0

            # Publica todos os blocos em uma única mensagem
            try:
                all_blocks_json = json.dumps(data_blocks).encode("utf-8")
                future = publisher.publish(topic_path, data=all_blocks_json)
                message_id = future.result()
                total_mensagens = sum(len(bloco) for bloco in data_blocks)
                logger.info(f"Todos os blocos publicados com sucesso. ID: {message_id}")
            except Exception as e:
                logger.error(f"Erro ao publicar blocos no Pub/Sub: {e}", exc_info=True)
        else:
            # Em ambiente local, salva o JSON na raiz do projeto
            total_mensagens = sum(len(bloco) for bloco in data_blocks)
            output_file = "transactions.json"
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(data_blocks, f, ensure_ascii=False, indent=2)
                logger.info(f"Modo local: {total_mensagens} mensagens salvas em {output_file}")
            except Exception as e:
                logger.error(f"Erro ao salvar arquivo JSON: {e}", exc_info=True)
        
        logger.info(f"Processamento concluído. Total de mensagens: {total_mensagens}.")

        return ({
            "file_path": file_path,
            "account": account,
            "blocos": total_blocos,
            "mensagens_publicadas": total_mensagens,
            "ambiente": "produção" if is_production else "local"
        }, 200)
    
    except Exception as e:
        logger.error(f"Erro inesperado na função: {e}", exc_info=True)
        return ({"error": str(e)}, 500)

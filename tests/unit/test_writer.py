import unittest
from unittest.mock import patch, MagicMock
import json
import os
from finance_data_writer.writer import write_to_bigquery, process_message, main, check_credentials

class TestFinanceDataWriter(unittest.TestCase):
    def setUp(self):
        # Dados de teste
        self.sample_transactions = [
            {
                'data': '2024-03-20',
                'valor': 100.50,
                'account': 'ITAU_CARD',
                'id': 'hash123'
            }
        ]
        
        self.sample_message = MagicMock()
        self.sample_message.data = json.dumps([self.sample_transactions]).encode('utf-8')
        
        # Configuração do ambiente
        self.env_patcher = patch.dict('os.environ', {
            'GCP_PROJECT_ID': 'test-project',
            'BIGQUERY_DATASET': 'test_dataset',
            'BIGQUERY_TABLE': 'test_table',
            'PUBSUB_SUBSCRIPTION_ID': 'test-subscription',
            'GOOGLE_APPLICATION_CREDENTIALS': 'test-credentials.json'
        })
        self.env_patcher.start()

    def tearDown(self):
        self.env_patcher.stop()

    @patch('os.path.exists')
    def test_check_credentials_success(self, mock_exists):
        """Testa verificação bem-sucedida de credenciais"""
        mock_exists.return_value = True
        check_credentials()  # Não deve lançar exceção

    @patch('os.path.exists')
    def test_check_credentials_missing_env(self, mock_exists):
        """Testa erro quando variável de credenciais não está configurada"""
        with patch.dict('os.environ', {}, clear=True):
            with self.assertRaises(ValueError) as context:
                check_credentials()
            self.assertIn('GOOGLE_APPLICATION_CREDENTIALS não configurada', str(context.exception))

    @patch('os.path.exists')
    def test_check_credentials_file_not_found(self, mock_exists):
        """Testa erro quando arquivo de credenciais não existe"""
        mock_exists.return_value = False
        with self.assertRaises(ValueError) as context:
            check_credentials()
        self.assertIn('Arquivo de credenciais não encontrado', str(context.exception))

    @patch('os.path.exists')
    @patch('finance_data_writer.writer.bigquery.Client')
    def test_write_to_bigquery_success(self, mock_bq_client, mock_exists):
        """Testa inserção bem-sucedida no BigQuery"""
        # Configura os mocks
        mock_exists.return_value = True
        mock_client = MagicMock()
        mock_bq_client.return_value = mock_client
        mock_client.insert_rows_json.return_value = []  # Sem erros
        
        # Executa a função
        result = write_to_bigquery(self.sample_transactions)
        
        # Verifica se foi chamado corretamente
        self.assertTrue(result)
        mock_client.insert_rows_json.assert_called_once()
        call_args = mock_client.insert_rows_json.call_args[0]
        self.assertEqual(call_args[0], 'test-project.test_dataset.test_table')
        self.assertEqual(call_args[1], self.sample_transactions)

    @patch('os.path.exists')
    @patch('finance_data_writer.writer.bigquery.Client')
    def test_write_to_bigquery_error(self, mock_bq_client, mock_exists):
        """Testa erro na inserção no BigQuery"""
        # Configura os mocks
        mock_exists.return_value = True
        mock_client = MagicMock()
        mock_bq_client.return_value = mock_client
        mock_client.insert_rows_json.return_value = [{'errors': ['Erro de inserção']}]
        
        # Verifica se a exceção é lançada
        with self.assertRaises(Exception) as context:
            write_to_bigquery(self.sample_transactions)
        
        self.assertIn('Erro ao inserir dados no BigQuery', str(context.exception))

    def test_write_to_bigquery_missing_env(self):
        """Testa erro quando variáveis de ambiente estão faltando"""
        # Remove variáveis de ambiente
        with patch.dict('os.environ', {}, clear=True):
            with self.assertRaises(ValueError) as context:
                write_to_bigquery(self.sample_transactions)
            
            self.assertIn('Variáveis de ambiente do BigQuery não configuradas', 
                         str(context.exception))

    @patch('finance_data_writer.writer.write_to_bigquery')
    def test_process_message_success(self, mock_write):
        """Testa processamento bem-sucedido de mensagem"""
        # Configura o mock
        mock_write.return_value = True
        
        # Executa a função
        process_message(self.sample_message)
        
        # Verifica se a mensagem foi confirmada
        self.sample_message.ack.assert_called_once()
        mock_write.assert_called_once()

    @patch('finance_data_writer.writer.write_to_bigquery')
    def test_process_message_error(self, mock_write):
        """Testa erro no processamento de mensagem"""
        # Configura o mock para simular erro
        mock_write.side_effect = Exception("Erro de processamento")
        
        # Executa a função
        process_message(self.sample_message)
        
        # Verifica se a mensagem foi negada
        self.sample_message.nack.assert_called_once()

    @patch('os.path.exists')
    @patch('finance_data_writer.writer.pubsub_v1.SubscriberClient')
    def test_main_success(self, mock_subscriber, mock_exists):
        """Testa inicialização bem-sucedida do subscriber"""
        # Configura os mocks
        mock_exists.return_value = True
        mock_sub = MagicMock()
        mock_subscriber.return_value = mock_sub
        
        # Configura o mock do streaming_pull_future
        mock_future = MagicMock()
        mock_sub.subscribe.return_value = mock_future
        
        # Simula um KeyboardInterrupt para sair do loop
        mock_future.result.side_effect = KeyboardInterrupt
        
        try:
            main()
        except KeyboardInterrupt:
            pass  # Ignora o KeyboardInterrupt esperado
        
        # Verifica se o subscriber foi configurado corretamente
        mock_sub.subscribe.assert_called_once()
        subscription_path = mock_sub.subscription_path.return_value
        mock_sub.subscribe.assert_called_with(
            subscription_path,
            callback=process_message
        )

    def test_main_missing_env(self):
        """Testa erro quando variáveis de ambiente do Pub/Sub estão faltando"""
        # Remove variáveis de ambiente
        with patch.dict('os.environ', {}, clear=True):
            with self.assertRaises(ValueError) as context:
                main()
            
            self.assertIn('Variáveis de ambiente do Pub/Sub não configuradas', 
                         str(context.exception))

if __name__ == '__main__':
    unittest.main() 
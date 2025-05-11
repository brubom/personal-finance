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
                'date': '2024-01-01',
                'description': 'Test Transaction',
                'amount': 100.50
            }
        ]
        
        self.sample_message = MagicMock()
        self.sample_message.data = b'{"date": "2024-01-01", "description": "Test Transaction", "amount": 100.50}'
        self.sample_message.ack = MagicMock()
        self.sample_message.nack = MagicMock()
        
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
        result = check_credentials()
        self.assertTrue(result)

    @patch('os.path.exists')
    def test_check_credentials_file_not_found(self, mock_exists):
        """Testa erro quando arquivo de credenciais não existe"""
        mock_exists.return_value = False
        with self.assertRaises(FileNotFoundError) as context:
            check_credentials()
        self.assertEqual(str(context.exception), "Credentials file not found: test-credentials.json")

    @patch.dict('os.environ', {}, clear=True)
    def test_check_credentials_missing_env(self):
        """Testa erro quando variável de ambiente está faltando"""
        with self.assertRaises(ValueError) as context:
            check_credentials()
        self.assertEqual(str(context.exception), "Missing GOOGLE_APPLICATION_CREDENTIALS environment variable")

    @patch('finance_data_writer.writer.bigquery.Client')
    def test_write_to_bigquery_success(self, mock_bq_client):
        """Testa inserção bem-sucedida no BigQuery"""
        mock_client = MagicMock()
        mock_bq_client.return_value = mock_client
        mock_client.insert_rows_json.return_value = []

        result = write_to_bigquery(self.sample_transactions)
        self.assertTrue(result)
        mock_client.insert_rows_json.assert_called_once()

    @patch('finance_data_writer.writer.bigquery.Client')
    def test_write_to_bigquery_error(self, mock_bq_client):
        """Testa erro na inserção no BigQuery"""
        mock_client = MagicMock()
        mock_bq_client.return_value = mock_client
        mock_client.insert_rows_json.return_value = ['Error']
        with self.assertRaises(RuntimeError):
            write_to_bigquery(self.sample_transactions)

    @patch.dict('os.environ', {}, clear=True)
    def test_write_to_bigquery_missing_env(self):
        """Testa erro quando variáveis de ambiente estão faltando"""
        with self.assertRaises(ValueError) as context:
            write_to_bigquery(self.sample_transactions)
        self.assertEqual(str(context.exception), "Missing BigQuery configuration")

    @patch('finance_data_writer.writer.write_to_bigquery')
    def test_process_message_success(self, mock_write):
        """Testa processamento bem-sucedido de mensagem"""
        mock_write.return_value = True
        process_message(self.sample_message)
        self.sample_message.ack.assert_called_once()

    @patch('finance_data_writer.writer.write_to_bigquery')
    def test_process_message_error(self, mock_write):
        """Testa erro no processamento de mensagem"""
        mock_write.side_effect = Exception("Erro de processamento")
        process_message(self.sample_message)
        self.sample_message.nack.assert_called_once()

    @patch('os.path.exists')
    @patch('finance_data_writer.writer.pubsub_v1.SubscriberClient')
    def test_main_success(self, mock_subscriber, mock_exists):
        """Testa inicialização bem-sucedida do subscriber"""
        mock_request = MagicMock()
        mock_exists.return_value = True
        mock_sub = MagicMock()
        mock_subscriber.return_value = mock_sub
        mock_future = MagicMock()
        mock_sub.subscribe.return_value = mock_future
        mock_future.result.side_effect = KeyboardInterrupt
        try:
            main(mock_request)
        except KeyboardInterrupt:
            pass

    @patch.dict('os.environ', {}, clear=True)
    @patch('finance_data_writer.writer.write_to_bigquery')
    def test_main_missing_env(self, mock_write):
        """Testa erro quando variáveis de ambiente estão faltando"""
        mock_request = MagicMock()
        result = main(mock_request)
        self.assertIsInstance(result, tuple)
        self.assertEqual(result[1], 500)
        self.assertIn("Missing GOOGLE_APPLICATION_CREDENTIALS environment variable", result[0])

if __name__ == '__main__':
    unittest.main() 
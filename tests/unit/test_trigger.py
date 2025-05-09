import unittest
from unittest.mock import patch, MagicMock
from function_file_arrival.trigger import storage_trigger_function
import requests

class TestStorageTrigger(unittest.TestCase):
    def setUp(self):
        self.valid_event = {
            'name': 'finance_transactions/azul/test_file.xlsx',
            'bucket': 'test-bucket'
        }

    @patch('function_file_arrival.trigger.os.environ.get')
    @patch('function_file_arrival.trigger.requests.post')
    def test_valid_event_azul_card(self, mock_post, mock_env_get):
        # Configura o mock para retornar uma URL de teste
        mock_env_get.return_value = 'http://test-url.com'
        
        # Configura o mock da resposta HTTP
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        # Executa a função
        storage_trigger_function(self.valid_event, None)

        # Verifica se a URL correta foi chamada
        mock_env_get.assert_called_with('TRANSACTIONS_FUNCTION_ITAU_CARD')
        
        # Verifica se o POST foi chamado com os parâmetros corretos
        mock_post.assert_called_once()
        call_args = mock_post.call_args[1]
        self.assertEqual(call_args['json']['bucket'], 'test-bucket')
        self.assertEqual(call_args['json']['file_path'], 'finance_transactions/azul/test_file.xlsx')
        self.assertEqual(call_args['json']['account'], 'ITAU_CARD')

    def test_invalid_event_missing_name(self):
        event = {'bucket': 'test-bucket'}
        with self.assertLogs(level='WARNING') as log:
            storage_trigger_function(event, None)
            self.assertIn("Nome do arquivo ou bucket não encontrados no evento", log.output[0])

    def test_invalid_event_missing_bucket(self):
        event = {'name': 'test_file.xlsx'}
        with self.assertLogs(level='WARNING') as log:
            storage_trigger_function(event, None)
            self.assertIn("Nome do arquivo ou bucket não encontrados no evento", log.output[0])

    @patch('function_file_arrival.trigger.os.environ.get')
    def test_missing_environment_variable(self, mock_env_get):
        mock_env_get.return_value = None
        with self.assertLogs(level='ERROR') as log:
            storage_trigger_function(self.valid_event, None)
            self.assertIn("A variável de ambiente 'TRANSACTIONS_FUNCTION_ITAU_CARD' não foi encontrada", log.output[0])

    @patch('function_file_arrival.trigger.os.environ.get')
    @patch('function_file_arrival.trigger.requests.post')
    def test_http_error(self, mock_post, mock_env_get):
        mock_env_get.return_value = 'http://test-url.com'
        mock_post.side_effect = requests.exceptions.RequestException("HTTP Error")
        
        with self.assertLogs(level='ERROR') as log:
            storage_trigger_function(self.valid_event, None)
            self.assertIn("Erro ao chamar a segunda função", log.output[0])

if __name__ == '__main__':
    unittest.main() 
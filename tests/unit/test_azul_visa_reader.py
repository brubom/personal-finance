import unittest
from unittest.mock import patch, MagicMock
import os
import pandas as pd
from credit_card_readers.azul_visa_reader import (
    converter_data_br,
    converter_valor_br,
    compute_row_hash,
    parse_excel
)

class TestAzulVisaReader(unittest.TestCase):
    def setUp(self):
        self.env_patcher = patch.dict(os.environ, {
            'K_SERVICE': 'test-service',
            'GCP_PROJECT_ID': 'test-project',
            'TRANSACTIONS_TOPIC': 'test-topic'
        })
        self.env_patcher.start()
        
        # Mock do load_workbook
        self.load_workbook_patcher = patch('credit_card_readers.azul_visa_reader.load_workbook')
        self.mock_load_workbook = self.load_workbook_patcher.start()
        
        # Configurar o mock do workbook
        self.mock_sheet = MagicMock()
        self.mock_sheet.iter_rows.return_value = [
            ['data', 'descricao', 'valor'],  # cabeçalho
            ['01/01/2024', 'Teste 1', 'R$ 100,00'],
            ['02/01/2024', 'Teste 2', 'R$ 200,00'],
            [None, None, None]  # linha vazia para simular fim do arquivo
        ]
        self.mock_workbook = MagicMock()
        self.mock_workbook.active = self.mock_sheet
        self.mock_load_workbook.return_value = self.mock_workbook

        self.test_file = 'tests/resources/test_file.xlsx'
        self.valid_request = {
            'file_path': 'test-folder/test-file.xlsx'
        }

    def tearDown(self):
        self.env_patcher.stop()
        self.load_workbook_patcher.stop()

    def test_converter_data_br(self):
        """Testa conversão de data no formato brasileiro"""
        self.assertEqual(converter_data_br('01/01/2024'), '2024-01-01')
        self.assertEqual(converter_data_br('31/12/2024'), '2024-12-31')
        self.assertEqual(converter_data_br('invalid'), 'invalid')

    def test_converter_valor_br(self):
        """Testa conversão de valor no formato brasileiro"""
        self.assertEqual(converter_valor_br('R$ 100,50'), 100.50)
        self.assertEqual(converter_valor_br('R$ 1.234,56'), 1234.56)
        self.assertIsNone(converter_valor_br('invalid'))

    def test_compute_row_hash(self):
        """Testa geração de hash para linha"""
        columns = ['Data', 'Valor', 'Descrição']
        account = 'test-account'
        row = {'Data': '01/01/2024', 'Valor': 'R$ 100,50', 'Descrição': 'Test Transaction'}
        hash_value = compute_row_hash(row, columns, account)
        self.assertEqual(len(hash_value), 32)

    @patch('credit_card_readers.azul_visa_reader.get_pubsub_publisher')
    @patch('credit_card_readers.azul_visa_reader.load_workbook')
    def test_parse_excel_success(self, mock_load_workbook, mock_get_pubsub_publisher):
        """Testa processamento bem-sucedido do Excel"""
        mock_wb = MagicMock()
        mock_sheet = MagicMock()
        mock_wb.active = mock_sheet
        mock_sheet.iter_rows.return_value = [
            ['Data', 'Valor', 'Descrição'],
            ['01/01/2024', 'R$ 100,50', 'Test Transaction']
        ]
        mock_load_workbook.return_value = mock_wb

        # Mock publisher
        mock_publisher = MagicMock()
        mock_future = MagicMock()
        mock_future.result.return_value = None
        mock_publisher.publish.return_value = mock_future
        mock_get_pubsub_publisher.return_value = mock_publisher

        mock_request = MagicMock()
        mock_request.get_json.return_value = self.valid_request

        result = parse_excel(mock_request)
        self.assertEqual(result[0], "OK")
        self.assertEqual(result[1], 200)

    def test_parse_excel_invalid_request(self):
        """Testa erro quando request é inválido"""
        mock_request = MagicMock()
        mock_request.get_json.return_value = None

        result = parse_excel(mock_request)
        self.assertEqual(result[0], "Invalid JSON in request")
        self.assertEqual(result[1], 400)

    def test_parse_excel_missing_file_path(self):
        """Testa erro quando caminho do arquivo está faltando"""
        mock_request = MagicMock()
        mock_request.get_json.return_value = {}

        result = parse_excel(mock_request)
        self.assertIn(result[0], ["Missing file_path in request", "Invalid JSON in request"])

    @patch('credit_card_readers.azul_visa_reader.get_pubsub_publisher')
    @patch('credit_card_readers.azul_visa_reader.load_workbook')
    def test_parse_excel_local_mode(self, mock_load_workbook, mock_get_pubsub_publisher):
        """Testa processamento em modo local"""
        mock_wb = MagicMock()
        mock_sheet = MagicMock()
        mock_wb.active = mock_sheet
        mock_sheet.iter_rows.return_value = [
            ['Data', 'Valor', 'Descrição'],
            ['01/01/2024', 'R$ 100,50', 'Test Transaction']
        ]
        mock_load_workbook.return_value = mock_wb

        # Mock publisher
        mock_publisher = MagicMock()
        mock_future = MagicMock()
        mock_future.result.return_value = None
        mock_publisher.publish.return_value = mock_future
        mock_get_pubsub_publisher.return_value = mock_publisher

        # Remover K_SERVICE para simular modo local
        if 'K_SERVICE' in os.environ:
            del os.environ['K_SERVICE']

        mock_request = MagicMock()
        mock_request.get_json.return_value = {'file_path': 'local/test-file.xlsx'}

        result = parse_excel(mock_request)
        if isinstance(result, tuple):
            self.assertEqual(result[0], "Running in local mode")
        else:
            self.assertEqual(result, "Running in local mode")

if __name__ == '__main__':
    unittest.main() 
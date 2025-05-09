import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime
import os
from credit_card_readers.azul_visa_reader import (
    converter_data_br,
    converter_valor_br,
    compute_row_hash,
    convert_data,
    parse_excel
)

class TestAzulVisaReader(unittest.TestCase):
    def setUp(self):
        # Define o caminho para o arquivo de teste
        self.test_file_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'resources',
            'Fatura-Excel-fev.xlsx'
        )

    def test_converter_data_br(self):
        # Testa conversão de data no formato dd/mm/yyyy
        self.assertEqual(converter_data_br("01/01/2024"), "2024-01-01")
        # Testa conversão de data no formato dd/mm/yy
        self.assertEqual(converter_data_br("01/01/24"), "2024-01-01")
        # Testa valor não string
        self.assertEqual(converter_data_br(123), 123)
        # Testa string inválida
        self.assertEqual(converter_data_br("data inválida"), "data inválida")

    def test_converter_valor_br(self):
        # Testa conversão de valor com R$
        self.assertEqual(converter_valor_br("R$ 1.234,56"), 1234.56)
        # Testa conversão de valor sem R$
        self.assertEqual(converter_valor_br("1.234,56"), 1234.56)
        # Testa conversão de valor com espaços
        self.assertEqual(converter_valor_br(" 1.234,56 "), 1234.56)
        # Testa valor não string
        self.assertEqual(converter_valor_br(1234.56), 1234.56)
        # Testa string inválida
        self.assertIsNone(converter_valor_br("valor inválido"))

    def test_compute_row_hash(self):
        # Testa geração de hash com dados válidos
        row = {
            'data': '2024-01-01',
            'valor': 1234.56,
            'descricao': 'Teste'
        }
        columns = ['data', 'valor', 'descricao']
        account = 'ITAU_CARD'
        
        hash_result = compute_row_hash(row, columns, account)
        self.assertIsInstance(hash_result, str)
        self.assertEqual(len(hash_result), 32)  # MD5 hash length

        # Testa que o mesmo input gera o mesmo hash
        hash_result2 = compute_row_hash(row, columns, account)
        self.assertEqual(hash_result, hash_result2)

        # Testa que inputs diferentes geram hashes diferentes
        row2 = row.copy()
        row2['valor'] = 1234.57
        hash_result3 = compute_row_hash(row2, columns, account)
        self.assertNotEqual(hash_result, hash_result3)

    @patch('credit_card_readers.azul_visa_reader.load_workbook')
    def test_convert_data(self, mock_load_workbook):
        # Mock do workbook e sheet
        mock_sheet = MagicMock()
        mock_sheet.iter_rows.return_value = [
            ['data', 'valor', 'descricao'],  # Header
            ['01/01/2024', 'R$ 1.234,56', 'Teste 1'],  # Dados
            ['02/01/2024', 'R$ 2.345,67', 'Teste 2'],  # Dados
            [None, None, None],  # Fim do bloco
            ['data', 'valor', 'descricao'],  # Novo header
            ['03/01/2024', 'R$ 3.456,78', 'Teste 3'],  # Dados
            [None, None, None]  # Fim do bloco
        ]
        mock_wb = MagicMock()
        mock_wb.active = mock_sheet
        mock_load_workbook.return_value = mock_wb

        # Testa conversão de dados
        result = convert_data('test.xlsx', 'ITAU_CARD')

        # Verifica resultado
        self.assertEqual(len(result), 2)  # Dois blocos
        self.assertEqual(len(result[0]), 2)  # Primeiro bloco tem 2 linhas
        self.assertEqual(len(result[1]), 1)  # Segundo bloco tem 1 linha

        # Verifica conversões
        self.assertEqual(result[0][0]['data'], '2024-01-01')
        self.assertEqual(result[0][0]['valor'], 1234.56)
        self.assertEqual(result[0][0]['account'], 'ITAU_CARD')
        self.assertIn('id', result[0][0])

    @patch('credit_card_readers.azul_visa_reader.convert_data')
    def test_parse_excel_local(self, mock_convert_data):
        # Mock da função convert_data
        mock_convert_data.return_value = [
            [{'data': '2024-01-01', 'valor': 1234.56, 'account': 'ITAU_CARD', 'id': 'hash1'}]
        ]

        # Mock do request
        mock_request = MagicMock()
        mock_request.get_json.return_value = {
            'file_path': 'test.xlsx',
            'account': 'ITAU_CARD'
        }

        # Testa função parse_excel em ambiente local
        with patch.dict('os.environ', {}, clear=True):
            response, status_code = parse_excel(mock_request)

        # Verifica resultado
        self.assertEqual(status_code, 200)
        self.assertEqual(response['file_path'], 'test.xlsx')
        self.assertEqual(response['account'], 'ITAU_CARD')
        self.assertEqual(response['blocos'], 1)
        self.assertEqual(response['mensagens_publicadas'], 1)
        self.assertEqual(response['ambiente'], 'local')

    @patch('credit_card_readers.azul_visa_reader.convert_data')
    @patch('credit_card_readers.azul_visa_reader.pubsub_v1.PublisherClient')
    def test_parse_excel_production(self, mock_publisher, mock_convert_data):
        # Mock da função convert_data
        mock_convert_data.return_value = [
            [{'data': '2024-01-01', 'valor': 1234.56, 'account': 'ITAU_CARD', 'id': 'hash1'}]
        ]

        # Mock do publisher
        mock_publisher_instance = MagicMock()
        mock_publisher.return_value = mock_publisher_instance
        mock_publisher_instance.publish.return_value.result.return_value = 'message_id'

        # Mock do request
        mock_request = MagicMock()
        mock_request.get_json.return_value = {
            'file_path': 'test.xlsx',
            'account': 'ITAU_CARD'
        }

        # Testa função parse_excel em ambiente de produção
        with patch.dict('os.environ', {
            'K_SERVICE': 'test-service',
            'TRANSACTIONS_TOPIC': 'projects/test/topics/test-topic'
        }, clear=True):
            response, status_code = parse_excel(mock_request)

        # Verifica resultado
        self.assertEqual(status_code, 200)
        self.assertEqual(response['file_path'], 'test.xlsx')
        self.assertEqual(response['account'], 'ITAU_CARD')
        self.assertEqual(response['blocos'], 1)
        self.assertEqual(response['mensagens_publicadas'], 1)
        self.assertEqual(response['ambiente'], 'produção')

        # Verifica se o publisher foi chamado
        mock_publisher_instance.publish.assert_called_once()

    def test_parse_excel_invalid_json(self):
        # Mock do request com JSON inválido
        mock_request = MagicMock()
        mock_request.get_json.return_value = None

        # Testa função parse_excel com JSON inválido
        response, status_code = parse_excel(mock_request)

        # Verifica resultado
        self.assertEqual(status_code, 400)
        self.assertEqual(response['error'], 'JSON inválido ou inexistente')

    def test_parse_excel_missing_file_path(self):
        # Mock do request sem file_path
        mock_request = MagicMock()
        mock_request.get_json.return_value = {
            'account': 'ITAU_CARD'
        }

        # Testa função parse_excel sem file_path
        response, status_code = parse_excel(mock_request)

        # Verifica resultado
        self.assertEqual(status_code, 400)
        self.assertEqual(response['error'], 'Parâmetro \'file_path\' é obrigatório')

    def test_parse_excel_with_real_file(self):
        """Testa a função parse_excel com um arquivo real."""
        # Mock do request
        mock_request = MagicMock()
        mock_request.get_json.return_value = {
            'file_path': self.test_file_path,
            'account': 'Cartão Azul Visa'
        }

        # Testa função parse_excel em ambiente local
        with patch.dict('os.environ', {}, clear=True):
            response, status_code = parse_excel(mock_request)

        # Verifica resultado
        self.assertEqual(status_code, 200)
        self.assertEqual(response['file_path'], self.test_file_path)
        self.assertEqual(response['account'], 'Cartão Azul Visa')
        self.assertGreater(response['blocos'], 0)
        self.assertGreater(response['mensagens_publicadas'], 0)
        self.assertEqual(response['ambiente'], 'local')

if __name__ == '__main__':
    unittest.main() 
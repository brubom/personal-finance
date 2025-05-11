import unittest
from unittest.mock import MagicMock, patch
import os
from function_file_arrival.trigger import storage_trigger_function

class MockCloudEvent(dict):
    @property
    def data(self):
        return self

class TestTrigger(unittest.TestCase):
    def setUp(self):
        self.valid_event = {
            'bucket': 'test-bucket',
            'name': 'azul-visa/test-file.xls',
        }
        self.mock_response = MagicMock()
        self.mock_response.status_code = 200

    @patch('function_file_arrival.trigger.requests.post')
    def test_valid_event_azul_card(self, mock_post):
        """Test processing a valid event for Azul card."""
        mock_post.return_value = self.mock_response
        os.environ['TRANSACTIONS_FUNCTION_ITAU_CARD_AZUL-VISA'] = 'http://test-function'
        result = storage_trigger_function(MockCloudEvent(self.valid_event), None)
        self.assertEqual(result, "File processed successfully")

    def test_missing_environment_variable(self):
        """Test handling missing environment variable."""
        os.environ.pop('TRANSACTIONS_FUNCTION_ITAU_CARD_AZUL-VISA', None)
        result = storage_trigger_function(MockCloudEvent(self.valid_event), None)
        self.assertEqual(result, "Missing environment variable: TRANSACTIONS_FUNCTION_ITAU_CARD_AZUL-VISA")

    def test_invalid_event_missing_bucket(self):
        """Test handling event with missing bucket."""
        invalid_event = self.valid_event.copy()
        del invalid_event['bucket']
        result = storage_trigger_function(MockCloudEvent(invalid_event), None)
        self.assertEqual(result, "Missing required fields in event: bucket")

    def test_invalid_event_missing_name(self):
        """Test handling event with missing name."""
        invalid_event = self.valid_event.copy()
        del invalid_event['name']
        result = storage_trigger_function(MockCloudEvent(invalid_event), None)
        self.assertEqual(result, "Missing required fields in event: name")

    def test_invalid_folder(self):
        """Test handling event with invalid folder."""
        invalid_event = self.valid_event.copy()
        invalid_event['name'] = 'invalid/test-file.xls'
        result = storage_trigger_function(MockCloudEvent(invalid_event), None)
        self.assertEqual(result, "Invalid folder name in file path")

    @patch('function_file_arrival.trigger.requests.post')
    def test_http_error(self, mock_post):
        """Test handling HTTP error from processing function."""
        mock_post.return_value = self.mock_response
        self.mock_response.raise_for_status.side_effect = Exception("HTTP Error")
        os.environ['TRANSACTIONS_FUNCTION_ITAU_CARD_AZUL-VISA'] = 'http://test-function'
        result = storage_trigger_function(MockCloudEvent(self.valid_event), None)
        self.assertEqual(result, "Error processing file: HTTP Error")

if __name__ == '__main__':
    unittest.main() 
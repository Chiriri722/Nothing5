import unittest
import json
import os
from unittest.mock import patch, mock_open, MagicMock
from pathlib import Path
from modules.credential_manager import CredentialManager

class TestCredentialManager(unittest.TestCase):
    def setUp(self):
        self.manager = CredentialManager()

    @patch('pathlib.Path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='{"apiKey": "test_gemini_key"}')
    def test_detect_gemini_credentials_simple(self, mock_file, mock_exists):
        # Simulate file exists at ~/.gemini/settings.json
        # Using return_value instead of side_effect for simplicity and correctness
        mock_exists.return_value = True

        key = self.manager.detect_gemini_credentials()
        self.assertEqual(key, "test_gemini_key")

    @patch('pathlib.Path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='{"authentication": {"apiKey": "test_gemini_key_nested"}}')
    def test_detect_gemini_credentials_nested(self, mock_file, mock_exists):
        mock_exists.return_value = True

        key = self.manager.detect_gemini_credentials()
        self.assertEqual(key, "test_gemini_key_nested")

    @patch('pathlib.Path.exists')
    def test_detect_gemini_credentials_not_found(self, mock_exists):
        mock_exists.return_value = False
        key = self.manager.detect_gemini_credentials()
        self.assertIsNone(key)

    @patch('pathlib.Path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='{"apiKey": "test_claude_key"}')
    def test_detect_claude_credentials(self, mock_file, mock_exists):
        mock_exists.return_value = True

        key = self.manager.detect_claude_credentials()
        self.assertEqual(key, "test_claude_key")

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test_env_key"})
    def test_detect_openai_credentials(self):
        key = self.manager.detect_openai_credentials()
        self.assertEqual(key, "test_env_key")

    def test_mask_key(self):
        self.assertEqual(self.manager._mask_key("1234567890"), "1234...7890")
        self.assertEqual(self.manager._mask_key("short"), "****")

if __name__ == '__main__':
    unittest.main()

import unittest
import os
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

from modules.extractor import FileExtractor
from modules.classifier import FileClassifier, ClassificationStatus

class TestNewFeatures(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path("test_data")
        self.test_dir.mkdir(exist_ok=True)
        self.extractor = FileExtractor()

        # Mock Config for Classifier
        with patch("modules.classifier.OPENAI_API_KEY", "dummy_key"):
            self.classifier = FileClassifier(api_key="dummy_key")

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_smart_extraction_long_text(self):
        """Test if smart extraction truncates long text correctly."""
        long_text = "a" * 5000
        test_file = self.test_dir / "long.txt"
        test_file.write_text(long_text, encoding="utf-8")

        result = self.extractor.extract(str(test_file))
        content = result["content"]

        self.assertIn("... [중간 내용 생략", content)
        self.assertTrue(len(content) < 5000)
        self.assertTrue(content.startswith("aaaa"))
        self.assertTrue(content.endswith("aaaa"))

    def test_hierarchical_filtering_extension(self):
        """Test if extension-based rules work without API call."""
        # Mock API call to ensure it's NOT called
        self.classifier._call_api = MagicMock()

        result = self.classifier.classify_file("music.mp3", "mp3", "")

        self.assertEqual(result["status"], ClassificationStatus.SUCCESS.value)
        self.assertEqual(result["folder_name"], "음악")
        self.classifier._call_api.assert_not_called()

    def test_hierarchical_filtering_keyword(self):
        """Test if keyword-based rules work without API call."""
        # Mock API call to ensure it's NOT called
        self.classifier._call_api = MagicMock()

        result = self.classifier.classify_file("2024_Invoice_Scan.pdf", "pdf", "content")

        self.assertEqual(result["status"], ClassificationStatus.SUCCESS.value)
        self.assertEqual(result["folder_name"], "영수증")
        self.classifier._call_api.assert_not_called()

    def test_api_call_fallback(self):
        """Test if API is called when no rules match."""
        # Mock API response
        mock_response = """
        {
            "folder_name": "기획서",
            "category": "문서",
            "confidence": 0.9,
            "reason": "테스트"
        }
        """
        self.classifier._call_api = MagicMock(return_value=mock_response)

        result = self.classifier.classify_file("unknown.doc", "doc", "content")

        self.assertEqual(result["folder_name"], "기획서")
        self.classifier._call_api.assert_called_once()

if __name__ == '__main__':
    unittest.main()


import unittest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from modules.classifier import FileClassifier, ClassificationStatus

class TestAsyncIntegration(unittest.TestCase):
    def setUp(self):
        self.classifier = FileClassifier(api_key="test_key")
        # Mocking history_db to avoid actual DB operations
        self.classifier.history_db = MagicMock()
        self.classifier.history_db.get_file_hash_async = AsyncMock(return_value="dummy_hash")
        self.classifier.history_db.get_result_async = AsyncMock(return_value=None)
        self.classifier.history_db.save_result_async = AsyncMock()

        # Mocking API call
        # Note: _classify_file_api_async is the method to mock, as it wraps the internal logic
        self.classifier._classify_file_api_async = AsyncMock(return_value={
            "folder_name": "test_folder",
            "category": "test",
            "confidence": 1.0,
            "reason": "test",
            "status": "success"
        })

    def test_classify_file_async_flow(self):
        async def run_test():
            result = await self.classifier.classify_file_async(
                filename="test.txt",
                file_type="txt",
                content="test content",
                file_path="/tmp/test.txt"
            )
            return result

        result = asyncio.run(run_test())

        self.assertEqual(result["folder_name"], "test_folder")
        self.classifier.history_db.get_file_hash_async.assert_called_once()
        self.classifier.history_db.get_result_async.assert_called_once()
        self.classifier.history_db.save_result_async.assert_called_once()

if __name__ == "__main__":
    unittest.main()

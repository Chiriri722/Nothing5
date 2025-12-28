# -*- coding: utf-8 -*-
"""
신규 기능 테스트 (Smart Extraction & Hierarchical Filtering)
"""

import unittest
import os
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch
import sys

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from modules.extractor import FileExtractor
from modules.classifier import FileClassifier, ClassificationStatus

class TestFileExtractorSmartSummary(unittest.TestCase):
    """Smart Summary Extraction 테스트"""

    def setUp(self):
        self.test_dir = Path("test_temp")
        self.test_dir.mkdir(exist_ok=True)
        self.extractor = FileExtractor()

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_extract_short_text(self):
        """짧은 텍스트 파일 추출"""
        file_path = self.test_dir / "short.txt"
        content = "Short content"
        file_path.write_text(content, encoding='utf-8')

        result = self.extractor.extract_text_from_txt(str(file_path))
        self.assertEqual(result['content'], content)

    def test_extract_long_text(self):
        """긴 텍스트 파일 추출 (요약 동작 확인)"""
        file_path = self.test_dir / "long.txt"
        # 3000자 생성
        content = "A" * 1500 + "B" * 1500
        file_path.write_text(content, encoding='utf-8')

        result = self.extractor.extract_text_from_txt(str(file_path))
        extracted = result['content']

        # 앞 1000자 + 구분자 + 뒤 1000자
        self.assertTrue(extracted.startswith("A" * 1000))
        self.assertTrue(extracted.endswith("B" * 1000))
        self.assertIn("...[중간 생략]...", extracted)
        self.assertTrue(len(extracted) < 3000)


class TestHierarchicalFiltering(unittest.TestCase):
    """계층적 필터링 테스트"""

    def setUp(self):
        self.classifier = FileClassifier(api_key="test_key")
        # API 호출을 방지하기 위해 mock 처리 (혹시 호출될 경우를 대비)
        self.classifier._call_api = MagicMock()

    def test_extension_rule(self):
        """확장자 기반 규칙 테스트"""
        # 이미지 확장자 -> 이미지 폴더
        result = self.classifier.check_rules("photo.jpg", "jpg")
        self.assertIsNotNone(result)
        self.assertEqual(result['folder_name'], "이미지")
        self.assertEqual(result['status'], "success")

        # 오디오 확장자 -> 오디오 폴더
        result = self.classifier.check_rules("music.mp3", "mp3")
        self.assertIsNotNone(result)
        self.assertEqual(result['folder_name'], "오디오")

    def test_keyword_rule(self):
        """키워드 기반 규칙 테스트"""
        # invoice 키워드 -> 청구서 폴더
        result = self.classifier.check_rules("my_invoice_2023.pdf", "pdf")
        self.assertIsNotNone(result)
        self.assertEqual(result['folder_name'], "청구서")

        # report 키워드 -> 보고서 폴더
        result = self.classifier.check_rules("weekly_report.docx", "docx")
        self.assertIsNotNone(result)
        self.assertEqual(result['folder_name'], "보고서")

    def test_no_rule_match(self):
        """규칙 매칭 안됨 -> API 호출 대상"""
        result = self.classifier.check_rules("unknown_file.xyz", "xyz")
        self.assertIsNone(result)

    def test_classify_file_uses_rules(self):
        """classify_file 메서드가 규칙을 우선 사용하는지 테스트"""
        # 규칙에 맞는 파일
        result = self.classifier.classify_file("test.jpg", "jpg", "")

        # API가 호출되지 않아야 함
        self.classifier._call_api.assert_not_called()
        self.assertEqual(result['folder_name'], "이미지")

if __name__ == "__main__":
    unittest.main()

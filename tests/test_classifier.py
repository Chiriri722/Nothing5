# -*- coding: utf-8 -*-
"""
분류기 모듈 테스트

FileClassifier 클래스의 기능을 검증하는 단위 테스트입니다.
"""

import unittest
import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from modules.classifier import FileClassifier, ClassificationStatus


class TestFileClassifierInit(unittest.TestCase):
    """FileClassifier 초기화 테스트"""

    def test_init_with_api_key(self):
        """API 키를 전달하여 초기화"""
        classifier = FileClassifier(api_key="test_key_123")
        self.assertEqual(classifier.api_key, "test_key_123")
        self.assertIsNotNone(classifier.client)

    def test_init_without_api_key_raises_error(self):
        """API 키 없이 초기화하면 에러 발생"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
            with self.assertRaises(ValueError):
                FileClassifier(api_key="")

    def test_init_with_custom_model(self):
        """커스텀 모델로 초기화"""
        classifier = FileClassifier(
            api_key="test_key_123", model="gpt-4"
        )
        self.assertEqual(classifier.model, "gpt-4")


class TestValidateFolderName(unittest.TestCase):
    """폴더명 유효성 검사 테스트"""

    def setUp(self):
        """테스트 설정"""
        self.classifier = FileClassifier(api_key="test_key_123")

    def test_valid_folder_name(self):
        """유효한 폴더명"""
        result = self.classifier._validate_folder_name("여행사진")
        self.assertEqual(result, "여행사진")

    def test_folder_name_with_forbidden_chars(self):
        """금지된 문자 제거"""
        result = self.classifier._validate_folder_name("여행/사진*테스트")
        # 금지된 문자가 제거되어야 함
        self.assertNotIn("/", result)
        self.assertNotIn("*", result)

    def test_folder_name_too_short(self):
        """너무 짧은 폴더명"""
        result = self.classifier._validate_folder_name("a")
        self.assertIsNone(result)

    def test_folder_name_too_long(self):
        """너무 긴 폴더명"""
        result = self.classifier._validate_folder_name("a" * 50)
        self.assertIsNone(result)

    def test_forbidden_system_folder_name(self):
        """시스템 예약어"""
        result = self.classifier._validate_folder_name("Documents")
        self.assertIsNone(result)

    def test_empty_folder_name(self):
        """빈 폴더명"""
        result = self.classifier._validate_folder_name("")
        self.assertIsNone(result)


class TestCreateFallbackFolderName(unittest.TestCase):
    """폴백 폴더명 생성 테스트"""

    def setUp(self):
        """테스트 설정"""
        self.classifier = FileClassifier(api_key="test_key_123")

    def test_fallback_from_file_type(self):
        """파일 타입 기반 폴백"""
        # 파일명이 너무 짧으면 파일 타입 매핑에서 카테고리 반환
        result = self.classifier._create_fallback_folder_name(
            "x.pdf", "pdf"
        )
        # 구현상 FILE_TYPE_MAPPING에서 "pdf"에 해당하는 값 반환
        self.assertIn(result, ["문서", "document"])

    def test_fallback_from_filename(self):
        """파일명 기반 폴백"""
        result = self.classifier._create_fallback_folder_name(
            "invoice_2024.pdf", "pdf"
        )
        # 파일명에서 의미있는 부분 추출
        self.assertTrue(len(result) >= 2)

    def test_fallback_unknown_type(self):
        """알 수 없는 파일 타입"""
        # 알 수 없는 타입은 "기타"로 분류되어야 함
        result = self.classifier._create_fallback_folder_name(
            "x.unknown", "unknown"
        )
        # 구현상 "기타" 또는 파일명 추출 가능
        self.assertIn(result, ["기타", "x"])


class TestParseResponse(unittest.TestCase):
    """API 응답 파싱 테스트"""

    def setUp(self):
        """테스트 설정"""
        self.classifier = FileClassifier(api_key="test_key_123")

    def test_parse_valid_json_response(self):
        """유효한 JSON 응답 파싱"""
        response = """{
            "folder_name": "청구서",
            "category": "문서",
            "confidence": 0.95,
            "reason": "청구서 문서로 판단됨"
        }"""
        result = self.classifier._parse_response(response)
        self.assertEqual(result["folder_name"], "청구서")
        self.assertEqual(result["category"], "문서")
        self.assertEqual(result["confidence"], 0.95)

    def test_parse_json_with_markdown_codeblock(self):
        """마크다운 코드블록이 포함된 JSON 파싱"""
        response = """```json
{
    "folder_name": "여행사진",
    "category": "이미지",
    "confidence": 0.88,
    "reason": "여행 관련 사진"
}
```"""
        result = self.classifier._parse_response(response)
        self.assertEqual(result["folder_name"], "여행사진")
        self.assertEqual(result["category"], "이미지")

    def test_parse_response_with_missing_fields(self):
        """필드가 누락된 응답 파싱"""
        response = """{
            "folder_name": "문서",
            "category": "문서"
        }"""
        result = self.classifier._parse_response(response)
        self.assertEqual(result["folder_name"], "문서")
        self.assertIn("confidence", result)
        self.assertIn("reason", result)

    def test_parse_invalid_json_raises_error(self):
        """잘못된 JSON 파싱 시 에러"""
        response = "This is not JSON"
        with self.assertRaises(ValueError):
            self.classifier._parse_response(response)


class TestIsImageFile(unittest.TestCase):
    """이미지 파일 판별 테스트"""

    def setUp(self):
        """테스트 설정"""
        self.classifier = FileClassifier(api_key="test_key_123")

    def test_image_file_formats(self):
        """이미지 파일 형식 판별"""
        image_types = ["jpg", "png", "gif", "bmp", "webp"]
        for img_type in image_types:
            with self.subTest(img_type=img_type):
                self.assertTrue(self.classifier._is_image_file(img_type))

    def test_non_image_file_formats(self):
        """비이미지 파일 형식 판별"""
        non_image_types = ["pdf", "docx", "mp4", "mp3"]
        for file_type in non_image_types:
            with self.subTest(file_type=file_type):
                self.assertFalse(self.classifier._is_image_file(file_type))


class TestCreateErrorResult(unittest.TestCase):
    """에러 결과 생성 테스트"""

    def setUp(self):
        """테스트 설정"""
        self.classifier = FileClassifier(api_key="test_key_123")

    def test_create_error_result(self):
        """에러 결과 생성"""
        error_msg = "Test error message"
        result = self.classifier._create_error_result(error_msg)

        self.assertEqual(result["status"], ClassificationStatus.ERROR.value)
        self.assertEqual(result["folder_name"], "기타")
        self.assertEqual(result["confidence"], 0.0)
        self.assertEqual(result["error"], error_msg)


class TestCreateFallbackResult(unittest.TestCase):
    """폴백 결과 생성 테스트"""

    def setUp(self):
        """테스트 설정"""
        self.classifier = FileClassifier(api_key="test_key_123")

    def test_create_fallback_result(self):
        """폴백 결과 생성"""
        result = self.classifier._create_fallback_result(
            "document.pdf", "pdf", "API Error"
        )

        self.assertEqual(result["status"], ClassificationStatus.SUCCESS.value)
        self.assertIsNotNone(result["folder_name"])
        self.assertEqual(result["confidence"], 0.5)
        self.assertIn("폴백", result["reason"])


class TestFileMappings(unittest.TestCase):
    """파일 타입 매핑 테스트"""

    def setUp(self):
        """테스트 설정"""
        self.classifier = FileClassifier(api_key="test_key_123")

    def test_document_type_mapping(self):
        """문서 타입 매핑"""
        # 파일명이 너무 짧으면 파일 타입 기반 카테고리 반환
        doc_types = ["pdf", "docx", "doc", "txt"]
        for doc_type in doc_types:
            with self.subTest(doc_type=doc_type):
                result = self.classifier._create_fallback_folder_name(
                    f"x.{doc_type}", doc_type
                )
                # "x"는 2자 미만이므로 카테고리 반환
                self.assertEqual(result, "문서")

    def test_image_type_mapping(self):
        """이미지 타입 매핑"""
        # 파일명이 너무 짧으면 파일 타입 기반 카테고리 반환
        img_types = ["jpg", "png", "gif"]
        for img_type in img_types:
            with self.subTest(img_type=img_type):
                result = self.classifier._create_fallback_folder_name(
                    f"x.{img_type}", img_type
                )
                # "x"는 2자 미만이므로 카테고리 반환
                self.assertEqual(result, "이미지")

    def test_video_type_mapping(self):
        """비디오 타입 매핑"""
        # 파일명이 너무 짧으면 파일 타입 기반 카테고리 반환
        video_types = ["mp4", "avi", "mov"]
        for video_type in video_types:
            with self.subTest(video_type=video_type):
                result = self.classifier._create_fallback_folder_name(
                    f"x.{video_type}", video_type
                )
                # "x"는 2자 미만이므로 카테고리 반환
                self.assertEqual(result, "비디오")

    def test_audio_type_mapping(self):
        """오디오 타입 매핑"""
        # 파일명이 너무 짧으면 파일 타입 기반 카테고리 반환
        audio_types = ["mp3", "wav", "flac"]
        for audio_type in audio_types:
            with self.subTest(audio_type=audio_type):
                result = self.classifier._create_fallback_folder_name(
                    f"x.{audio_type}", audio_type
                )
                # "x"는 2자 미만이므로 카테고리 반환
                self.assertEqual(result, "음악")


class TestPromptTemplates(unittest.TestCase):
    """프롬프트 템플릿 테스트"""

    def setUp(self):
        """테스트 설정"""
        self.classifier = FileClassifier(api_key="test_key_123")

    def test_classification_prompt_template(self):
        """분류 프롬프트 템플릿 확인"""
        prompt = self.classifier.CLASSIFICATION_PROMPT
        self.assertIn("{filename}", prompt)
        self.assertIn("{file_type}", prompt)
        self.assertIn("{content_length}", prompt)
        self.assertIn("{content}", prompt)
        self.assertIn("JSON", prompt)

    def test_vision_prompt_template(self):
        """Vision 프롬프트 템플릿 확인"""
        prompt = self.classifier.VISION_PROMPT
        self.assertIn("{filename}", prompt)
        self.assertIn("{file_type}", prompt)
        self.assertIn("JSON", prompt)


if __name__ == "__main__":
    unittest.main()

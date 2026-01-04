# -*- coding: utf-8 -*-
"""
파일 분류 모듈

OpenAI LLM API를 사용하여 파일 내용을 분석하고 적절한 폴더 이름을 생성합니다.
"""

import json
import re
import base64
import logging
import asyncio
from typing import Dict, List, Optional, Any
from enum import Enum
from pathlib import Path
import os

try:
    from openai import APIError, APIConnectionError, RateLimitError
except ImportError:
    # OpenAI not installed, but we might be using other providers
    pass

from config.config import (
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    LLM_MODEL,
    LLM_TEMPERATURE,
    LLM_MAX_TOKENS,
    TIMEOUT,
    MAX_CONTENT_LENGTH,
)
import config.config as cfg
from modules.history_db import ProcessingHistory
from modules.llm.factory import create_llm_client
from modules.llm.openai_client import OpenAIClient

logger = logging.getLogger(__name__)


class ClassificationStatus(Enum):
    """분류 상태"""
    SUCCESS = "success"
    ERROR = "error"


class FileClassifier:
    """
    OpenAI LLM 기반 파일 분류 클래스

    파일의 내용을 분석하고 LLM이 추천하는 폴더 이름을 생성합니다.
    """

    # 파일 타입별 카테고리 매핑
    FILE_TYPE_MAPPING = {
        # 문서
        "txt": "문서",
        "pdf": "문서",
        "docx": "문서",
        "doc": "문서",
        "xlsx": "스프레드시트",
        "xls": "스프레드시트",
        "csv": "데이터",
        # 이미지
        "jpg": "이미지",
        "jpeg": "이미지",
        "png": "이미지",
        "gif": "이미지",
        "bmp": "이미지",
        "svg": "이미지",
        "webp": "이미지",
        # 비디오
        "mp4": "비디오",
        "avi": "비디오",
        "mov": "비디오",
        "mkv": "비디오",
        "flv": "비디오",
        # 음악
        "mp3": "음악",
        "wav": "음악",
        "flac": "음악",
        "aac": "음악",
        "m4a": "음악",
        # 압축
        "zip": "압축파일",
        "rar": "압축파일",
        "7z": "압축파일",
        "tar": "압축파일",
        "gz": "압축파일",
    }

    # 계층적 필터링을 위한 규칙 정의 (확장자 -> 폴더명)
    EXTENSION_RULES = {
        "jpg": "이미지", "jpeg": "이미지", "png": "이미지", "gif": "이미지",
        "bmp": "이미지", "svg": "이미지", "webp": "이미지",
        "mp3": "오디오", "wav": "오디오", "flac": "오디오", "aac": "오디오", "m4a": "오디오",
        "mp4": "비디오", "avi": "비디오", "mov": "비디오", "mkv": "비디오", "flv": "비디오",
        "zip": "압축파일", "rar": "압축파일", "7z": "압축파일", "tar": "압축파일", "gz": "압축파일",
        "py": "코드", "js": "코드", "java": "코드", "cpp": "코드", "c": "코드", "html": "코드", "css": "코드"
    }

    # 키워드 규칙 (키워드 -> 폴더명)
    KEYWORD_RULES = {
        "invoice": "청구서", "receipt": "영수증", "report": "보고서",
        "bill": "청구서", "contract": "계약서", "manual": "매뉴얼",
        "screenshot": "스크린샷"
    }

    # 금지된 폴더명 (시스템 예약어)
    FORBIDDEN_FOLDER_NAMES = {
        "documents",
        "desktop",
        "downloads",
        "pictures",
        "music",
        "videos",
        "con",
        "prn",
        "aux",
        "nul",
        "com1",
        "lpt1",
    }

    # 금지된 문자
    FORBIDDEN_CHARS = r'[\\/:\*\?"<>|]'

    # 프롬프트 템플릿
    CLASSIFICATION_PROMPT = """파일을 분석하여 적절한 폴더명을 추천해주세요.
정보: {filename}, {file_type}
내용:
{content}

규칙:
1. 한글로 된 의미있는 이름 (예: 청구서, 회의록)
2. 짧고 간결하게
3. 내용 기반 분류

JSON 응답:
{{
    "folder_name": "추천폴더명",
    "category": "문서|이미지|비디오|음악|기타",
    "confidence": 0.85,
    "reason": "이유"
}}"""

    VISION_PROMPT = """이미지를 분석하여 폴더명을 추천해주세요.
정보: {filename}, {file_type}

규칙:
1. 한글로 된 의미있는 이름
2. 짧고 간결하게
3. 내용 기반

JSON 응답:
{{
    "folder_name": "추천폴더명",
    "category": "이미지",
    "confidence": 0.85,
    "reason": "이유"
}}"""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: Optional[str] = None):
        """FileClassifier 초기화"""
        # API 키 설정
        self.api_key = api_key or OPENAI_API_KEY
        if not self.api_key:
            logger.error("OPENAI_API_KEY가 설정되지 않았습니다")
            # raise ValueError("OPENAI_API_KEY 환경 변수가 필요합니다") # Allow init for UI, check later

        # Base URL 설정
        self.base_url = base_url or OPENAI_BASE_URL

        # 모델 설정
        self.model = model or LLM_MODEL
        self.temperature = LLM_TEMPERATURE
        self.max_tokens = LLM_MAX_TOKENS
        self.timeout = TIMEOUT

        # LLM Client Factory
        try:
            self.llm_client = create_llm_client(
                cfg.CREDENTIAL_SOURCE,
                self.api_key,
                self.base_url,
                self.model,
                self.temperature,
                self.max_tokens,
                self.timeout
            )
        except Exception as e:
            logger.error(f"Failed to initialize LLM Client: {e}")
            self.llm_client = None

        # 히스토리 DB 및 세마포어
        self.history_db = ProcessingHistory()
        self.semaphore = asyncio.Semaphore(5) # 최대 5개 동시 요청

        logger.info(f"FileClassifier 초기화됨 - 모델: {self.model}, Base URL: {self.base_url}")

    async def classify_file_async(
        self, filename: str, file_type: str, content: str, file_path: str = None
    ) -> Dict[str, Any]:
        """비동기 파일 분류"""
        # 1. 캐시 확인
        if file_path:
            file_hash = await self.history_db.get_file_hash_async(file_path)
            cached_result = await self.history_db.get_result_async(file_hash)
            if cached_result:
                logger.info(f"캐시된 결과 사용: {filename} -> {cached_result['folder_name']}")
                return {**cached_result, "status": ClassificationStatus.SUCCESS.value}

        # 2. 규칙 기반 확인
        rule_based_result = self.check_rules(filename, file_type)
        if rule_based_result:
            return rule_based_result

        # 3. API 호출 (세마포어 적용)
        async with self.semaphore:
            result = await self._classify_file_api_async(filename, file_type, content)

        # 4. 결과 저장
        if result.get("status") == ClassificationStatus.SUCCESS.value and file_path:
            file_size = Path(file_path).stat().st_size
            await self.history_db.save_result_async(file_hash, filename, file_size, result)

        return result

    async def _classify_file_api_async(self, filename: str, file_type: str, content: str) -> Dict[str, Any]:
        """실제 API 호출 로직 (비동기)"""
        try:
            # 입력 검증
            if not filename or not file_type:
                return self._create_fallback_result(filename, file_type, "파일명 누락")

            truncated_content = content[:2500] if content else ""
            content_length = len(content) if content else 0

            prompt = self.CLASSIFICATION_PROMPT.format(
                filename=filename,
                file_type=file_type,
                content_length=content_length,
                content=truncated_content,
            )

            # 재시도 로직
            for attempt in range(3):
                try:
                    if not self.llm_client:
                        raise ValueError("LLM Client not initialized")

                    response_text = await self.llm_client.call_async(prompt)
                    result = self._parse_response(response_text)

                    folder_name = result.get("folder_name", "")
                    validated = self._validate_folder_name(folder_name)
                    if not validated:
                        validated = self._create_fallback_folder_name(filename, file_type)

                    result["folder_name"] = validated
                    result["status"] = ClassificationStatus.SUCCESS.value
                    return result
                except Exception as e: # Catch generic exception for retry
                    # Check for RateLimit if using OpenAI directly, but abstraction hides it slightly
                    # For now, simple retry logic
                    if "rate limit" in str(e).lower():
                        if attempt == 2: raise
                        await asyncio.sleep(2 ** attempt)
                    else:
                        logger.error(f"API 호출 중 오류 ({attempt+1}/3): {e}")
                        if attempt == 2: raise

        except Exception as e:
            logger.error(f"비동기 분류 실패: {e}")
            return self._create_fallback_result(filename, file_type, str(e))

    async def classify_image_async(self, image_path: str) -> Dict[str, Any]:
        """비동기 이미지 분류"""
        return await asyncio.to_thread(self.classify_image, image_path)

    def classify_file(
        self, filename: str, file_type: str, content: str
    ) -> Dict[str, Any]:
        """파일 분류 (동기)"""
        logger.info(f"파일 분류 시작: {filename}")

        try:
            if not filename or not file_type:
                error_msg = "파일명과 파일 타입이 필요합니다"
                logger.error(error_msg)
                return self._create_fallback_result(filename, file_type, error_msg)

            rule_based_result = self.check_rules(filename, file_type)
            if rule_based_result:
                logger.info(f"규칙 기반 분류 성공: {filename} -> {rule_based_result['folder_name']}")
                return rule_based_result

            truncated_content = content[:MAX_CONTENT_LENGTH] if content else ""
            content_length = len(content) if content else 0

            prompt = self.CLASSIFICATION_PROMPT.format(
                filename=filename,
                file_type=file_type,
                content_length=content_length,
                content=truncated_content,
            )

            if not self.llm_client:
                 raise ValueError("LLM Client not initialized")

            response = self.llm_client.call(prompt)
            result = self._parse_response(response)

            folder_name = result.get("folder_name", "")
            validated_folder_name = self._validate_folder_name(folder_name)

            if not validated_folder_name:
                logger.warning(f"폴더명 검증 실패: {folder_name}, 폴백 사용")
                validated_folder_name = self._create_fallback_folder_name(filename, file_type)

            result["folder_name"] = validated_folder_name
            result["status"] = ClassificationStatus.SUCCESS.value

            return result

        except Exception as e:
            error_msg = f"분류 중 오류 발생: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return self._create_fallback_result(filename, file_type, error_msg)

    def classify_image(self, image_path: str) -> Dict[str, Any]:
        """이미지 분류"""
        logger.info(f"이미지 분류 시작: {image_path}")

        try:
            if not Path(image_path).exists():
                return self._create_error_result(f"파일을 찾을 수 없습니다: {image_path}")

            filename = Path(image_path).name
            file_type = Path(image_path).suffix.lstrip(".").lower()

            rule_based_result = self.check_rules(filename, file_type)
            if rule_based_result:
                 return rule_based_result

            if not self._is_image_file(file_type):
                return self._create_fallback_result(filename, file_type, "이미지 파일이 아닙니다")

            # Vision API is only supported by OpenAI client currently in this impl
            if not isinstance(self.llm_client, OpenAIClient):
                 # Fallback for other providers if they don't support vision in this abstraction yet
                 return self._create_fallback_result(filename, file_type, "Vision API not supported by current provider")

            image_data = self._encode_image_to_base64(image_path)

            prompt = self.VISION_PROMPT.format(filename=filename, file_type=file_type)

            # Determine mime type
            mime_types = {
                "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
                "gif": "image/gif", "webp": "image/webp",
            }
            mime_type = mime_types.get(file_type, "image/jpeg")

            response = self.llm_client.call_vision(prompt, image_data, mime_type)
            result = self._parse_response(response)

            folder_name = result.get("folder_name", "")
            validated_folder_name = self._validate_folder_name(folder_name)

            if not validated_folder_name:
                validated_folder_name = self._create_fallback_folder_name(filename, file_type)

            result["folder_name"] = validated_folder_name
            result["status"] = ClassificationStatus.SUCCESS.value

            return result

        except Exception as e:
            error_msg = f"이미지 분류 중 오류: {str(e)}"
            logger.error(error_msg, exc_info=True)
            filename = Path(image_path).name if image_path else "unknown"
            return self._create_fallback_result(filename, "image", error_msg)

    def check_rules(self, filename: str, file_type: str) -> Optional[Dict[str, Any]]:
        """규칙 기반 분류 (Hierarchical Filtering)"""
        file_type_lower = file_type.lower()
        filename_lower = filename.lower()

        # 1. 키워드 기반 규칙
        for keyword, folder in self.KEYWORD_RULES.items():
            if keyword in filename_lower:
                return {
                    "status": ClassificationStatus.SUCCESS.value,
                    "folder_name": folder,
                    "category": self.FILE_TYPE_MAPPING.get(file_type_lower, "기타"),
                    "confidence": 1.0,
                    "reason": f"파일명 키워드 매칭 ('{keyword}')"
                }

        # 2. 확장자 기반 규칙
        if file_type_lower in self.EXTENSION_RULES:
            folder_name = self.EXTENSION_RULES[file_type_lower]
            return {
                "status": ClassificationStatus.SUCCESS.value,
                "folder_name": folder_name,
                "category": self.FILE_TYPE_MAPPING.get(file_type_lower, "기타"),
                "confidence": 0.95,
                "reason": f"확장자 기반 규칙 ('{file_type}')"
            }

        return None

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        try:
            cleaned = re.sub(r"```(?:json)?\n?", "", response_text)
            cleaned = cleaned.strip()
            result = json.loads(cleaned)

            required_fields = ["folder_name", "category", "confidence", "reason"]
            for field in required_fields:
                if field not in result:
                    if field == "confidence": result[field] = 0.5
                    else: result[field] = ""
            return result
        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 실패: {str(e)}")
            raise ValueError(f"JSON 파싱 실패: {str(e)}")

    def _validate_folder_name(self, folder_name: str) -> Optional[str]:
        if not folder_name: return None
        cleaned = re.sub(self.FORBIDDEN_CHARS, "", folder_name).strip()
        if len(cleaned) < 2 or len(cleaned) > 30: return None
        if cleaned.lower() in self.FORBIDDEN_FOLDER_NAMES: return None
        return cleaned

    def _create_fallback_folder_name(self, filename: str, file_type: str) -> str:
        category = self.FILE_TYPE_MAPPING.get(file_type.lower(), "기타")
        name_without_ext = Path(filename).stem
        cleaned_name = re.sub(self.FORBIDDEN_CHARS, "", name_without_ext).strip()[:20]
        if cleaned_name and len(cleaned_name) >= 2: return cleaned_name
        return category

    def _create_error_result(self, error_msg: str) -> Dict[str, Any]:
        return {
            "status": ClassificationStatus.ERROR.value,
            "folder_name": "기타",
            "category": "기타",
            "confidence": 0.0,
            "reason": "분류 실패",
            "error": error_msg,
        }

    def _create_fallback_result(self, filename: str, file_type: str, error_msg: str) -> Dict[str, Any]:
        folder_name = self._create_fallback_folder_name(filename, file_type)
        category = self.FILE_TYPE_MAPPING.get(file_type.lower(), "기타")
        return {
            "status": ClassificationStatus.SUCCESS.value,
            "folder_name": folder_name,
            "category": category,
            "confidence": 0.5,
            "reason": f"폴백 분류 (오류: {error_msg})",
        }

    def _is_image_file(self, file_type: str) -> bool:
        return file_type.lower() in {"jpg", "jpeg", "png", "gif", "bmp", "svg", "webp"}

    def _encode_image_to_base64(self, image_path: str) -> str:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

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
from modules.prompts import CLASSIFICATION_PROMPT, VISION_PROMPT
from modules.file_rules import FILE_TYPE_MAPPING, EXTENSION_RULES, KEYWORD_RULES

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
        self.max_concurrent_requests = getattr(cfg, 'MAX_CONCURRENT_API_CALLS', 5)
        self.semaphore = asyncio.Semaphore(self.max_concurrent_requests)

        logger.info(f"FileClassifier 초기화됨 - 모델: {self.model}, Base URL: {self.base_url}, Max Concurrent: {self.max_concurrent_requests}")

    async def classify_file_async(
        self, filename: str, file_type: str, content: str, file_path: str = None
    ) -> Dict[str, Any]:
        """비동기 파일 분류"""
        file_hash = None

        # 1. 캐시 확인 (Smart Caching)
        if file_path:
            file_hash = await self.history_db.get_file_hash_async(file_path)
            cached_result = await self.history_db.get_result_async(file_hash)
            if cached_result:
                logger.info(f"캐시된 결과 사용: {filename} -> {cached_result['folder_name']}")
                return {**cached_result, "status": ClassificationStatus.SUCCESS.value}

        # 2. 규칙 기반 확인 (Hierarchical Filtering)
        rule_based_result = self.check_rules(filename, file_type)
        if rule_based_result:
            return rule_based_result

        # 3. API 호출 (세마포어 적용 + Rate Limiting)
        async with self.semaphore:
            result = await self._classify_file_api_async(filename, file_type, content)

        # 4. 결과 저장 (Memoization)
        if result.get("status") == ClassificationStatus.SUCCESS.value and file_path and file_hash:
            try:
                file_size = Path(file_path).stat().st_size
                await self.history_db.save_result_async(file_hash, filename, file_size, result)
            except Exception as e:
                logger.warning(f"DB 저장 실패: {e}")

        return result

    def _prepare_classification_prompt(self, filename: str, file_type: str, content: str) -> str:
        """Helper to prepare the prompt string."""
        # 토큰 최적화를 위해 내용 길이 제한 (최대 2500자)
        truncated_content = content[:MAX_CONTENT_LENGTH] if content else ""
        content_length = len(content) if content else 0

        # Note: The prompt template CLASSIFICATION_PROMPT expects 'content_length' argument in sync version
        # but the async version in original code didn't use it.
        # I will unify to use content_length if the prompt supports it, or just ignore if it doesn't matter.
        # Assuming CLASSIFICATION_PROMPT has {content_length} placeholder.

        # Let's check CLASSIFICATION_PROMPT structure (imported from modules.prompts).
        # Since I cannot see modules.prompts now, I'll rely on what was in the original code.
        # Sync version used: filename, file_type, content_length, content
        # Async version used: filename, file_type, content (and truncated it manually)

        # I'll use the superset of arguments.
        return CLASSIFICATION_PROMPT.format(
            filename=filename,
            file_type=file_type,
            content_length=content_length,
            content=truncated_content,
        )

    async def _classify_file_api_async(self, filename: str, file_type: str, content: str) -> Dict[str, Any]:
        """실제 API 호출 로직 (비동기)"""
        try:
            # 입력 검증
            if not filename or not file_type:
                return self._create_fallback_result(filename, file_type, "파일명 누락")

            prompt = self._prepare_classification_prompt(filename, file_type, content)

            # 재시도 로직 (Exponential Backoff 적용)
            for attempt in range(3):
                try:
                    if not self.llm_client:
                        raise ValueError("LLM Client not initialized")

                    response_text = await self.llm_client.call_async(prompt)
                    return self._process_llm_response(response_text, filename, file_type)

                except Exception as e: # Catch generic exception for retry
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

            prompt = self._prepare_classification_prompt(filename, file_type, content)

            if not self.llm_client:
                 raise ValueError("LLM Client not initialized")

            response = self.llm_client.call(prompt)
            return self._process_llm_response(response, filename, file_type)

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

            prompt = VISION_PROMPT.format(filename=filename, file_type=file_type)

            # Determine mime type
            mime_types = {
                "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
                "gif": "image/gif", "webp": "image/webp",
            }
            mime_type = mime_types.get(file_type, "image/jpeg")

            response = self.llm_client.call_vision(prompt, image_data, mime_type)
            # Use shared response processor?
            # Vision prompt response likely has same structure.
            return self._process_llm_response(response, filename, file_type)

        except Exception as e:
            error_msg = f"이미지 분류 중 오류: {str(e)}"
            logger.error(error_msg, exc_info=True)
            filename = Path(image_path).name if image_path else "unknown"
            return self._create_fallback_result(filename, "image", error_msg)

    def _process_llm_response(self, response_text: str, filename: str, file_type: str) -> Dict[str, Any]:
        """Helper to process LLM response and validate folder name."""
        result = self._parse_response(response_text)

        folder_name = result.get("folder_name", "")
        validated_folder_name = self._validate_folder_name(folder_name)

        if not validated_folder_name:
            # Only log warning if it was intended to be successful but failed validation
            if result.get("status", "") != "error":
                logger.warning(f"폴더명 검증 실패: {folder_name}, 폴백 사용")
            validated_folder_name = self._create_fallback_folder_name(filename, file_type)

        result["folder_name"] = validated_folder_name
        result["status"] = ClassificationStatus.SUCCESS.value
        return result

    def check_rules(self, filename: str, file_type: str) -> Optional[Dict[str, Any]]:
        """규칙 기반 분류 (Hierarchical Filtering)"""
        file_type_lower = file_type.lower()
        filename_lower = filename.lower()

        # 1. 키워드 기반 규칙
        for keyword, folder in KEYWORD_RULES.items():
            if keyword in filename_lower:
                return {
                    "status": ClassificationStatus.SUCCESS.value,
                    "folder_name": folder,
                    "category": FILE_TYPE_MAPPING.get(file_type_lower, "기타"),
                    "confidence": 1.0,
                    "reason": f"파일명 키워드 매칭 ('{keyword}')"
                }

        # 2. 확장자 기반 규칙
        if file_type_lower in EXTENSION_RULES:
            folder_name = EXTENSION_RULES[file_type_lower]
            return {
                "status": ClassificationStatus.SUCCESS.value,
                "folder_name": folder_name,
                "category": FILE_TYPE_MAPPING.get(file_type_lower, "기타"),
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
            # Don't raise, return a partial result or let caller handle?
            # Original code raised ValueError.
            # I'll stick to raising it for now, caught by caller.
            raise ValueError(f"JSON 파싱 실패: {str(e)}")

    def _validate_folder_name(self, folder_name: str) -> Optional[str]:
        if not folder_name: return None
        cleaned = re.sub(self.FORBIDDEN_CHARS, "", folder_name).strip()
        if len(cleaned) < 2 or len(cleaned) > 30: return None
        if cleaned.lower() in self.FORBIDDEN_FOLDER_NAMES: return None
        return cleaned

    def _create_fallback_folder_name(self, filename: str, file_type: str) -> str:
        category = FILE_TYPE_MAPPING.get(file_type.lower(), "기타")
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
        category = FILE_TYPE_MAPPING.get(file_type.lower(), "기타")
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

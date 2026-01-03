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
    from openai import OpenAI, AsyncOpenAI, APIError, APIConnectionError, RateLimitError
except ImportError:
    raise ImportError("openai 패키지가 설치되지 않았습니다. 'pip install openai' 실행해주세요.")

# Optional providers
try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

try:
    import anthropic
    HAS_CLAUDE = True
except ImportError:
    HAS_CLAUDE = False

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
        """
        FileClassifier 초기화

        Args:
            api_key (Optional[str]): OpenAI API 키. None이면 환경변수에서 로드
            base_url (Optional[str]): OpenAI 호환 Base URL. None이면 환경변수에서 로드
            model (Optional[str]): 사용할 모델명. None이면 설정값 사용

        Raises:
            ValueError: API 키가 없을 경우
        """
        # API 키 설정
        self.api_key = api_key or OPENAI_API_KEY
        if not self.api_key:
            logger.error("OPENAI_API_KEY가 설정되지 않았습니다")
            raise ValueError("OPENAI_API_KEY 환경 변수가 필요합니다")

        # Base URL 설정
        self.base_url = base_url or OPENAI_BASE_URL

        # 모델 설정
        self.model = model or LLM_MODEL
        self.temperature = LLM_TEMPERATURE
        self.max_tokens = LLM_MAX_TOKENS
        self.timeout = TIMEOUT

        # OpenAI 클라이언트 초기화
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        self.async_client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

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
                    response_text = await self._call_api_async(prompt)
                    result = self._parse_response(response_text)

                    folder_name = result.get("folder_name", "")
                    validated = self._validate_folder_name(folder_name)
                    if not validated:
                        validated = self._create_fallback_folder_name(filename, file_type)

                    result["folder_name"] = validated
                    result["status"] = ClassificationStatus.SUCCESS.value
                    return result
                except RateLimitError:
                    if attempt == 2: raise
                    await asyncio.sleep(2 ** attempt) # Exponential Backoff
                except Exception as e:
                    logger.error(f"API 호출 중 오류 ({attempt+1}/3): {e}")
                    if attempt == 2: raise

        except Exception as e:
            logger.error(f"비동기 분류 실패: {e}")
            return self._create_fallback_result(filename, file_type, str(e))

    async def _call_api_async(self, prompt: str) -> str:
        """비동기 API 호출"""
        if cfg.CREDENTIAL_SOURCE == "gemini" and self.genai_configured:
             # Gemini doesn't have native async in this version maybe, verify or use thread
             return await asyncio.to_thread(self._call_gemini, prompt)
        elif cfg.CREDENTIAL_SOURCE == "claude" and self.claude_client:
             # Claude native async client check
             return await asyncio.to_thread(self._call_claude, prompt)
        elif self.async_client:
             response = await self.async_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                timeout=self.timeout,
            )
             return response.choices.message.content
        else:
             raise ValueError("No Async Client Available")

    async def classify_image_async(self, image_path: str) -> Dict[str, Any]:
        """비동기 이미지 분류"""
        return await asyncio.to_thread(self.classify_image, image_path)

    def classify_file(
        self, filename: str, file_type: str, content: str
    ) -> Dict[str, Any]:
        """
        파일을 분류합니다.

        Args:
            filename (str): 파일명
            file_type (str): 파일 타입 (확장자, 예: "pdf")
            content (str): 파일 내용

        Returns:
            Dict[str, Any]: 분류 결과
                {
                    "status": "success" | "error",
                    "folder_name": "폴더명",
                    "category": "카테고리",
                    "confidence": 0.85,
                    "reason": "이유",
                    "error": "에러메시지 (실패 시만)"
                }
        """
        logger.info(f"파일 분류 시작: {filename}")

        try:
            # 입력 검증
            if not filename or not file_type:
                error_msg = "파일명과 파일 타입이 필요합니다"
                logger.error(error_msg)
                return self._create_fallback_result(filename, file_type, error_msg)

            # 1. 계층적 필터링 (규칙 기반 분류)
            rule_based_result = self.check_rules(filename, file_type)
            if rule_based_result:
                logger.info(f"규칙 기반 분류 성공: {filename} -> {rule_based_result['folder_name']}")
                return rule_based_result

            # 콘텐츠 길이 제한 (Smart Summary 고려하여 2500자까지 허용)
            # Extractor에서 이미 요약했더라도, 여기서 한번 더 안전장치
            truncated_content = content[:MAX_CONTENT_LENGTH] if content else ""
            content_length = len(content) if content else 0

            # 프롬프트 생성
            prompt = self.CLASSIFICATION_PROMPT.format(
                filename=filename,
                file_type=file_type,
                content_length=content_length,
                content=truncated_content,
            )

            logger.debug(f"프롬프트 생성 완료 - 길이: {len(prompt)}")

            # API 호출
            response = self._call_api(prompt)

            # 응답 파싱
            result = self._parse_response(response)

            # 폴더명 검증
            folder_name = result.get("folder_name", "")
            validated_folder_name = self._validate_folder_name(folder_name)

            if not validated_folder_name:
                logger.warning(
                    f"폴더명 검증 실패: {folder_name}, 폴백 사용"
                )
                validated_folder_name = self._create_fallback_folder_name(
                    filename, file_type
                )

            result["folder_name"] = validated_folder_name
            result["status"] = ClassificationStatus.SUCCESS.value

            logger.info(
                f"분류 완료 - {filename} -> {validated_folder_name} "
                f"(신뢰도: {result.get('confidence', 0):.2f})"
            )

            return result

        except RateLimitError as e:
            error_msg = "API 레이트 제한 도달. 잠시 후 다시 시도해주세요."
            logger.error(f"{error_msg}: {str(e)}")
            return self._create_fallback_result(filename, file_type, error_msg)

        except APIConnectionError as e:
            error_msg = "OpenAI API 연결 오류"
            logger.error(f"{error_msg}: {str(e)}")
            return self._create_fallback_result(filename, file_type, error_msg)

        except APIError as e:
            error_msg = f"OpenAI API 오류: {str(e)}"
            logger.error(error_msg)
            return self._create_fallback_result(filename, file_type, error_msg)

        except Exception as e:
            error_msg = f"분류 중 오류 발생: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return self._create_fallback_result(filename, file_type, error_msg)

    def check_rules(self, filename: str, file_type: str) -> Optional[Dict[str, Any]]:
        """
        규칙 기반 분류 (Hierarchical Filtering)

        Args:
            filename (str): 파일명
            file_type (str): 파일 확장자 (점 제외)

        Returns:
            Optional[Dict[str, Any]]: 분류 결과가 있으면 반환, 없으면 None
        """
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

    def classify_image(self, image_path: str) -> Dict[str, Any]:
        """
        이미지를 Vision API를 사용하여 분류합니다.

        Args:
            image_path (str): 이미지 파일 경로

        Returns:
            Dict[str, Any]: 분류 결과
        """
        logger.info(f"이미지 분류 시작: {image_path}")

        try:
            # 파일 존재 확인
            if not Path(image_path).exists():
                error_msg = f"파일을 찾을 수 없습니다: {image_path}"
                logger.error(error_msg)
                return self._create_error_result(error_msg)

            filename = Path(image_path).name
            file_type = Path(image_path).suffix.lstrip(".").lower()

            # 1. 계층적 필터링 (규칙 기반 분류)
            rule_based_result = self.check_rules(filename, file_type)
            if rule_based_result:
                 logger.info(f"규칙 기반 이미지 분류 성공: {filename} -> {rule_based_result['folder_name']}")
                 return rule_based_result

            # 이미지 파일 확인
            if not self._is_image_file(file_type):
                error_msg = f"이미지 파일이 아닙니다: {filename}"
                logger.error(error_msg)
                return self._create_fallback_result(filename, file_type, error_msg)

            # 이미지를 Base64로 인코딩
            image_data = self._encode_image_to_base64(image_path)

            # 프롬프트 생성
            prompt = self.VISION_PROMPT.format(
                filename=filename,
                file_type=file_type,
            )

            # Vision API 호출
            response = self._call_vision_api(prompt, image_data, file_type)

            # 응답 파싱
            result = self._parse_response(response)

            # 폴더명 검증
            folder_name = result.get("folder_name", "")
            validated_folder_name = self._validate_folder_name(folder_name)

            if not validated_folder_name:
                validated_folder_name = self._create_fallback_folder_name(
                    filename, file_type
                )

            result["folder_name"] = validated_folder_name
            result["status"] = ClassificationStatus.SUCCESS.value

            logger.info(
                f"이미지 분류 완료 - {filename} -> {validated_folder_name}"
            )

            return result

        except Exception as e:
            error_msg = f"이미지 분류 중 오류: {str(e)}"
            logger.error(error_msg, exc_info=True)
            filename = Path(image_path).name if image_path else "unknown"
            file_type = "image"
            return self._create_fallback_result(filename, file_type, error_msg)

    def _call_api(self, prompt: str) -> str:
        """
        설정된 LLM API를 호출합니다.

        Args:
            prompt (str): 프롬프트

        Returns:
            str: API 응답 텍스트
        """
        logger.debug(f"API 호출 - 모델: {self.model}, 소스: {cfg.CREDENTIAL_SOURCE}")

        if cfg.CREDENTIAL_SOURCE == "gemini" and self.genai_configured:
            return self._call_gemini(prompt)
        elif cfg.CREDENTIAL_SOURCE == "claude" and self.claude_client:
            return self._call_claude(prompt)
        elif self.client:
            return self._call_openai(prompt)
        else:
            raise ValueError("사용 가능한 LLM 클라이언트가 없습니다.")

    def _call_openai(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            timeout=self.timeout,
        )
        return response.choices.message.content

    def _call_gemini(self, prompt: str) -> str:
        try:
            # gemini-pro 등 모델명 매핑 또는 그대로 사용
            model_name = self.model if "gemini" in self.model else "gemini-pro"
            model = genai.GenerativeModel(model_name)

            # Generation Config
            generation_config = genai.types.GenerationConfig(
                temperature=self.temperature,
                max_output_tokens=self.max_tokens
            )

            response = model.generate_content(prompt, generation_config=generation_config)
            return response.text
        except Exception as e:
            logger.error(f"Gemini API Error: {e}")
            raise

    def _call_claude(self, prompt: str) -> str:
        try:
            # Claude 3 모델명 확인 (claude-3-opus-20240229, claude-3-sonnet-20240229, etc)
            model_name = self.model if "claude" in self.model else "claude-3-haiku-20240307"

            message = self.claude_client.messages.create(
                model=model_name,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return message.content[0].text
        except Exception as e:
            logger.error(f"Claude API Error: {e}")
            raise

    def _call_vision_api(
        self, prompt: str, image_data: str, image_type: str
    ) -> str:
        """
        OpenAI Vision API를 호출합니다.

        Args:
            prompt (str): 프롬프트
            image_data (str): Base64 인코딩된 이미지
            image_type (str): 이미지 타입 (확장자)

        Returns:
            str: API 응답 텍스트
        """
        logger.debug(f"Vision API 호출 - 이미지 타입: {image_type}")

        # MIME 타입 결정
        mime_types = {
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "gif": "image/gif",
            "webp": "image/webp",
        }
        mime_type = mime_types.get(image_type, "image/jpeg")

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_data}"
                            },
                        },
                    ],
                }
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            timeout=self.timeout,
        )

        return response.choices.message.content

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """
        LLM 응답을 JSON으로 파싱합니다.

        Args:
            response_text (str): LLM 응답 텍스트

        Returns:
            Dict[str, Any]: 파싱된 JSON

        Raises:
            ValueError: 파싱 실패 시
        """
        try:
            # 마크다운 코드블록 제거
            cleaned = re.sub(r"```(?:json)?\n?", "", response_text)
            cleaned = cleaned.strip()

            # JSON 파싱
            result = json.loads(cleaned)

            # 필수 필드 검증
            required_fields = ["folder_name", "category", "confidence", "reason"]
            for field in required_fields:
                if field not in result:
                    logger.warning(f"필수 필드 누락: {field}")
                    if field == "confidence":
                        result[field] = 0.5
                    else:
                        result[field] = ""

            return result

        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 실패: {str(e)}")
            logger.debug(f"응답 텍스트: {response_text}")
            raise ValueError(f"JSON 파싱 실패: {str(e)}")

    def _validate_folder_name(self, folder_name: str) -> Optional[str]:
        """
        폴더명의 유효성을 검사합니다.

        Args:
            folder_name (str): 검사할 폴더명

        Returns:
            Optional[str]: 검증된 폴더명 (유효하지 않으면 None)
        """
        if not folder_name:
            return None

        # 금지된 문자 제거
        cleaned = re.sub(self.FORBIDDEN_CHARS, "", folder_name)

        # 공백 제거
        cleaned = cleaned.strip()

        # 길이 확인
        if len(cleaned) < 2 or len(cleaned) > 30:
            logger.warning(
                f"폴더명 길이 부적절: {len(cleaned)} (2-30 범위)"
            )
            return None

        # 시스템 예약어 확인
        if cleaned.lower() in self.FORBIDDEN_FOLDER_NAMES:
            logger.warning(f"시스템 예약어: {cleaned}")
            return None

        return cleaned

    def _create_fallback_folder_name(self, filename: str, file_type: str) -> str:
        """
        API 오류 시 폴백 폴더명을 생성합니다.

        Args:
            filename (str): 파일명
            file_type (str): 파일 타입

        Returns:
            str: 생성된 폴더명
        """
        logger.debug(f"폴백 폴더명 생성 - 파일: {filename}, 타입: {file_type}")

        # 파일 타입으로 기본 분류
        category = self.FILE_TYPE_MAPPING.get(file_type.lower(), "기타")

        # 파일명에서 의미있는 부분 추출
        name_without_ext = Path(filename).stem
        cleaned_name = re.sub(self.FORBIDDEN_CHARS, "", name_without_ext)
        cleaned_name = cleaned_name.strip()[:20]

        if cleaned_name and len(cleaned_name) >= 2:
            return cleaned_name

        return category

    def _create_error_result(self, error_msg: str) -> Dict[str, Any]:
        """
        에러 결과를 생성합니다.

        Args:
            error_msg (str): 에러 메시지

        Returns:
            Dict[str, Any]: 에러 결과
        """
        return {
            "status": ClassificationStatus.ERROR.value,
            "folder_name": "기타",
            "category": "기타",
            "confidence": 0.0,
            "reason": "분류 실패",
            "error": error_msg,
        }

    def _create_fallback_result(
        self, filename: str, file_type: str, error_msg: str
    ) -> Dict[str, Any]:
        """
        폴백 분류 결과를 생성합니다.

        Args:
            filename (str): 파일명
            file_type (str): 파일 타입
            error_msg (str): 에러 메시지

        Returns:
            Dict[str, Any]: 폴백 분류 결과
        """
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
        """
        이미지 파일인지 확인합니다.

        Args:
            file_type (str): 파일 타입 (확장자)

        Returns:
            bool: 이미지 파일 여부
        """
        image_types = {
            "jpg",
            "jpeg",
            "png",
            "gif",
            "bmp",
            "svg",
            "webp",
        }
        return file_type.lower() in image_types

    def _encode_image_to_base64(self, image_path: str) -> str:
        """
        이미지 파일을 Base64로 인코딩합니다.

        Args:
            image_path (str): 이미지 파일 경로

        Returns:
            str: Base64 인코딩된 이미지
        """
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    def _check_rules(self, filename: str, file_type: str) -> Optional[Dict[str, Any]]:
        """
        규칙 기반 분류를 수행합니다.

        Args:
            filename (str): 파일명
            file_type (str): 파일 타입

        Returns:
            Optional[Dict[str, Any]]: 분류 결과 (매칭되는 규칙이 없으면 None)
        """
        # 1. 명확한 확장자 규칙
        extension_rules = {
            "mp3": "음악", "wav": "음악", "flac": "음악",
            "mp4": "비디오", "avi": "비디오", "mkv": "비디오",
            "zip": "압축파일", "rar": "압축파일", "7z": "압축파일",
            "exe": "설치파일", "msi": "설치파일", "apk": "설치파일",
            "py": "소스코드", "js": "소스코드", "html": "소스코드", "css": "소스코드"
        }

        lower_type = file_type.lower()
        if lower_type in extension_rules:
            folder_name = extension_rules[lower_type]
            return {
                "status": ClassificationStatus.SUCCESS.value,
                "folder_name": folder_name,
                "category": self.FILE_TYPE_MAPPING.get(lower_type, "기타"),
                "confidence": 1.0,
                "reason": f"확장자 규칙 ({lower_type})"
            }

        # 2. 키워드 규칙 (파일명에 특정 단어가 포함된 경우)
        keyword_rules = [
            (r"(?i)invoice|영수증|bill|receipt", "영수증"),
            (r"(?i)contract|계약서", "계약서"),
            (r"(?i)manual|매뉴얼|사용설명서", "매뉴얼"),
            (r"(?i)schedule|일정표|계획표", "일정"),
            (r"(?i)screenshot|스크린샷", "스크린샷"),
            (r"(?i)scan|스캔", "스캔문서"),
        ]

        for pattern, folder in keyword_rules:
            if re.search(pattern, filename):
                return {
                    "status": ClassificationStatus.SUCCESS.value,
                    "folder_name": folder,
                    "category": "문서",
                    "confidence": 0.95,
                    "reason": f"키워드 규칙 ({folder})"
                }

        return None

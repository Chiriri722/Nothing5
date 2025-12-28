# -*- coding: utf-8 -*-
"""
로깅 설정 모듈 (레거시 지원)

이 모듈은 modules/logger.py로 이동되었습니다.
기존 코드와의 호환성을 위해 유지됩니다.
"""

import logging
from modules.logger import AppLogger

def setup_logging() -> None:
    """애플리케이션 전역 로깅 설정을 초기화합니다."""
    AppLogger.initialize()

def get_logger(name: str = None) -> logging.Logger:
    """모듈별 로거 인스턴스를 반환합니다."""
    if name is None:
        return AppLogger.get_logger()
    return logging.getLogger(name)

def log_file_processing(filename: str, status: str) -> None:
    """파일 처리 과정을 로깅합니다."""
    logger = get_logger(__name__)
    if status == "started":
        logger.info(f"파일 처리 시작: {filename}")
    elif status == "completed":
        logger.info(f"파일 처리 완료: {filename}")
    elif status == "failed":
        logger.warning(f"파일 처리 실패: {filename}")
    else:
        logger.debug(f"파일 처리 상태 변경 - {filename}: {status}")

def log_classification_result(
    filename: str, category: str, confidence: float
) -> None:
    """분류 결과를 로깅합니다."""
    logger = get_logger(__name__)
    logger.info(
        f"분류 완료 - 파일: {filename}, "
        f"카테고리: {category}, 신뢰도: {confidence:.2%}"
    )

def log_error_with_context(error: Exception, context_info: dict) -> None:
    """컨텍스트 정보와 함께 에러를 로깅합니다."""
    logger = get_logger(__name__)
    logger.error(
        f"에러 발생: {error.__class__.__name__} - {error} (컨텍스트: {context_info})",
        exc_info=True
    )

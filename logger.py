"""중앙화된 로깅 모듈

file-classifier 애플리케이션의 모든 모듈이 사용할 구조화된 로깅을 제공합니다.
파이썬 표준 logging 모듈을 기반으로 하며, 다음 기능을 포함합니다:

- 중앙화된 로깅 설정
- 다중 핸들러 (콘솔과 파일)
- 로그 로테이션 (RotatingFileHandler)
- 일관된 타임스탬프 포맷
- 모듈별 로거 지원
- 민감한 정보 보호
"""

import logging
import logging.handlers
from pathlib import Path
from typing import Optional

from config.config import (
    LOG_LEVEL,
    LOG_DIR,
    LOG_FILE_PATH,
    LOG_MAX_BYTES,
    LOG_BACKUP_COUNT,
    LOG_FORMAT,
    LOG_DATE_FORMAT,
    CONSOLE_LOG_LEVEL,
    FILE_LOG_LEVEL,
)

# 전역 로깅 설정 완료 여부
_LOGGING_CONFIGURED = False


class LoggerConfig:
    """애플리케이션 로깅 설정을 관리하는 클래스
    
    로그 디렉토리 생성, 핸들러 설정, 포매터 적용 등을
    중앙화하여 관리합니다.
    """

    @staticmethod
    def _ensure_log_directory() -> None:
        """로그 디렉토리가 없으면 생성합니다."""
        try:
            LOG_DIR.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise RuntimeError(f"로그 디렉토리 생성 실패: {LOG_DIR} - {e}")

    @staticmethod
    def _create_console_handler(level: str) -> logging.StreamHandler:
        """콘솔 핸들러를 생성합니다.
        
        Args:
            level: 로그 레벨 (예: 'INFO', 'DEBUG')
            
        Returns:
            StreamHandler 인스턴스
        """
        handler = logging.StreamHandler()
        handler.setLevel(getattr(logging, level.upper()))
        
        formatter = logging.Formatter(
            fmt=LOG_FORMAT,
            datefmt=LOG_DATE_FORMAT
        )
        handler.setFormatter(formatter)
        return handler

    @staticmethod
    def _create_file_handler(level: str) -> logging.handlers.RotatingFileHandler:
        """회전하는 파일 핸들러를 생성합니다.
        
        maxBytes만큼 파일이 커지면 자동으로 회전하며,
        backupCount만큼의 이전 파일들을 보관합니다.
        
        Args:
            level: 로그 레벨 (예: 'DEBUG', 'INFO')
            
        Returns:
            RotatingFileHandler 인스턴스
        """
        handler = logging.handlers.RotatingFileHandler(
            filename=LOG_FILE_PATH,
            maxBytes=LOG_MAX_BYTES,
            backupCount=LOG_BACKUP_COUNT,
            encoding='utf-8'
        )
        handler.setLevel(getattr(logging, level.upper()))
        
        formatter = logging.Formatter(
            fmt=LOG_FORMAT,
            datefmt=LOG_DATE_FORMAT
        )
        handler.setFormatter(formatter)
        return handler

    @staticmethod
    def setup() -> None:
        """애플리케이션 전역 로깅을 설정합니다.
        
        루트 로거를 설정하고, 콘솔 및 파일 핸들러를 추가합니다.
        이 함수는 애플리케이션 시작 시점에 한 번만 호출되어야 합니다.
        """
        global _LOGGING_CONFIGURED
        
        if _LOGGING_CONFIGURED:
            return
        
        try:
            # 로그 디렉토리 생성
            LoggerConfig._ensure_log_directory()
            
            # 루트 로거 설정
            root_logger = logging.getLogger()
            root_logger.setLevel(getattr(logging, LOG_LEVEL.upper()))
            
            # 기존 핸들러 제거 (중복 설정 방지)
            for handler in root_logger.handlers[:]:
                root_logger.removeHandler(handler)
            
            # 콘솔 핸들러 추가
            console_handler = LoggerConfig._create_console_handler(CONSOLE_LOG_LEVEL)
            root_logger.addHandler(console_handler)
            
            # 파일 핸들러 추가
            file_handler = LoggerConfig._create_file_handler(FILE_LOG_LEVEL)
            root_logger.addHandler(file_handler)
            
            _LOGGING_CONFIGURED = True
            
            # 초기 로깅 메시지
            root_logger.debug("로깅 시스템이 초기화되었습니다")
            root_logger.debug(f"로그 파일 경로: {LOG_FILE_PATH}")
            
        except Exception as e:
            raise RuntimeError(f"로깅 설정 실패: {e}")


def setup_logging() -> None:
    """애플리케이션 전역 로깅 설정을 초기화합니다.
    
    이 함수는 main() 또는 애플리케이션 진입점에서
    가장 먼저 호출되어야 합니다.
    
    Example:
        >>> from logger import setup_logging, get_logger
        >>> setup_logging()
        >>> logger = get_logger(__name__)
        >>> logger.info("애플리케이션 시작")
    """
    LoggerConfig.setup()


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """모듈별 로거 인스턴스를 반환합니다.
    
    이 함수는 각 모듈에서 호출되어 모듈별 로거를 얻을 수 있습니다.
    반드시 setup_logging()이 먼저 호출되어야 합니다.
    
    Args:
        name: 로거 이름. 보통 __name__을 전달합니다.
              None이면 루트 로거를 반환합니다.
    
    Returns:
        logging.Logger 인스턴스
    
    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("현재 모듈의 로거 사용")
    """
    # 로깅이 아직 설정되지 않았다면 자동으로 설정
    if not _LOGGING_CONFIGURED:
        setup_logging()
    
    return logging.getLogger(name)


def log_file_processing(filename: str, status: str) -> None:
    """파일 처리 과정을 로깅합니다.
    
    Args:
        filename: 처리 중인 파일명
        status: 처리 상태 (예: 'started', 'completed', 'failed')
    
    Example:
        >>> log_file_processing("document.pdf", "started")
    """
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
    """분류 결과를 로깅합니다.
    
    Args:
        filename: 분류된 파일명
        category: 분류 카테고리
        confidence: 분류 신뢰도 (0.0 ~ 1.0)
    
    Example:
        >>> log_classification_result("photo.jpg", "image", 0.95)
    """
    logger = get_logger(__name__)
    logger.info(
        f"분류 완료 - 파일: {filename}, "
        f"카테고리: {category}, 신뢰도: {confidence:.2%}"
    )


def log_error_with_context(error: Exception, context_info: dict) -> None:
    """컨텍스트 정보와 함께 에러를 로깅합니다.
    
    민감한 정보(API 키, 패스워드 등)는 자동으로 마스킹됩니다.
    
    Args:
        error: 발생한 예외
        context_info: 컨텍스트 정보를 담은 딕셔너리
                     (민감한 정보 제외)
    
    Example:
        >>> try:
        ...     # 어떤 작업
        ... except Exception as e:
        ...     log_error_with_context(
        ...         e,
        ...         {"filename": "test.pdf", "action": "classification"}
        ...     )
    """
    logger = get_logger(__name__)
    
    # 민감한 정보 마스킹
    sanitized_context = _sanitize_context(context_info)
    
    logger.error(
        f"에러 발생: {error.__class__.__name__} - {error} "
        f"(컨텍스트: {sanitized_context})",
        exc_info=True
    )


def _sanitize_context(context: dict) -> dict:
    """컨텍스트 정보에서 민감한 정보를 마스킹합니다.
    
    Args:
        context: 원본 컨텍스트 딕셔너리
    
    Returns:
        마스킹된 컨텍스트 딕셔너리
    """
    sensitive_keys = {'api_key', 'password', 'token', 'secret', 'key'}
    sanitized = {}
    
    for key, value in context.items():
        if any(sensitive in key.lower() for sensitive in sensitive_keys):
            # API 키나 패스워드는 마스킹
            sanitized[key] = "***MASKED***"
        else:
            sanitized[key] = value
    
    return sanitized


if __name__ == "__main__":
    # 테스트 코드
    setup_logging()
    
    logger = get_logger(__name__)
    
    logger.debug("DEBUG 레벨 메시지")
    logger.info("INFO 레벨 메시지")
    logger.warning("WARNING 레벨 메시지")
    logger.error("ERROR 레벨 메시지")
    
    # 함수별 로깅 테스트
    log_file_processing("test_document.pdf", "started")
    log_classification_result("photo.jpg", "image", 0.95)
    
    try:
        raise ValueError("테스트용 에러")
    except Exception as e:
        log_error_with_context(
            e,
            {"filename": "test.pdf", "api_key": "secret_key_123"}
        )

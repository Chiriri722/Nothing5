# -*- coding: utf-8 -*-
"""
로깅 모듈

파일 분류 프로그램의 로그 기록을 관리합니다.
콘솔 및 파일 기반 로깅을 지원합니다.
"""

import logging
import logging.handlers
from pathlib import Path
from typing import Optional


class LoggerConfig:
    """
    로거 설정 클래스
    
    로그 레벨, 형식, 출력 방식을 설정하고 관리합니다.
    """
    
    def __init__(
        self,
        name: str,
        log_level: str = "INFO",
        log_file: Optional[str] = None,
        max_bytes: int = 10485760,  # 10MB
        backup_count: int = 5
    ):
        """
        LoggerConfig 초기화
        
        Args:
            name (str): 로거 이름
            log_level (str): 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_file (Optional[str]): 로그 파일 경로
            max_bytes (int): 로그 파일 최대 크기
            backup_count (int): 백업 로그 파일 개수
        """
        self.logger = logging.getLogger(name)
        self.log_level = getattr(logging, log_level.upper(), logging.INFO)
        self.logger.setLevel(self.log_level)
        
        # 로그 포매터 설정
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 콘솔 핸들러 추가
        self._add_console_handler(formatter)
        
        # 파일 핸들러 추가
        if log_file:
            self._add_file_handler(log_file, formatter, max_bytes, backup_count)
    
    def _add_console_handler(self, formatter: logging.Formatter) -> None:
        """
        콘솔 핸들러 추가
        
        Args:
            formatter (logging.Formatter): 로그 포매터
        """
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self.log_level)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
    
    def _add_file_handler(
        self,
        log_file: str,
        formatter: logging.Formatter,
        max_bytes: int,
        backup_count: int
    ) -> None:
        """
        파일 핸들러 추가
        
        Args:
            log_file (str): 로그 파일 경로
            formatter (logging.Formatter): 로그 포매터
            max_bytes (int): 파일 최대 크기
            backup_count (int): 백업 개수
        """
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(self.log_level)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
    
    def get_logger(self) -> logging.Logger:
        """
        로거 객체 반환
        
        Returns:
            logging.Logger: 설정된 로거
        """
        return self.logger
    
    def set_level(self, level: str) -> None:
        """
        로그 레벨 변경
        
        Args:
            level (str): 로그 레벨
        """
        log_level = getattr(logging, level.upper(), logging.INFO)
        self.logger.setLevel(log_level)
        
        for handler in self.logger.handlers:
            handler.setLevel(log_level)


class AppLogger:
    """
    애플리케이션 전역 로거 클래스
    
    전체 애플리케이션에서 사용할 공통 로거를 제공합니다.
    """
    
    _instance: Optional['AppLogger'] = None
    _logger_config: Optional[LoggerConfig] = None
    
    def __new__(cls) -> 'AppLogger':
        """싱글톤 패턴 구현"""
        if cls._instance is None:
            cls._instance = super(AppLogger, cls).__new__(cls)
        return cls._instance
    
    @classmethod
    def initialize(
        cls,
        name: str = "FileClassifier",
        log_level: str = "INFO",
        log_file: Optional[str] = None
    ) -> 'AppLogger':
        """
        로거 초기화
        
        Args:
            name (str): 로거 이름
            log_level (str): 로그 레벨
            log_file (Optional[str]): 로그 파일 경로
            
        Returns:
            AppLogger: 싱글톤 인스턴스
        """
        instance = cls()
        if cls._logger_config is None:
            cls._logger_config = LoggerConfig(
                name=name,
                log_level=log_level,
                log_file=log_file
            )
        return instance
    
    @classmethod
    def get_logger(cls) -> logging.Logger:
        """
        로거 객체 반환
        
        Returns:
            logging.Logger: 설정된 로거
        """
        if cls._logger_config is None:
            cls.initialize()
        return cls._logger_config.get_logger()
    
    @classmethod
    def set_level(cls, level: str) -> None:
        """
        로그 레벨 변경
        
        Args:
            level (str): 로그 레벨
        """
        if cls._logger_config:
            cls._logger_config.set_level(level)


if __name__ == "__main__":
    logger = AppLogger.initialize(log_level="DEBUG")
    log = AppLogger.get_logger()
    
    log.debug("디버그 메시지")
    log.info("정보 메시지")
    log.warning("경고 메시지")
    log.error("오류 메시지")
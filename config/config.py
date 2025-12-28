# -*- coding: utf-8 -*-
"""
파일 분류 프로그램 설정 모듈

LLM 기반 파일 분류 프로그램의 전역 설정값을 정의합니다.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# .env 파일에서 환경 변수 로드
load_dotenv()

# ========================
# 기본 경로 설정
# ========================
PROJECT_ROOT = Path(__file__).parent.parent
LOGS_DIR = PROJECT_ROOT / "logs"
UNDO_HISTORY_FILE = PROJECT_ROOT / "undo_history.json"

# 로그 디렉토리 생성
LOGS_DIR.mkdir(exist_ok=True)

# ========================
# LLM 설정
# ========================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
LLM_MODEL = "gpt-3.5-turbo"  # 또는 "gpt-4"
LLM_TEMPERATURE = 0.7
LLM_MAX_TOKENS = 500

# ========================
# 파일 분류 설정
# ========================
DEFAULT_CATEGORIES = [
    "문서",
    "이미지",
    "비디오",
    "오디오",
    "압축파일",
    "코드",
    "기타"
]

# 지원하는 파일 확장자
SUPPORTED_EXTENSIONS = {
    "document": [".pdf", ".docx", ".doc", ".txt", ".xlsx", ".xls"],
    "image": [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg"],
    "video": [".mp4", ".avi", ".mov", ".mkv", ".flv"],
    "audio": [".mp3", ".wav", ".flac", ".aac", ".m4a"],
    "archive": [".zip", ".rar", ".7z", ".tar", ".gz"],
    "code": [".py", ".js", ".java", ".cpp", ".c", ".html", ".css"]
}

# ========================
# 파일 모니터링 설정
# ========================
MONITOR_ENABLED = True
MONITOR_INTERVAL = 5  # 초 단위
MONITOR_DEBOUNCE_TIME = 1  # 초 단위

# ========================
# 로깅 설정
# ========================
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_FILE = LOGS_DIR / "file_classifier.log"
LOG_FILE_PATH = str(LOGS_DIR / "file_classifier.log")
LOG_DIR = LOGS_DIR  # logger.py를 위한 호환성
LOG_MAX_BYTES = 10485760  # 10MB
LOG_BACKUP_COUNT = 5
CONSOLE_LOG_LEVEL = "INFO"
FILE_LOG_LEVEL = "DEBUG"

# ========================
# GUI 설정
# ========================
GUI_WINDOW_WIDTH = 800
GUI_WINDOW_HEIGHT = 600
GUI_THEME = "default"

# ========================
# 파일 처리 설정
# ========================
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
CHUNK_SIZE = 1024 * 1024  # 1MB

# 파일 이동 시 충돌 처리 방식
# "skip": 기존 파일 유지
# "overwrite": 기존 파일 덮어쓰기
# "rename": 새 파일명 생성
FILE_CONFLICT_STRATEGY = "rename"

# ========================
# 성능 설정
# ========================
MAX_WORKERS = 4  # 동시 처리 스레드 수
TIMEOUT = 30  # API 요청 타임아웃 (초)

# ========================
# 유효성 검사
# ========================
def validate_config():
    """설정값 유효성 검사"""
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")
    
    if LLM_TEMPERATURE < 0 or LLM_TEMPERATURE > 2:
        raise ValueError("LLM_TEMPERATURE는 0~2 사이의 값이어야 합니다.")
    
    if MAX_WORKERS < 1:
        raise ValueError("MAX_WORKERS는 1 이상이어야 합니다.")
    
    return True


if __name__ == "__main__":
    # 설정 테스트
    print("프로젝트 루트:", PROJECT_ROOT)
    print("로그 디렉토리:", LOGS_DIR)
    print("LLM 모델:", LLM_MODEL)
    print("지원 카테고리:", DEFAULT_CATEGORIES)
    print("설정 유효성:", validate_config())
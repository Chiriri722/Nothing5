# -*- coding: utf-8 -*-
"""
파일 분류 프로그램 설정 모듈

LLM 기반 파일 분류 프로그램의 전역 설정값을 정의합니다.
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv

# .env 파일에서 환경 변수 로드
load_dotenv()

# ========================
# 기본 경로 설정
# ========================
import sys
if getattr(sys, 'frozen', False):
    # PyInstaller로 빌드된 경우 실행 파일 위치 기준
    PROJECT_ROOT = Path(sys.executable).parent
else:
    # 일반 실행 시 현재 파일 기준
    PROJECT_ROOT = Path(__file__).parent.parent

LOGS_DIR = PROJECT_ROOT / "logs"
UNDO_HISTORY_FILE = PROJECT_ROOT / "undo_history.json"
USER_SETTINGS_FILE = PROJECT_ROOT / "user_settings.json"

# 로그 디렉토리 생성
LOGS_DIR.mkdir(exist_ok=True)

# ========================
# LLM 설정
# ========================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
LLM_MODEL = "gpt-3.5-turbo"  # 기본 모델
LLM_TEMPERATURE = 0.7
LLM_MAX_TOKENS = 500

# 자격 증명 소스 설정 (기본값: 'openai' - 환경변수)
# options: 'openai', 'gemini', 'claude', 'manual'
CREDENTIAL_SOURCE = "openai"
MANUAL_API_KEY = "" # 수동 입력 시 저장될 키

# 사용자 설정 파일 로드 (있다면)
if USER_SETTINGS_FILE.exists():
    try:
        with open(USER_SETTINGS_FILE, 'r', encoding='utf-8') as f:
            user_settings = json.load(f)
            CREDENTIAL_SOURCE = user_settings.get("CREDENTIAL_SOURCE", CREDENTIAL_SOURCE)
            MANUAL_API_KEY = user_settings.get("MANUAL_API_KEY", MANUAL_API_KEY)

            # 저장된 모델이 있으면 복원 (옵션)
            if "LLM_MODEL" in user_settings:
                LLM_MODEL = user_settings["LLM_MODEL"]

    except Exception as e:
        print(f"Failed to load user settings: {e}")

# 자격 증명 소스에 따른 API 키 및 모델 초기화
# 모듈 로딩 시점에 실행됨. 의존성 문제를 피하기 위해 CredentialManager는 이 블록 안에서만 임포트 시도.
try:
    if CREDENTIAL_SOURCE in ["gemini", "claude"]:
        # 로컬 임포트로 순환 참조 방지
        # 주의: config.py는 프로젝트 전역에서 임포트되므로, modules 패키지가 import 가능한 상태여야 함.
        # sys.path 설정이 완료된 상태라고 가정.
        from modules.credential_manager import CredentialManager
        cm = CredentialManager()

        if CREDENTIAL_SOURCE == "gemini":
            key = cm.detect_gemini_credentials()
            if key:
                OPENAI_API_KEY = key
                # 모델이 기본값이면 Gemini 모델로 변경
                if LLM_MODEL.startswith("gpt-"):
                     LLM_MODEL = "gemini-pro"
        elif CREDENTIAL_SOURCE == "claude":
            key = cm.detect_claude_credentials()
            if key:
                OPENAI_API_KEY = key
                if LLM_MODEL.startswith("gpt-"):
                    LLM_MODEL = "claude-3-opus-20240229" # 또는 적절한 기본값

    elif CREDENTIAL_SOURCE == "manual" and MANUAL_API_KEY:
        OPENAI_API_KEY = MANUAL_API_KEY

except ImportError:
    # modules를 아직 찾을 수 없는 초기 단계일 수 있음 (setup.py 실행 중 등)
    # 이 경우 무시하고 넘어감
    pass
except Exception as e:
    print(f"Error loading credentials in config: {e}")

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
    # API 키 검사는 실행 시점의 동적 로딩을 위해 여기서 제거하거나 완화할 수 있음
    # 하지만 현재 구조상 Classifier 초기화 시 필요하므로,
    # 동적으로 키를 가져오는 로직이 추가되면 이 부분은 수정되어야 함.
    # 일단 경고만 하거나 패스하도록 수정.
    pass
    
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
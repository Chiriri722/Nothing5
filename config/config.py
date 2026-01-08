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
PROJECT_ROOT = Path(__file__).parent.parent
LOGS_DIR = PROJECT_ROOT / "logs"
UNDO_HISTORY_FILE = PROJECT_ROOT / "undo_history.json"
USER_SETTINGS_FILE = PROJECT_ROOT / "user_settings.json"
ENV_FILE = PROJECT_ROOT / ".env"

# 로그 디렉토리 생성
LOGS_DIR.mkdir(exist_ok=True)

# ========================
# LLM 설정
# ========================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
LLM_TEMPERATURE = 0.7
LLM_MAX_TOKENS = 500

# 자격 증명 소스 설정 (기본값: 'openai' - 환경변수)
# options: 'openai', 'gemini', 'claude', 'manual'
CREDENTIAL_SOURCE = "openai"
MANUAL_API_KEY = "" # 수동 입력 시 저장될 키

# ========================
# 사용자 설정 (기본값)
# ========================
LANGUAGE = "한국어"
RECURSIVE_SEARCH = False
MONITOR_INTERVAL = 5

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
MONITOR_DEBOUNCE_TIME = 1

# ========================
# 로깅 설정
# ========================
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_FILE = LOGS_DIR / "file_classifier.log"
LOG_FILE_PATH = str(LOGS_DIR / "file_classifier.log")
LOG_DIR = LOGS_DIR
LOG_MAX_BYTES = 10485760
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
MAX_FILE_SIZE = 100 * 1024 * 1024
MAX_CONTENT_LENGTH = 2500
CHUNK_SIZE = 1024 * 1024
FILE_CONFLICT_STRATEGY = "rename"

# ========================
# 성능 설정
# ========================
MAX_WORKERS = 4  # 동시 처리 스레드 수
TIMEOUT = 30  # API 요청 타임아웃 (초)
MAX_CONCURRENT_FILE_PROCESSING = 20 # 동시에 처리할 파일 수 (추출/이동)
MAX_CONCURRENT_API_CALLS = 5 # 동시에 실행할 API 호출 수

# ========================
# 초기화 함수
# ========================
def load_settings():
    """사용자 설정을 로드합니다."""
    global CREDENTIAL_SOURCE, MANUAL_API_KEY, LANGUAGE, RECURSIVE_SEARCH, MONITOR_INTERVAL, LLM_MODEL

    if USER_SETTINGS_FILE.exists():
        try:
            with open(USER_SETTINGS_FILE, 'r', encoding='utf-8') as f:
                user_settings = json.load(f)
                CREDENTIAL_SOURCE = user_settings.get("CREDENTIAL_SOURCE", CREDENTIAL_SOURCE)
                MANUAL_API_KEY = user_settings.get("MANUAL_API_KEY", MANUAL_API_KEY)
                LANGUAGE = user_settings.get("LANGUAGE", LANGUAGE)
                RECURSIVE_SEARCH = user_settings.get("RECURSIVE_SEARCH", RECURSIVE_SEARCH)
                MONITOR_INTERVAL = user_settings.get("MONITOR_INTERVAL", MONITOR_INTERVAL)

                if "LLM_MODEL" in user_settings:
                    LLM_MODEL = user_settings["LLM_MODEL"]

        except Exception as e:
            print(f"Failed to load user settings: {e}")

def load_credentials():
    """자격 증명 소스에 따른 API 키를 로드합니다. (Lazy Loading)"""
    global OPENAI_API_KEY, LLM_MODEL

    # 먼저 설정을 로드하여 CREDENTIAL_SOURCE를 최신화
    load_settings()

    try:
        if CREDENTIAL_SOURCE in ["gemini", "claude"]:
            from modules.credential_manager import CredentialManager
            cm = CredentialManager()

            if CREDENTIAL_SOURCE == "gemini":
                key = cm.detect_gemini_credentials()
                if key:
                    OPENAI_API_KEY = key
                    if LLM_MODEL.startswith("gpt-"):
                         LLM_MODEL = "gemini-pro"
            elif CREDENTIAL_SOURCE == "claude":
                key = cm.detect_claude_credentials()
                if key:
                    OPENAI_API_KEY = key
                    if LLM_MODEL.startswith("gpt-"):
                        LLM_MODEL = "claude-3-opus-20240229"

        elif CREDENTIAL_SOURCE == "manual" and MANUAL_API_KEY:
            OPENAI_API_KEY = MANUAL_API_KEY

    except ImportError:
        pass
    except Exception as e:
        print(f"Error loading credentials in config: {e}")

# ========================
# 유틸리티 함수
# ========================
def validate_config():
    """설정값 유효성 검사"""
    if not OPENAI_API_KEY:
        raise ValueError(
            "API 키가 설정되지 않았습니다. \n"
            ".env 파일 또는 설정 메뉴에서 OPENAI_API_KEY (또는 다른 제공자의 API Key)를 설정해주세요."
        )
    
    if LLM_TEMPERATURE < 0 or LLM_TEMPERATURE > 2:
        raise ValueError("LLM_TEMPERATURE는 0~2 사이의 값이어야 합니다.")
    
    if MAX_WORKERS < 1:
        raise ValueError("MAX_WORKERS는 1 이상이어야 합니다.")
    
    return True

def save_to_env(api_key: str, base_url: str, model: str):
    """
    설정을 .env 파일에 저장합니다.
    """
    env_content = ""
    if ENV_FILE.exists():
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()

        updated_keys = set()

        for line in lines:
            if line.startswith("OPENAI_API_KEY="):
                env_content += f"OPENAI_API_KEY={api_key}\n"
                updated_keys.add("OPENAI_API_KEY")
            elif line.startswith("OPENAI_BASE_URL="):
                env_content += f"OPENAI_BASE_URL={base_url}\n"
                updated_keys.add("OPENAI_BASE_URL")
            elif line.startswith("LLM_MODEL="):
                env_content += f"LLM_MODEL={model}\n"
                updated_keys.add("LLM_MODEL")
            else:
                env_content += line

        if "OPENAI_API_KEY" not in updated_keys:
            env_content += f"OPENAI_API_KEY={api_key}\n"
        if "OPENAI_BASE_URL" not in updated_keys:
            env_content += f"OPENAI_BASE_URL={base_url}\n"
        if "LLM_MODEL" not in updated_keys:
            env_content += f"LLM_MODEL={model}\n"

    else:
        env_content = f"OPENAI_API_KEY={api_key}\n"
        env_content += f"OPENAI_BASE_URL={base_url}\n"
        env_content += f"LLM_MODEL={model}\n"

    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.write(env_content)

    os.environ["OPENAI_API_KEY"] = api_key
    os.environ["OPENAI_BASE_URL"] = base_url
    os.environ["LLM_MODEL"] = model

    global OPENAI_API_KEY, OPENAI_BASE_URL, LLM_MODEL
    OPENAI_API_KEY = api_key
    OPENAI_BASE_URL = base_url
    LLM_MODEL = model

def save_user_settings(settings: dict):
    """
    사용자 설정을 JSON 파일에 저장합니다.
    """
    current_settings = {}
    if USER_SETTINGS_FILE.exists():
        try:
            with open(USER_SETTINGS_FILE, 'r', encoding='utf-8') as f:
                current_settings = json.load(f)
        except:
            pass

    current_settings.update(settings)

    with open(USER_SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(current_settings, f, ensure_ascii=False, indent=2)

    # 전역 변수 업데이트
    global LANGUAGE, RECURSIVE_SEARCH, MONITOR_INTERVAL, CREDENTIAL_SOURCE, MANUAL_API_KEY
    if "LANGUAGE" in settings: LANGUAGE = settings["LANGUAGE"]
    if "RECURSIVE_SEARCH" in settings: RECURSIVE_SEARCH = settings["RECURSIVE_SEARCH"]
    if "MONITOR_INTERVAL" in settings: MONITOR_INTERVAL = settings["MONITOR_INTERVAL"]
    if "CREDENTIAL_SOURCE" in settings: CREDENTIAL_SOURCE = settings["CREDENTIAL_SOURCE"]
    if "MANUAL_API_KEY" in settings: MANUAL_API_KEY = settings["MANUAL_API_KEY"]

# Load settings initially (cheap), but defer credentials (expensive/risky)
load_settings()

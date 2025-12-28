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
        # API 키가 없어도 GUI에서 설정할 수 있도록 허용 (경고만 로깅하거나 처리)
        # 여기서는 ValueError를 발생시키되, main에서 처리하도록 함
        raise ValueError("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")
    
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

        # 키 업데이트 추적
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

        # 없는 키 추가
        if "OPENAI_API_KEY" not in updated_keys:
            env_content += f"OPENAI_API_KEY={api_key}\n"
        if "OPENAI_BASE_URL" not in updated_keys:
            env_content += f"OPENAI_BASE_URL={base_url}\n"
        if "LLM_MODEL" not in updated_keys:
            env_content += f"LLM_MODEL={model}\n"

    else:
        # 새 파일 생성
        env_content = f"OPENAI_API_KEY={api_key}\n"
        env_content += f"OPENAI_BASE_URL={base_url}\n"
        env_content += f"LLM_MODEL={model}\n"

    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.write(env_content)

    # 현재 프로세스 환경 변수 업데이트 (재시작 없이 반영 위함)
    os.environ["OPENAI_API_KEY"] = api_key
    os.environ["OPENAI_BASE_URL"] = base_url
    os.environ["LLM_MODEL"] = model

    # 전역 변수 업데이트
    global OPENAI_API_KEY, OPENAI_BASE_URL, LLM_MODEL
    OPENAI_API_KEY = api_key
    OPENAI_BASE_URL = base_url
    LLM_MODEL = model


if __name__ == "__main__":
    # 설정 테스트
    print("프로젝트 루트:", PROJECT_ROOT)
    print("로그 디렉토리:", LOGS_DIR)
    print("LLM 모델:", LLM_MODEL)
    print("Base URL:", OPENAI_BASE_URL)
    print("지원 카테고리:", DEFAULT_CATEGORIES)
    try:
        print("설정 유효성:", validate_config())
    except ValueError as e:
        print(f"설정 유효성 실패: {e}")

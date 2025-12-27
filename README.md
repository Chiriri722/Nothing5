# file-classifier - 로깅 모듈 구현

LLM 기반 파일 자동 분류 프로그램의 로깅 시스템입니다.

## 프로젝트 구조

```
file-classifier/
├── config/
│   ├── __init__.py
│   └── config.py           # 애플리케이션 전역 설정
├── logs/
│   └── app.log            # 메인 로그 파일 (자동 회전)
├── logger.py              # 중앙화된 로깅 모듈 ✨ NEW
├── __init__.py            # 패키지 초기화
└── README.md              # 이 파일
```

## logger.py 모듈 소개

### 개요

`logger.py`는 파이썬 표준 `logging` 모듈을 기반으로 한 구조화된 로깅 시스템입니다.
애플리케이션의 모든 모듈이 동일한 로깅 설정을 사용하도록 중앙화하여 관리합니다.

### 핵심 기능

| 기능 | 설명 |
|------|------|
| **중앙화된 로깅 설정** | 애플리케이션 전역에서 일관된 로깅 설정 사용 |
| **다중 핸들러** | 콘솔(INFO)과 파일(DEBUG) 각각 독립적인 레벨 설정 |
| **로그 로테이션** | RotatingFileHandler로 파일 크기 관리 (10MB, 5개 백업) |
| **일관된 타임스탬프** | 모든 로그에 `YYYY-MM-DD HH:MM:SS` 형식의 타임스탐프 포함 |
| **구조화된 로깅** | 모듈명, 파일명, 라인 번호 등 구조화된 정보 기록 |
| **모듈별 로거** | `logging.getLogger(__name__)` 방식으로 모듈별 로거 생성 지원 |
| **민감 정보 보호** | API 키, 패스워드 등 자동 마스킹 |

### 로그 포맷

```
%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s
```

**예시:**
```
2025-12-27 14:30:45 - __main__ - INFO - [test.py:42] - 파일 처리 시작: document.pdf
2025-12-27 14:30:46 - classifier - DEBUG - [classifier.py:88] - 분류 모델 로드 완료
2025-12-27 14:30:50 - mover - WARNING - [mover.py:156] - 지원되지 않는 파일 형식: .exe
```

## 로그 레벨 정책

| 레벨 | 용도 | 예시 |
|------|------|------|
| **DEBUG** | 개발 단계의 상세 정보 | 변수값, 함수 진입/종료, 반복 처리 |
| **INFO** | 일반적인 정보 | 파일 처리 시작/완료, API 호출, 분류 결과 |
| **WARNING** | 예상치 못한 이벤트 | 지원되지 않는 파일 형식, 재시도 |
| **ERROR** | 심각한 문제 | API 오류, 파일 이동 실패, 예외 발생 |
| **CRITICAL** | 시스템 동작 불가능 | 필수 리소스 초기화 실패 |

## 사용 방법

### 1. 기본 사용

```python
from logger import setup_logging, get_logger

# 애플리케이션 시작 시점에 한 번 호출
setup_logging()

# 각 모듈에서 로거 인스턴스 얻기
logger = get_logger(__name__)

# 로깅하기
logger.debug("디버그 정보")
logger.info("일반 정보")
logger.warning("경고")
logger.error("에러")
logger.critical("심각한 에러")
```

### 2. 파일 처리 로깅

```python
from logger import log_file_processing

# 파일 처리 과정 로깅
log_file_processing("document.pdf", "started")    # 시작
log_file_processing("document.pdf", "completed")  # 완료
log_file_processing("document.pdf", "failed")     # 실패
```

### 3. 분류 결과 로깅

```python
from logger import log_classification_result

# 분류 결과 로깅
log_classification_result(
    filename="photo.jpg",
    category="image",
    confidence=0.95
)
# 출력: 분류 완료 - 파일: photo.jpg, 카테고리: image, 신뢰도: 95.00%
```

### 4. 에러 로깅 (컨텍스트 정보 포함)

```python
from logger import log_error_with_context

try:
    # 어떤 작업 수행
    pass
except Exception as e:
    log_error_with_context(
        error=e,
        context_info={
            "filename": "test.pdf",
            "action": "classification",
            "api_key": "secret_key_123"  # 자동으로 마스킹됨
        }
    )
# API 키는 자동으로 "***MASKED***"로 표시됨
```

## 설정 파일 (config/config.py)

로깅 관련 설정은 `config/config.py`에서 관리합니다:

```python
# 로그 레벨 설정 (환경변수로도 지정 가능)
LOG_LEVEL = "INFO"

# 로그 파일 경로
LOG_DIR = PROJECT_ROOT / "logs"
LOG_FILE_PATH = LOG_DIR / "app.log"

# 로그 로테이션 설정
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5              # 5개의 백업 파일 유지

# 로그 포맷
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 핸들러별 로그 레벨
CONSOLE_LOG_LEVEL = "INFO"      # 콘솔: INFO 이상
FILE_LOG_LEVEL = "DEBUG"        # 파일: DEBUG 이상
```

## 로그 파일 위치

```
file-classifier/logs/
├── app.log              # 현재 로그 파일
├── app.log.1            # 이전 로그 파일 (자동 백업)
├── app.log.2
├── app.log.3
├── app.log.4
└── app.log.5
```

파일이 10MB에 도달하면 자동으로 회전하며, 가장 오래된 파일은 삭제됩니다.

## 주요 클래스 및 함수

### LoggerConfig 클래스

```python
class LoggerConfig:
    """애플리케이션 로깅 설정을 관리하는 클래스"""
    
    @staticmethod
    def _ensure_log_directory() -> None:
        """로그 디렉토리 생성"""
    
    @staticmethod
    def _create_console_handler(level: str) -> logging.StreamHandler:
        """콘솔 핸들러 생성"""
    
    @staticmethod
    def _create_file_handler(level: str) -> logging.handlers.RotatingFileHandler:
        """회전하는 파일 핸들러 생성"""
    
    @staticmethod
    def setup() -> None:
        """전역 로깅 설정 초기화"""
```

### 공개 함수

| 함수 | 설명 |
|------|------|
| `setup_logging()` | 애플리케이션 전역 로깅 설정 초기화 |
| `get_logger(name)` | 모듈별 로거 인스턴스 반환 |
| `log_file_processing(filename, status)` | 파일 처리 과정 로깅 |
| `log_classification_result(filename, category, confidence)` | 분류 결과 로깅 |
| `log_error_with_context(error, context_info)` | 컨텍스트와 함께 에러 로깅 |

## 민감 정보 보호

로거는 다음 키를 자동으로 감지하여 마스킹합니다:
- `api_key`, `password`, `token`, `secret`, `key` 등

```python
# 입력
log_error_with_context(
    error=Exception("Test"),
    context_info={
        "filename": "test.pdf",
        "api_key": "sk-12345..."
    }
)

# 출력
# api_key: ***MASKED***
```

## 테스트

로거 모듈을 직접 실행하여 테스트할 수 있습니다:

```bash
cd C:/Users/White/Documents
python -m file_classifier.logger
```

**출력:**
```
2025-12-27 14:35:22 - root - DEBUG - [logger.py:171] - 로깅 시스템이 초기화되었습니다
2025-12-27 14:35:22 - root - DEBUG - [logger.py:172] - 로그 파일 경로: C:\Users\White\Documents\file-classifier\logs\app.log
2025-12-27 14:35:22 - __main__ - DEBUG - [logger.py:291] - DEBUG 레벨 메시지
2025-12-27 14:35:22 - __main__ - INFO - [logger.py:292] - INFO 레벨 메시지
2025-12-27 14:35:22 - __main__ - WARNING - [logger.py:293] - WARNING 레벨 메시지
2025-12-27 14:35:22 - __main__ - ERROR - [logger.py:294] - ERROR 레벨 메시지
```

## 멀티스레드 안전성

`logger.py`는 Python의 표준 `logging` 모듈을 기반으로 하므로 **멀티스레드 환경에서 안전**합니다.

## 베스트 프랙티스

✅ **각 모듈의 시작에서 로거 생성**
```python
logger = get_logger(__name__)
```

✅ **적절한 로그 레벨 사용**
```python
logger.debug("개발 단계 정보만")      # 상세 정보
logger.info("주요 이벤트")           # 일반 정보
logger.warning("예상 가능한 문제")   # 경고
logger.error("예상 불가능한 문제")   # 에러
```

✅ **민감 정보 보호**
```python
# ❌ 나쁜 예
logger.info(f"API 호출: {api_key}")

# ✅ 좋은 예
log_error_with_context(
    error=e,
    context_info={"action": "api_call"}  # api_key 제외
)
```

✅ **구조화된 정보 제공**
```python
# ❌ 나쁜 예
logger.error("에러 발생")

# ✅ 좋은 예
log_error_with_context(
    error=e,
    context_info={
        "filename": "test.pdf",
        "action": "classification",
        "retry_count": 3
    }
)
```

## 파일 구조 요약

| 파일 | 용도 |
|------|------|
| `logger.py` | 로깅 모듈 구현 (296줄) |
| `config/config.py` | 로깅 설정 관리 |
| `logs/app.log` | 메인 로그 파일 |
| `__init__.py` | 패키지 초기화 |

## 다음 단계

이 로깅 모듈은 파일 분류 프로그램의 다른 모듈들과 통합될 준비가 완료되었습니다:

- ✅ logger.py 구현 완료
- ⏳ 다른 모듈(classifier, mover 등)과의 통합
- ⏳ 실제 파일 분류 작업에서 로깅 적용

## 라이선스

MIT License

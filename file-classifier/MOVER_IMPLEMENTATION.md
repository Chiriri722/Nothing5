# FileMover 모듈 구현 문서

## 개요

`FileMover` 클래스는 LLM 기반 파일 자동 분류 프로그램의 핵심 모듈로, LLM이 추천한 폴더로 파일을 안전하게 이동시키는 기능을 제공합니다.

## 구현 완료 기능

### 1. 핵심 기능

#### ✅ 폴더 생성
- `_create_destination_folder()`: 추천된 폴더명으로 새 폴더 생성
- 이미 존재하는 폴더는 재사용
- 쓰기 권한 자동 확인

#### ✅ 파일 이동
- `move_file()`: 메인 파일 이동 함수
- `shutil.move()` 사용으로 안전한 이동 구현
- 원본 파일 보호 (이동 실패 시 원본 유지)
- 상세한 에러 처리

#### ✅ 중복 파일 처리
- 4가지 처리 전략 지원:
  - `RENAME_WITH_NUMBER`: `filename(1).txt` 형식
  - `RENAME_WITH_TIMESTAMP`: `2025-12-27_12-34-56_filename.txt` 형식
  - `OVERWRITE`: 기존 파일 덮어쓰기
  - `SKIP`: 이동 건너뛰기

#### ✅ 이동 로깅
- 모든 이동 작업 자동 기록
- `UndoManager`와의 통합
- 로컬 이동 히스토리 유지

#### ✅ 에러 처리
- `FileNotFoundError`: 파일 찾기 실패
- `PermissionError`: 권한 오류
- `OSError`: 디스크 용량 부족 등
- `shutil.Error`: 파일 이동 오류
- 모든 경우 상세 로깅 및 에러 정보 반환

### 2. 입출력 형식

#### 입력
```python
mover.move_file(source_file_path: str, folder_name: str) -> Dict
```

#### 출력
```python
{
    "status": "success" | "error" | "warning",
    "source_path": "원본 파일 경로",
    "destination_path": "이동된 파일 경로",
    "folder_name": "생성/사용된 폴더명",
    "created_new_folder": True | False,
    "duplicate_handled": True | False,
    "error": "에러 메시지 (실패 시만)",
    "move_history_id": "undo_manager 기록 ID"
}
```

### 3. 주요 메서드

#### `__init__(base_path, duplicate_strategy, undo_manager)`
초기화 메서드
- `base_path`: 파일 정리 대상 폴더 (기본값: `~/Downloads`)
- `duplicate_strategy`: 중복 파일 처리 방식 (기본값: `RENAME_WITH_NUMBER`)
- `undo_manager`: UndoManager 인스턴스 (선택사항)

#### `move_file(source_file_path, folder_name)`
단일 파일 이동 - 메인 메서드

#### `move_multiple_files(file_list)`
여러 파일을 동시에 이동
```python
file_list = [
    {"source": "path1", "folder_name": "folder1"},
    {"source": "path2", "folder_name": "folder2"}
]
results = mover.move_multiple_files(file_list)
```

#### `get_move_history()`
파일 이동 히스토리 반환

#### `get_move_history_summary()`
히스토리 요약 정보 반환
```python
{
    "total_operations": 10,
    "successful": 9,
    "failed": 0,
    "warnings": 1,
    "success_rate": "90.0%"
}
```

### 4. 유효성 검사

#### 파일 경로 검증
- 파일 존재 여부
- 파일 형식 (디렉토리 제외)
- 읽기 권한

#### 폴더명 검증
- **금지 문자 제거**: `/ \ : * ? " < > |`
- **길이 제한**: 최대 255자
- **시스템 예약어 제외**: `CON, PRN, AUX, NUL, COM1-9, LPT1-9`
- **점 전용 폴더명 방지**: `...` → `folder`
- **공백 정리**: 양쪽 공백 제거

## 사용 예시

### 기본 사용법
```python
from modules.mover import FileMover

# FileMover 초기화
mover = FileMover(base_path="/path/to/organize")

# 단일 파일 이동
result = mover.move_file(
    source_file_path="/Downloads/document.pdf",
    folder_name="문서"
)

if result["status"] == "success":
    print(f"파일 이동 완료: {result['destination_path']}")
else:
    print(f"오류: {result['error']}")
```

### 중복 처리 전략 설정
```python
from modules.mover import FileMover, DuplicateHandlingStrategy

# 타임스탬프 기반 중복 처리
mover = FileMover(
    base_path="/path/to/organize",
    duplicate_strategy=DuplicateHandlingStrategy.RENAME_WITH_TIMESTAMP
)
```

### 여러 파일 이동
```python
file_list = [
    {"source": "/Downloads/photo1.jpg", "folder_name": "이미지"},
    {"source": "/Downloads/video.mp4", "folder_name": "비디오"},
    {"source": "/Downloads/report.pdf", "folder_name": "문서"}
]

results = mover.move_multiple_files(file_list)

# 결과 요약
summary = mover.get_move_history_summary()
print(f"성공률: {summary['success_rate']}")
```

### UndoManager 통합
```python
from modules.mover import FileMover
from modules.undo_manager import UndoManager
from config.config import UNDO_HISTORY_FILE

# UndoManager 초기화
undo_manager = UndoManager(str(UNDO_HISTORY_FILE))

# FileMover와 연동
mover = FileMover(undo_manager=undo_manager)

# 파일 이동 (자동으로 undo_manager에 기록됨)
result = mover.move_file("/Downloads/file.txt", "Documents")

# 나중에 실행 취소 가능
undo_manager.undo()
```

## 로깅

모든 작업이 자동으로 로깅됩니다.

### 로그 레벨
- **DEBUG**: 유효성 검사, 폴더 생성 등 상세 정보
- **INFO**: 파일 이동 시작/완료
- **WARNING**: 중복 파일, 폴더명 변경 등
- **ERROR**: 파일 찾기 실패, 권한 오류 등

### 로그 예시
```
2025-12-27 12:34:56 - modules.mover - INFO - FileMover 초기화됨 - base_path: /path/to/organize
2025-12-27 12:34:57 - modules.mover - INFO - 파일 이동 시작: /Downloads/document.pdf -> /path/to/organize/문서/document.pdf
2025-12-27 12:34:57 - modules.mover - INFO - 파일 이동 완료: /path/to/organize/문서/document.pdf
```

## 설정 연동

`config/config.py`와 자동으로 연동됩니다:
- `ORGANIZE_BASE_PATH`: 기본 정리 대상 폴더
- `DUPLICATE_FILE_HANDLING`: 중복 파일 처리 방식
- `MAX_FOLDER_NAME_LENGTH`: 최대 폴더명 길이 (255)

## 테스트

### 테스트 실행
```bash
python -m unittest tests.test_mover -v
```

### 특정 테스트 클래스 실행
```bash
python -m unittest tests.test_mover.TestFileMover -v
```

### 특정 테스트 메서드 실행
```bash
python -m unittest tests.test_mover.TestFileMover.test_move_single_file -v
```

### 구현된 테스트 케이스

#### TestFileMover 클래스
1. `test_move_single_file()` - 단일 파일 이동
2. `test_create_destination_folder()` - 목표 폴더 생성
3. `test_duplicate_file_handling_rename()` - 중복 파일 처리 (번호)
4. `test_invalid_folder_name()` - 잘못된 폴더명 처리
5. `test_validate_folder_name_reserved_words()` - 시스템 예약어 처리
6. `test_validate_file_path_not_exists()` - 존재하지 않는 파일
7. `test_move_multiple_files()` - 여러 파일 이동
8. `test_move_history_recording()` - 이동 히스토리 기록
9. `test_move_history_summary()` - 이동 히스토리 요약
10. `test_duplicate_handling_overwrite()` - 중복 파일 덮어쓰기
11. `test_duplicate_handling_timestamp()` - 중복 파일 타임스탬프 처리
12. `test_folder_name_length_validation()` - 폴더명 길이 검증
13. `test_folder_name_with_dots()` - 점 전용 폴더명 처리
14. `test_clear_move_history()` - 히스토리 초기화

#### TestFileMoverWithUndoManager 클래스
1. `test_undo_manager_integration()` - UndoManager 통합 테스트

## 에러 처리 전략

### 파일 찾기 실패 (FileNotFoundError)
```
status: "error"
error: "파일 경로 유효성 검사 실패: [path]"
```

### 권한 오류 (PermissionError)
```
status: "error"
error: "권한 오류: [message]"
```

### 디스크 용량 부족 (OSError)
```
status: "error"
error: "디스크 용량 부족: [message]"
```

### 파일 이동 오류 (shutil.Error)
```
status: "error"
error: "파일 이동 오류: [message]"
```

### 중복 파일 처리 실패
```
status: "warning"
error: "중복 파일 처리 실패: [path]"
duplicate_handled: True
```

## 주요 고려사항

### ✅ 원자성
- 파일 이동은 all-or-nothing으로 구현
- 실패 시 원본 파일 유지

### ✅ 권한 관리
- 폴더 생성/파일 이동 전 권한 확인
- 부분 실패 방지

### ✅ 크로스 플랫폼 지원
- `pathlib.Path` 사용으로 Windows/Linux/Mac 호환
- 금지 문자는 모든 플랫폼 통일

### ✅ 유효성 검사
- 파일 경로: 존재 여부, 파일 형식, 읽기 권한
- 폴더명: 금지 문자, 길이, 예약어, 점 전용

### ✅ 로깅 및 추적
- 모든 작업 상세 로깅
- UndoManager와의 완전한 통합
- 로컬 히스토리 유지

## 향후 확장 가능성

1. **진행 상태 추적**: 대용량 파일 이동 시 진행률 표시
2. **배치 이동**: 트랜잭션 지원
3. **메타데이터 보존**: 파일 생성/수정 시간 유지
4. **압축 파일 처리**: 자동 압축/해제
5. **원격 스토리지**: 클라우드 저장소 지원

## API 호환성

기존 `FileMover` 클래스의 메서드와 호환성 유지:
- `move_file()`: 반환 타입 변경 (문자열 → 딕셔너리)
- `copy_file()`: 호환 (이동만 구현)
- `get_move_history()`: 호환
- `clear_history()`: 호환 (메서드명 변경: `clear_move_history`)

## 결론

FileMover 모듈은 LLM 기반 파일 자동 분류 프로그램의 핵심 기능을 안전하고 효율적으로 구현합니다:

✅ **안전성**: 원본 파일 보호, 상세 에러 처리
✅ **유연성**: 다양한 중복 처리 전략 지원
✅ **추적성**: 완벽한 로깅 및 히스토리 관리
✅ **확장성**: UndoManager 및 설정 연동
✅ **신뢰성**: 16개의 종합 테스트 케이스

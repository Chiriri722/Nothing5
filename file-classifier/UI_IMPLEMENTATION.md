# UI 모듈 구현 설명서

## 개요

ui.py는 Tkinter를 기반으로 한 LLM 기반 파일 자동 분류 프로그램의 GUI 모듈입니다.
사용자 친화적인 인터페이스를 통해 파일 분류 작업을 시각적으로 제어할 수 있습니다.

---

## 주요 기능

### 1. 메인 윈도우 구성

#### 폴더 선택 (Top Frame)
- **찾기 버튼**: filedialog.askdirectory()를 사용하여 대상 폴더 선택
- **경로 표시**: 선택된 폴더 경로를 읽기 전용 Entry에 표시
- **초기화 버튼**: 선택한 폴더 제거

#### 제어 버튼 (Control Frame)
- **시작**: 파일 모니터링 시작
- **중지**: 파일 모니터링 중지
- **일시중지**: 모니터링을 일시적으로 중지
- **재개**: 일시중지된 모니터링 재개
- **실행 취소 (Ctrl+Z)**: 마지막 작업 취소
- **다시 실행 (Ctrl+Y)**: 취소된 작업 복원

#### 상태 및 파일 목록 (Middle Frame)
- **상태 표시**: 현재 모니터링 상태 (준비됨, 모니터링 중, 일시중지, 중지 등)
- **진행률 표시**: 진행 상황을 프로그레스 바로 표시
- **파일 목록**: 처리된 파일을 실시간으로 표시
  - 형식: `[상태] 파일명 → 분류 폴더`
  - 우클릭 메뉴: 복사, 삭제, 모두 지우기

#### 통계 정보 (Statistics Frame)
- **처리된 파일 수**: 총 처리된 파일 수
- **처리 속도**: files/min 단위의 처리 속도
- **카테고리별 분류**: 각 카테고리별 분류 파일 수

#### 상태 표시줄 (Status Bar)
- **왼쪽**: 마지막 작업 정보
- **오른쪽**: 현재 시간 (HH:MM:SS)

### 2. 메뉴바

#### File 메뉴
- **폴더 선택**: 대상 폴더 선택 대화상자 열기
- **로그 내보내기**: 작업 로그를 파일로 저장
- **종료**: 프로그램 종료

#### Edit 메뉴
- **실행 취소**: 마지막 작업 취소 (Ctrl+Z)
- **다시 실행**: 취소된 작업 복원 (Ctrl+Y)
- **히스토리 초기화**: 작업 히스토리 전체 삭제

#### View 메뉴
- **새로 고침**: UI 새로 고침 (F5)
- **통계 표시**: 통계 정보를 팝업으로 표시
- **작업 히스토리**: 작업 히스토리 대화상자 표시

#### Help 메뉴
- **설정**: 프로그램 설정 대화상자
- **도움말 및 설명서**: 프로그램 도움말 표시
- **정보**: 프로그램 정보 표시

---

## 클래스 구조

### FileClassifierGUI

```python
class FileClassifierGUI:
    """파일 분류 프로그램 GUI 클래스"""
    
    def __init__(self, root: tk.Tk = None, window_width: int = 900, window_height: int = 700):
        """GUI 초기화"""
```

#### 주요 속성

| 속성 | 설명 | 타입 |
|------|------|------|
| `root` | Tkinter 루트 윈도우 | tk.Tk |
| `folder_path_var` | 선택된 폴더 경로 | tk.StringVar |
| `status_var` | 현재 상태 | tk.StringVar |
| `progress_var` | 진행률 | tk.DoubleVar |
| `is_monitoring` | 모니터링 여부 | bool |
| `is_paused` | 일시중지 여부 | bool |
| `stats` | 통계 데이터 | dict |
| `file_list_data` | 파일 목록 | List[tuple] |
| `ui_queue` | UI 업데이트 큐 | Queue |

#### 주요 메서드

| 메서드 | 설명 |
|--------|------|
| `browse_folder()` | 폴더 선택 대화상자 열기 |
| `clear_selection()` | 선택한 폴더 제거 |
| `start_monitoring()` | 모니터링 시작 |
| `stop_monitoring()` | 모니터링 중지 |
| `pause_monitoring()` | 모니터링 일시중지 |
| `resume_monitoring()` | 모니터링 재개 |
| `add_file_to_list(filename, folder, status)` | 파일 목록에 항목 추가 |
| `remove_file_from_list(index)` | 파일 목록에서 항목 제거 |
| `clear_file_list()` | 파일 목록 초기화 |
| `update_statistics(**kwargs)` | 통계 정보 업데이트 |
| `update_status(message)` | 상태 메시지 업데이트 |
| `update_progress(value)` | 진행률 업데이트 |
| `run_in_background(func, args)` | 백그라운드에서 작업 실행 |
| `safe_update_ui(func, args)` | 스레드 안전 UI 업데이트 |
| `run()` | GUI 실행 |

---

## 사용 예제

### 기본 사용법

```python
import tkinter as tk
from ui.ui import FileClassifierGUI

# GUI 생성
root = tk.Tk()
gui = FileClassifierGUI(root)

# 콜백 함수 설정
def on_start(folder_path):
    print(f"모니터링 시작: {folder_path}")
    # 모니터링 로직 구현

def on_stop():
    print("모니터링 중지")

def on_file_processed(filename, folder, status):
    print(f"{filename} → {folder}")

# 콜백 등록
gui.set_on_start_monitoring(on_start)
gui.set_on_stop_monitoring(on_stop)

# GUI 실행
gui.run()
```

### 파일 처리 워크플로우

```python
# 파일 처리 완료 시 호출
def on_file_processed(filename, folder, status):
    gui.add_file_to_list(filename, folder, status)
    gui.update_statistics()
    gui.update_progress(current_count / total_files * 100)

# 콜백 등록
gui.set_on_file_processed(on_file_processed)
```

### 통계 업데이트

```python
# 통계 업데이트
gui.update_statistics(
    total=42,
    speed=10.5,
    categories={'문서': 15, '이미지': 12, '비디오': 10, '기타': 5}
)
```

---

## 색상 및 폰트

### 색상 정의 (COLORS)

```python
COLORS = {
    'bg': '#f0f0f0',           # 배경색 (밝은 회색)
    'fg': '#333333',           # 글자색 (어두운 회색)
    'accent': '#0078d4',       # 강조 색상 (파란색)
    'success': '#107c10',      # 성공 (초록색)
    'warning': '#ffb900',      # 경고 (주황색)
    'error': '#e81123',        # 오류 (빨간색)
}
```

### 폰트 정의 (FONTS)

```python
FONTS = {
    'title': ('Arial', 14, 'bold'),    # 제목
    'normal': ('Arial', 10),           # 일반 텍스트
    'small': ('Arial', 9),             # 작은 텍스트
    'mono': ('Courier', 9),            # 고정폭 폰트
}
```

---

## 스레드 안전성

### 백그라운드 작업 실행

```python
def heavy_task():
    # 오래 걸리는 작업
    for i in range(100):
        gui.update_status(f"처리 중... {i}%")
        time.sleep(0.1)

# UI를 블록하지 않도록 백그라운드에서 실행
gui.run_in_background(heavy_task)
```

### 스레드 안전 UI 업데이트

```python
def worker_thread():
    # 백그라운드 스레드에서 UI 업데이트
    gui.safe_update_ui(gui.update_status, ("작업 완료",))
    gui.safe_update_ui(gui.add_file_to_list, ("file.txt", "문서", "✓"))

thread = threading.Thread(target=worker_thread, daemon=True)
thread.start()
```

---

## 대화상자 및 메시지

### 확인 대화

```python
result = gui.show_confirmation_dialog("확인", "정말 진행하시겠습니까?")
if result:
    # 사용자가 '예'를 선택
    pass
```

### 오류/경고/정보 메시지

```python
gui.show_error_dialog("오류", "파일을 찾을 수 없습니다.")
gui.show_warning_dialog("경고", "유효한 폴더를 선택하세요.")
gui.show_info_dialog("정보", "작업이 완료되었습니다.")
```

---

## 콜백 함수

### 콜백 등록 메서드

```python
gui.set_on_start_monitoring(callback)      # 모니터링 시작
gui.set_on_stop_monitoring(callback)       # 모니터링 중지
gui.set_on_file_processed(callback)        # 파일 처리 완료
gui.set_on_undo(callback)                  # 실행 취소
gui.set_on_redo(callback)                  # 다시 실행
gui.set_on_export_log(callback)            # 로그 내보내기
```

### 콜백 함수 시그니처

```python
def on_start_monitoring(folder_path: str) -> None:
    """모니터링 시작 콜백"""
    pass

def on_stop_monitoring() -> None:
    """모니터링 중지 콜백"""
    pass

def on_file_processed(filename: str, folder: str, status: str) -> None:
    """파일 처리 완료 콜백"""
    pass
```

---

## 상태 관리

### 모니터링 상태

| 상태 | is_monitoring | is_paused | 버튼 활성화 상태 |
|------|--------------|-----------|----------------|
| 초기화 | False | False | 시작만 활성화 |
| 모니터링 중 | True | False | 중지, 일시중지 활성화 |
| 일시중지됨 | True | True | 중지, 재개 활성화 |
| 중지됨 | False | False | 시작만 활성화 |

### 버튼 상태 업데이트

```python
# 모니터링 상태에 따라 자동으로 버튼 활성화/비활성화
gui._update_button_states()
```

---

## 파일 목록 관리

### 파일 목록 데이터 구조

```python
file_list_data: List[tuple] = [
    ("file1.pdf", "문서", "✓"),
    ("file2.jpg", "이미지", "✓"),
    ("file3.mp4", "비디오", "✗"),
]
```

### 파일 목록 조작

```python
# 파일 추가
gui.add_file_to_list("document.pdf", "문서", "✓")

# 파일 제거
gui.remove_file_from_list(0)

# 모든 파일 제거
gui.clear_file_list()

# 파일 목록 크기
count = len(gui.file_list_data)
```

---

## 통계 관리

### 통계 데이터 구조

```python
stats = {
    'total_processed': 42,              # 처리된 파일 수
    'categories': {                     # 카테고리별 통계
        '문서': 15,
        '이미지': 12,
        '비디오': 10,
        '기타': 5,
    },
    'processing_speed': 10.5,           # files/min
}
```

### 통계 업데이트

```python
# 자동 계산
gui.update_statistics()

# 수동 설정
gui.update_statistics(
    total=50,
    speed=12.3,
    categories={'문서': 20, '이미지': 15, '기타': 15}
)
```

---

## 테스트

### 테스트 실행

```bash
cd file-classifier
python -m pytest tests/test_ui.py -v
```

### 테스트 케이스

- `test_gui_initialization()`: GUI 초기화 테스트
- `test_folder_selection_variables()`: 폴더 선택 변수 테스트
- `test_add_file_to_list()`: 파일 목록 추가 테스트
- `test_clear_file_list()`: 파일 목록 초기화 테스트
- `test_update_statistics()`: 통계 업데이트 테스트
- `test_monitoring_state_changes()`: 모니터링 상태 변화 테스트
- `test_button_states_initialization()`: 버튼 상태 초기화 테스트
- 그 외 20개 이상의 테스트 케이스

---

## 성능 최적화

### 큐를 통한 UI 업데이트

```python
# 다른 스레드에서
for i in range(100):
    gui.safe_update_ui(gui.update_progress, (i,))
    gui.safe_update_ui(gui.add_file_to_list, (f"file_{i}.txt", "문서", "✓"))
```

### UI 새로 고침

```python
# 명시적 업데이트
gui.root.update_idletasks()

# 또는
gui._refresh()  # F5 키와 동일
```

---

## 제한 사항 및 주의사항

1. **Tkinter 버전**: Python 3.6 이상에서 테스트됨
2. **OS 호환성**: Windows, macOS, Linux에서 실행 가능
3. **인코딩**: UTF-8 인코딩 권장
4. **스레드 안전성**: 모든 UI 업데이트는 main 스레드에서 수행되어야 함
5. **파일 목록 크기**: 매우 많은 파일(수천 개)을 표시할 경우 성능 저하 가능

---

## 확장 가능성

### 커스텀 다이얼로그 추가

```python
def custom_dialog(self):
    """커스텀 대화상자"""
    dialog = tk.Toplevel(self.root)
    dialog.title("커스텀 대화")
    # 대화상자 구성
```

### 커스텀 프레임 추가

```python
def _create_custom_frame(self, parent):
    """커스텀 프레임 생성"""
    custom_frame = ttk.LabelFrame(parent, text="커스텀", padding="10")
    custom_frame.pack(fill=tk.X, pady=10)
    # 프레임 구성
```

---

## 문제 해결

### Q: UI가 응답하지 않음
A: `run_in_background()`를 사용하여 오래 걸리는 작업을 별도 스레드에서 실행하세요.

### Q: 파일 목록이 업데이트되지 않음
A: `safe_update_ui()`를 사용하여 스레드 안전 업데이트를 수행하세요.

### Q: 통계가 잘못 표시됨
A: `update_statistics()` 호출 시 `categories` 매개변수를 올바르게 전달하세요.

---

## 라이선스

MIT License

---

## 참고

- Tkinter 공식 문서: https://docs.python.org/3/library/tkinter.html
- Python 스레드 문서: https://docs.python.org/3/library/threading.html
- Queue 문서: https://docs.python.org/3/library/queue.html

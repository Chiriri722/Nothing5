# -*- coding: utf-8 -*-
"""
GUI 모듈

Tkinter 및 TkinterDnD를 사용하여 사용자 친화적인 그래픽 인터페이스를 제공합니다.
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import logging
from typing import Callable, Optional, Dict, Any, Tuple, List
from pathlib import Path
from tkinterdnd2 import DND_FILES, TkinterDnD
import config.config as cfg

logger = logging.getLogger(__name__)

class FileClassifierGUI:
    """
    파일 분류 프로그램 GUI 클래스
    
    TkinterDnD 기반으로 Drag & Drop을 지원하며,
    사이드바 내비게이션 구조를 가집니다.
    """
    
    def __init__(self, window_width: int = 900, window_height: int = 700):
        """
        FileClassifierGUI 초기화
        """
        # TkinterDnD.Tk()를 사용하여 DnD 지원
        self.root = TkinterDnD.Tk()
        self.root.title("LLM 기반 파일 자동 분류 프로그램")
        self.root.geometry(f"{window_width}x{window_height}")
        
        # 콜백 함수
        self.on_classify: Optional[Callable] = None
        self.on_monitor_start: Optional[Callable] = None
        self.on_monitor_stop: Optional[Callable] = None
        self.on_undo: Optional[Callable] = None
        self.on_redo: Optional[Callable] = None
        self.on_settings_changed: Optional[Callable] = None
        self.on_export_log: Optional[Callable] = None
        
        # 변수
        self.folder_path_var = tk.StringVar()
        self.status_var = tk.StringVar(value="준비됨")
        self.progress_var = tk.DoubleVar()
        self.current_page = None
        
        # 로그 데이터 (페이지 전환 시 데이터 유지용)
        self.log_data: List[Tuple[str, str, str]] = []

        # 스타일 설정
        self._setup_styles()

        # UI 구성
        self._init_layout()

        # 기본 페이지 로드
        self._show_main_page()

    def _setup_styles(self):
        style = ttk.Style()
        style.configure("Sidebar.TFrame", background="#f0f0f0")
        style.configure("Sidebar.TButton", anchor="w", padding=10)
        style.configure("Title.TLabel", font=("Arial", 16, "bold"))
        style.configure("Section.TLabel", font=("Arial", 12, "bold"))

    def _init_layout(self):
        """기본 레이아웃 구성 (사이드바 + 콘텐츠 영역)"""
        # 메인 컨테이너
        self.main_container = ttk.Frame(self.root)
        self.main_container.pack(fill=tk.BOTH, expand=True)

        # 사이드바
        self.sidebar = ttk.Frame(self.main_container, style="Sidebar.TFrame", width=200)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False) # 너비 고정

        # 사이드바 메뉴
        ttk.Label(self.sidebar, text="메뉴", style="Section.TLabel", background="#f0f0f0").pack(pady=20, padx=10, anchor="w")

        ttk.Button(self.sidebar, text="🏠 메인 화면", style="Sidebar.TButton",
                   command=self._show_main_page).pack(fill=tk.X, padx=5, pady=2)
        ttk.Button(self.sidebar, text="⚙️ LLM 설정", style="Sidebar.TButton",
                   command=self._show_llm_settings_page).pack(fill=tk.X, padx=5, pady=2)
        ttk.Button(self.sidebar, text="🛠 환경 설정", style="Sidebar.TButton",
                   command=self._show_env_settings_page).pack(fill=tk.X, padx=5, pady=2)

        # 콘텐츠 영역
        self.content_area = ttk.Frame(self.main_container, padding=20)
        self.content_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def _clear_content(self):
        for widget in self.content_area.winfo_children():
            widget.destroy()

    # =========================================================================
    # Pages
    # =========================================================================

    def _show_main_page(self):
        self._clear_content()
        self.current_page = "main"

        # 제목
        ttk.Label(self.content_area, text="파일 분류 메인", style="Title.TLabel").pack(anchor="w", pady=(0, 20))

        # 1. 경로 선택 및 DnD 영역
        path_frame = ttk.LabelFrame(self.content_area, text="작업 폴더 (여기에 폴더 드래그 앤 드롭)", padding=10)
        path_frame.pack(fill=tk.X, pady=(0, 10))

        entry = ttk.Entry(path_frame, textvariable=self.folder_path_var)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        # DnD 설정 (안전하게 시도)
        try:
            entry.drop_target_register(DND_FILES)
            entry.dnd_bind('<<Drop>>', self._on_drop)
            path_frame.drop_target_register(DND_FILES)
            path_frame.dnd_bind('<<Drop>>', self._on_drop)
        except Exception as e:
            logger.warning(f"DnD registration failed: {e}")
        
        ttk.Button(path_frame, text="찾기", command=self._select_folder).pack(side=tk.LEFT)
        
        # 2. 제어 버튼
        control_frame = ttk.Frame(self.content_area)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(control_frame, text="▶ 모니터링 시작", command=self._on_monitor_start_clicked).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(control_frame, text="⏹ 모니터링 중지", command=self._on_monitor_stop_clicked).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Separator(control_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        # 수동 분류 버튼 (기능 복구)
        ttk.Button(control_frame, text="⚡ 지금 분류 실행", command=self._on_classify_clicked).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Separator(control_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        ttk.Button(control_frame, text="↩ 실행 취소", command=self._on_undo_clicked).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(control_frame, text="↪ 다시 실행", command=self._on_redo_clicked).pack(side=tk.LEFT, padx=(0, 5))
        
        # 3. 상태 및 진행률
        status_frame = ttk.Frame(self.content_area)
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(status_frame, text="상태: ").pack(side=tk.LEFT)
        ttk.Label(status_frame, textvariable=self.status_var, foreground="blue").pack(side=tk.LEFT)
        
        progress = ttk.Progressbar(self.content_area, variable=self.progress_var, maximum=100)
        progress.pack(fill=tk.X, pady=(0, 10))
        
        # 4. 파일 목록 (Treeview)
        list_frame = ttk.LabelFrame(self.content_area, text="처리 내역", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("filename", "folder", "status")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings")
        self.tree.heading("filename", text="파일명")
        self.tree.heading("folder", text="분류 폴더")
        self.tree.heading("status", text="상태")

        self.tree.column("filename", width=200)
        self.tree.column("folder", width=150)
        self.tree.column("status", width=50, anchor="center")

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 저장된 로그 복원
        for item in self.log_data:
            self.tree.insert("", 0, values=item)

    def _show_llm_settings_page(self):
        self._clear_content()
        self.current_page = "llm_settings"
        
        ttk.Label(self.content_area, text="LLM API 설정", style="Title.TLabel").pack(anchor="w", pady=(0, 20))
        
        form_frame = ttk.Frame(self.content_area)
        form_frame.pack(anchor="w", fill=tk.X)

        # API Key
        ttk.Label(form_frame, text="API Key:").grid(row=1, column=0, sticky="w", pady=5)
        self.api_key_entry = ttk.Entry(form_frame, width=50, show="*")
        self.api_key_entry.grid(row=1, column=1, sticky="w", pady=5, padx=10)
        # config 값 로드
        if cfg.OPENAI_API_KEY:
            self.api_key_entry.insert(0, cfg.OPENAI_API_KEY)

        # Base URL
        ttk.Label(form_frame, text="Base URL:").grid(row=2, column=0, sticky="w", pady=5)
        self.base_url_entry = ttk.Entry(form_frame, width=50)
        self.base_url_entry.grid(row=2, column=1, sticky="w", pady=5, padx=10)
        if cfg.OPENAI_BASE_URL:
            self.base_url_entry.insert(0, cfg.OPENAI_BASE_URL)

        # Model
        ttk.Label(form_frame, text="Model Name:").grid(row=3, column=0, sticky="w", pady=5)
        self.model_entry = ttk.Entry(form_frame, width=30)
        self.model_entry.grid(row=3, column=1, sticky="w", pady=5, padx=10)
        if cfg.LLM_MODEL:
            self.model_entry.insert(0, cfg.LLM_MODEL)

        # Save Button
        ttk.Button(self.content_area, text="저장 및 적용", command=self._save_llm_settings).pack(anchor="w", pady=20)

        ttk.Label(self.content_area, text="* 설정 저장 시 .env 파일이 업데이트됩니다.", foreground="gray").pack(anchor="w")

    def _show_env_settings_page(self):
        self._clear_content()
        self.current_page = "env_settings"

        ttk.Label(self.content_area, text="환경 설정", style="Title.TLabel").pack(anchor="w", pady=(0, 20))

        form_frame = ttk.Frame(self.content_area)
        form_frame.pack(anchor="w", fill=tk.X)

        # 언어 (Mock)
        ttk.Label(form_frame, text="언어 (Language):").grid(row=0, column=0, sticky="w", pady=5)
        lang_combo = ttk.Combobox(form_frame, values=["한국어", "English"])
        lang_combo.set("한국어")
        lang_combo.grid(row=0, column=1, sticky="w", pady=5, padx=10)

        # 감시 주기
        ttk.Label(form_frame, text="감시 주기 (초):").grid(row=1, column=0, sticky="w", pady=5)
        interval_spin = ttk.Spinbox(form_frame, from_=1, to=60)
        interval_spin.set(5)
        interval_spin.grid(row=1, column=1, sticky="w", pady=5, padx=10)

        # Save Button (Mock)
        ttk.Button(self.content_area, text="설정 저장", command=lambda: messagebox.showinfo("저장", "환경 설정이 저장되었습니다.")).pack(anchor="w", pady=20)

    # =========================================================================
    # Event Handlers
    # =========================================================================
    
    def _on_drop(self, event):
        """DnD Drop 이벤트 핸들러"""
        path = event.data
        # Windows의 경우 중괄호로 감싸지는 경우가 있음
        if path.startswith('{') and path.endswith('}'):
            path = path[1:-1]

        if Path(path).is_dir():
            self.folder_path_var.set(path)
            logger.info(f"DnD 폴더 선택됨: {path}")
        else:
            messagebox.showwarning("경고", "폴더를 드롭해주세요.")

    def _select_folder(self) -> None:
        folder = filedialog.askdirectory(title="분류할 폴더 선택")
        if folder:
            self.folder_path_var.set(folder)

    def _on_monitor_start_clicked(self):
        folder = self.folder_path_var.get()
        if not folder:
            messagebox.showerror("오류", "폴더를 선택해주세요.")
            return
        if self.on_monitor_start:
            self.on_monitor_start(folder)

    def _on_monitor_stop_clicked(self):
        if self.on_monitor_stop:
            self.on_monitor_stop()

    def _on_classify_clicked(self):
        """수동 분류 실행"""
        folder = self.folder_path_var.get()
        if not folder:
            messagebox.showerror("오류", "폴더를 선택해주세요.")
            return
        
        if self.on_classify:
            # 카테고리는 config 기본값 사용 (GUI에서 별도 입력받지 않음)
            self.on_classify(folder, cfg.DEFAULT_CATEGORIES)

    def _on_undo_clicked(self):
        if self.on_undo:
            self.on_undo()

    def _on_redo_clicked(self):
        if self.on_redo:
            self.on_redo()

    def _save_llm_settings(self):
        api_key = self.api_key_entry.get().strip()
        base_url = self.base_url_entry.get().strip()
        model = self.model_entry.get().strip()

        if not api_key:
            messagebox.showwarning("경고", "API Key를 입력해주세요.")
            return

        try:
            cfg.save_to_env(api_key, base_url, model)
            messagebox.showinfo("성공", "설정이 저장되었습니다.")
            if self.on_settings_changed:
                self.on_settings_changed()
        except Exception as e:
            messagebox.showerror("오류", f"설정 저장 실패: {e}")

    # =========================================================================
    # Public Methods (Called by main.py)
    # =========================================================================
    
    # main.py에서 set_on_classify를 호출할 수 있음.
    def set_on_classify(self, callback: Callable) -> None:
        self.on_classify = callback

    def set_on_start_monitoring(self, callback: Callable):
        self.on_monitor_start = callback
        
    def set_on_stop_monitoring(self, callback: Callable):
        self.on_monitor_stop = callback

    def set_on_undo(self, callback: Callable):
        self.on_undo = callback

    def set_on_redo(self, callback: Callable):
        self.on_redo = callback

    def set_on_export_log(self, callback: Callable):
        self.on_export_log = callback

    def set_on_settings_changed(self, callback: Callable):
        self.on_settings_changed = callback

    def update_status(self, message: str):
        self.status_var.set(message)
        
    def update_progress(self, value: float):
        self.progress_var.set(value)

    def show_info_dialog(self, title: str, message: str):
        messagebox.showinfo(title, message)
        
    def show_error_dialog(self, title: str, message: str):
        messagebox.showerror(title, message)

    def show_warning_dialog(self, title: str, message: str):
        messagebox.showwarning(title, message)

    def show_message(self, title: str, message: str, message_type: str = "info"):
        if message_type == "info":
            self.show_info_dialog(title, message)
        elif message_type == "warning":
            self.show_warning_dialog(title, message)
        elif message_type == "error":
            self.show_error_dialog(title, message)

    def safe_update_ui(self, func: Callable, args: Tuple = ()):
        """Thread-safe UI update"""
        self.root.after(0, lambda: func(*args))

    def on_file_processed_event(self, filename: str, folder: str, status: str):
        """파일 처리 결과를 목록에 추가 (Main thread에서 호출됨)"""
        # 데이터 모델에 추가
        self.log_data.append((filename, folder, status))

        # 목록 제한 (예: 1000개)
        if len(self.log_data) > 1000:
            self.log_data.pop(0)

        # 현재 트리가 화면에 있으면 업데이트
        if self.current_page == "main" and hasattr(self, 'tree') and self.tree.winfo_exists():
            self.tree.insert("", 0, values=(filename, folder, status))

            # Treeview 위젯 자체의 아이템 수도 제한하여 성능 유지
            children = self.tree.get_children()
            if len(children) > 100:
                self.tree.delete(children[-1])

    def _show_settings(self):
        """설정 페이지로 이동 (main.py에서 호출 가능하도록)"""
        self._show_llm_settings_page()

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    gui = FileClassifierGUI()
    gui.run()

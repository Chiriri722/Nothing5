# -*- coding: utf-8 -*-
"""
GUI 모듈 (ui.py)

Tkinter를 사용하여 사용자 친화적인 그래픽 인터페이스를 제공합니다.
파일 분류 프로그램의 메인 UI를 담당합니다.
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import logging
import threading
from typing import Callable, Optional, Dict, Any, List
from pathlib import Path
from queue import Queue
from datetime import datetime

# 설정 저장을 위해 import
from config.config import save_to_env, OPENAI_API_KEY, OPENAI_BASE_URL, LLM_MODEL

logger = logging.getLogger(__name__)


# 색상 및 폰트 정의
COLORS = {
    'bg': '#f0f0f0',
    'fg': '#333333',
    'accent': '#0078d4',
    'success': '#107c10',
    'warning': '#ffb900',
    'error': '#e81123',
    'frame_bg': '#ffffff',
}

FONTS = {
    'title': ('Arial', 14, 'bold'),
    'normal': ('Arial', 10),
    'small': ('Arial', 9),
    'mono': ('Courier', 9),
}


class SettingsDialog(tk.Toplevel):
    """설정 대화상자"""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("설정")
        self.geometry("500x400")
        self.resizable(False, False)
        self.parent = parent

        self.api_key_var = tk.StringVar(value=OPENAI_API_KEY)
        self.base_url_var = tk.StringVar(value=OPENAI_BASE_URL)
        self.model_var = tk.StringVar(value=LLM_MODEL)
        self.provider_var = tk.StringVar(value="OpenAI")

        self._setup_ui()

    def _setup_ui(self):
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Provider Selection
        ttk.Label(main_frame, text="API 제공자 선택:", font=FONTS['normal']).pack(anchor=tk.W, pady=(0, 5))
        provider_combo = ttk.Combobox(
            main_frame,
            textvariable=self.provider_var,
            values=["OpenAI", "Ollama (Local)", "Custom"],
            state="readonly"
        )
        provider_combo.pack(fill=tk.X, pady=(0, 15))
        provider_combo.bind("<<ComboboxSelected>>", self._on_provider_change)

        # API Key
        ttk.Label(main_frame, text="API Key:", font=FONTS['normal']).pack(anchor=tk.W, pady=(0, 5))
        self.api_key_entry = ttk.Entry(main_frame, textvariable=self.api_key_var, show="*")
        self.api_key_entry.pack(fill=tk.X, pady=(0, 5))

        # Base URL
        ttk.Label(main_frame, text="Base URL:", font=FONTS['normal']).pack(anchor=tk.W, pady=(0, 5))
        self.base_url_entry = ttk.Entry(main_frame, textvariable=self.base_url_var)
        self.base_url_entry.pack(fill=tk.X, pady=(0, 15))

        # Model
        ttk.Label(main_frame, text="모델 이름:", font=FONTS['normal']).pack(anchor=tk.W, pady=(0, 5))
        self.model_entry = ttk.Entry(main_frame, textvariable=self.model_var)
        self.model_entry.pack(fill=tk.X, pady=(0, 20))

        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)

        ttk.Button(btn_frame, text="저장", command=self._save_settings).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="취소", command=self.destroy).pack(side=tk.RIGHT, padx=5)

        # Initial check
        self._check_provider_preset()

    def _check_provider_preset(self):
        """현재 URL에 따라 Provider 콤보박스 설정"""
        url = self.base_url_var.get()
        if "api.openai.com" in url:
            self.provider_var.set("OpenAI")
        elif "localhost" in url or "127.0.0.1" in url:
            self.provider_var.set("Ollama (Local)")
        else:
            self.provider_var.set("Custom")

    def _on_provider_change(self, event):
        provider = self.provider_var.get()
        if provider == "OpenAI":
            self.base_url_var.set("https://api.openai.com/v1")
            if not self.model_var.get():
                self.model_var.set("gpt-3.5-turbo")
        elif provider == "Ollama (Local)":
            self.base_url_var.set("http://localhost:11434/v1")
            self.api_key_var.set("ollama") # Dummy key
            if not self.model_var.get():
                self.model_var.set("llama3")

    def _save_settings(self):
        api_key = self.api_key_var.get().strip()
        base_url = self.base_url_var.get().strip()
        model = self.model_var.get().strip()

        if not api_key:
            messagebox.showerror("오류", "API Key를 입력해주세요.")
            return

        try:
            save_to_env(api_key, base_url, model)
            messagebox.showinfo("성공", "설정이 저장되었습니다.\n프로그램이 새 설정을 사용하도록 업데이트됩니다.")

            # 부모 창에 설정 변경 알림 (재초기화 요청)
            if hasattr(self.parent, 'on_settings_changed') and self.parent.on_settings_changed:
                 self.parent.on_settings_changed()

            self.destroy()
        except Exception as e:
            messagebox.showerror("오류", f"설정 저장 실패: {e}")


class FileClassifierGUI:
    """
    파일 분류 프로그램 GUI 클래스
    
    Tkinter 기반 사용자 인터페이스를 제공합니다.
    메뉴바, 상태 표시, 파일 목록, 제어 버튼, 통계 정보 등을 포함합니다.
    """
    
    def __init__(self, root: tk.Tk = None, window_width: int = 900, window_height: int = 700):
        """
        FileClassifierGUI 초기화
        
        Args:
            root (tk.Tk): Tkinter 루트 윈도우 (None이면 새로 생성)
            window_width (int): 창 너비
            window_height (int): 창 높이
        """
        self.root = root if root is not None else tk.Tk()
        self.root.title("LLM 기반 파일 자동 분류 프로그램")
        self.root.geometry(f"{window_width}x{window_height}")
        self.root.minsize(600, 400)
        
        # 상태 변수
        self.folder_path_var = tk.StringVar()
        self.status_var = tk.StringVar(value="준비됨")
        self.progress_var = tk.DoubleVar(value=0)
        
        # 모니터링 상태
        self.is_monitoring = False
        self.is_paused = False
        
        # 통계 데이터
        self.stats = {
            'total_processed': 0,
            'categories': {},
            'processing_speed': 0.0,  # files/min
        }
        
        # 파일 목록
        self.file_list_data: List[tuple] = []  # (filename, category, status)
        
        # UI 업데이트 큐 (스레드 안전성)
        self.ui_queue: Queue = Queue()
        
        # 콜백 함수
        self.on_file_processed: Optional[Callable] = None
        self.on_start_monitoring: Optional[Callable] = None
        self.on_stop_monitoring: Optional[Callable] = None
        self.on_undo: Optional[Callable] = None
        self.on_redo: Optional[Callable] = None
        self.on_export_log: Optional[Callable] = None
        self.on_settings_changed: Optional[Callable] = None
        
        # UI 생성
        self._setup_ui()
        
        # UI 업데이트 체크 시작
        self._check_ui_queue()
        
        logger.info("GUI 초기화 완료")

        # 초기 설정 확인 (API 키 없으면 설정창 띄우기)
        self.root.after(500, self._check_initial_config)

    def _check_initial_config(self):
        """초기 설정 확인 및 설정창 표시"""
        from config.config import OPENAI_API_KEY
        if not OPENAI_API_KEY:
             if messagebox.askyesno("초기 설정", "API 키가 설정되지 않았습니다.\n지금 설정하시겠습니까?"):
                 self._show_settings()
    
    def _setup_ui(self) -> None:
        """
        메인 UI 설정
        메뉴바, 프레임들, 위젯들을 생성하고 배치합니다.
        """
        # 메뉴바 생성
        self._create_menubar()
        
        # 메인 프레임
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 상단 프레임: 폴더 선택
        self._create_top_frame(main_frame)
        
        # 제어 프레임: 제어 버튼들
        self._create_control_frame(main_frame)
        
        # 중앙 프레임: 상태 정보 및 파일 목록
        self._create_middle_frame(main_frame)
        
        # 통계 프레임: 요약 정보
        self._create_statistics_frame(main_frame)
        
        # 상태 표시줄
        self._create_status_bar()
    
    def _create_menubar(self) -> None:
        """
        메뉴바 생성
        File, Edit, View, Help 메뉴를 포함합니다.
        """
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File 메뉴
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="파일(F)", menu=file_menu)
        file_menu.add_command(label="폴더 선택...", command=self.browse_folder)
        file_menu.add_command(label="로그 내보내기...", command=self._export_log)
        file_menu.add_separator()
        file_menu.add_command(label="종료", command=self._on_exit, accelerator="Alt+F4")
        
        # Edit 메뉴
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="편집(E)", menu=edit_menu)
        edit_menu.add_command(label="실행 취소", command=self._undo_operation, accelerator="Ctrl+Z")
        edit_menu.add_command(label="다시 실행", command=self._redo_operation, accelerator="Ctrl+Y")
        edit_menu.add_separator()
        edit_menu.add_command(label="히스토리 초기화", command=self._clear_history)
        
        # View 메뉴
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="보기(V)", menu=view_menu)
        view_menu.add_command(label="새로 고침", command=self._refresh, accelerator="F5")
        view_menu.add_command(label="통계 표시", command=self._show_statistics)
        view_menu.add_separator()
        view_menu.add_command(label="작업 히스토리", command=self._show_history)
        
        # Help 메뉴
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="도움말(H)", menu=help_menu)
        help_menu.add_command(label="설정...", command=self._show_settings)
        help_menu.add_command(label="도움말 및 설명서", command=self._show_help)
        help_menu.add_separator()
        help_menu.add_command(label="정보", command=self._show_about)
        
        # 단축키 바인딩
        self.root.bind('<Control-z>', lambda e: self._undo_operation())
        self.root.bind('<Control-y>', lambda e: self._redo_operation())
        self.root.bind('<F5>', lambda e: self._refresh())
    
    def _create_top_frame(self, parent: ttk.Frame) -> None:
        """
        상단 프레임: 폴더 선택
        폴더 선택 버튼, 경로 표시, 초기화 버튼을 포함합니다.
        """
        top_frame = ttk.LabelFrame(parent, text="폴더 선택", padding="10")
        top_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 폴더 경로 선택
        path_frame = ttk.Frame(top_frame)
        path_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(path_frame, text="경로:").pack(side=tk.LEFT, padx=5)
        path_entry = ttk.Entry(path_frame, textvariable=self.folder_path_var, state='readonly')
        path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        ttk.Button(path_frame, text="찾기", command=self.browse_folder, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(path_frame, text="초기화", command=self.clear_selection, width=10).pack(side=tk.LEFT, padx=5)
    
    def _create_control_frame(self, parent: ttk.Frame) -> None:
        """
        제어 프레임: 제어 버튼들
        시작, 중지, 일시중지, 재개, undo, redo 버튼을 포함합니다.
        """
        control_frame = ttk.LabelFrame(parent, text="제어", padding="10")
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        button_style = {'width': 12}
        
        self.btn_start = ttk.Button(
            control_frame, text="시작", command=self.start_monitoring, **button_style
        )
        self.btn_start.pack(side=tk.LEFT, padx=5)
        
        self.btn_stop = ttk.Button(
            control_frame, text="중지", command=self.stop_monitoring, state=tk.DISABLED, **button_style
        )
        self.btn_stop.pack(side=tk.LEFT, padx=5)
        
        self.btn_pause = ttk.Button(
            control_frame, text="일시중지", command=self.pause_monitoring, state=tk.DISABLED, **button_style
        )
        self.btn_pause.pack(side=tk.LEFT, padx=5)
        
        self.btn_resume = ttk.Button(
            control_frame, text="재개", command=self.resume_monitoring, state=tk.DISABLED, **button_style
        )
        self.btn_resume.pack(side=tk.LEFT, padx=5)
        
        ttk.Separator(control_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        self.btn_undo = ttk.Button(
            control_frame, text="실행 취소", command=self._undo_operation, **button_style
        )
        self.btn_undo.pack(side=tk.LEFT, padx=5)
        
        self.btn_redo = ttk.Button(
            control_frame, text="다시 실행", command=self._redo_operation, **button_style
        )
        self.btn_redo.pack(side=tk.LEFT, padx=5)
    
    def _create_middle_frame(self, parent: ttk.Frame) -> None:
        """
        중앙 프레임: 상태 정보 및 파일 목록
        현재 상태, 진행률, 처리된 파일 목록을 표시합니다.
        """
        middle_frame = ttk.LabelFrame(parent, text="상태 및 파일 목록", padding="10")
        middle_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 상태 정보 프레임
        status_info_frame = ttk.Frame(middle_frame)
        status_info_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(status_info_frame, text="상태:", font=FONTS['normal']).pack(side=tk.LEFT, padx=5)
        ttk.Label(status_info_frame, textvariable=self.status_var, font=FONTS['normal']).pack(
            side=tk.LEFT, padx=5
        )
        
        # 진행률 표시
        progress_frame = ttk.Frame(middle_frame)
        progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(progress_frame, text="진행률:").pack(anchor=tk.W)
        self.progress_bar = ttk.Progressbar(
            progress_frame, variable=self.progress_var, maximum=100, mode='determinate'
        )
        self.progress_bar.pack(fill=tk.X, pady=5)
        
        # 파일 목록 프레임
        file_list_frame = ttk.Frame(middle_frame)
        file_list_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(file_list_frame, text="처리된 파일:", font=FONTS['normal']).pack(anchor=tk.W)
        
        # 리스트박스와 스크롤바
        list_scroll_frame = ttk.Frame(file_list_frame)
        list_scroll_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        scrollbar = ttk.Scrollbar(list_scroll_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.file_listbox = tk.Listbox(
            list_scroll_frame,
            yscrollcommand=scrollbar.set,
            font=FONTS['mono'],
            height=10
        )
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.file_listbox.yview)
        
        # 우클릭 메뉴 바인딩
        self.file_listbox.bind('<Button-3>', self._show_listbox_context_menu)
    
    def _create_statistics_frame(self, parent: ttk.Frame) -> None:
        """
        통계 프레임: 요약 정보
        처리된 파일 수, 카테고리별 통계, 처리 속도 등을 표시합니다.
        """
        stats_frame = ttk.LabelFrame(parent, text="통계", padding="10")
        stats_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 통계 정보 표시
        stats_grid = ttk.Frame(stats_frame)
        stats_grid.pack(fill=tk.X)
        
        ttk.Label(stats_grid, text="처리된 파일:", font=FONTS['normal']).pack(side=tk.LEFT, padx=10)
        self.label_total = ttk.Label(stats_grid, text="0개", font=FONTS['normal'], foreground='blue')
        self.label_total.pack(side=tk.LEFT, padx=10)
        
        ttk.Separator(stats_grid, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        ttk.Label(stats_grid, text="처리 속도:", font=FONTS['normal']).pack(side=tk.LEFT, padx=10)
        self.label_speed = ttk.Label(stats_grid, text="0.0 files/min", font=FONTS['normal'], foreground='green')
        self.label_speed.pack(side=tk.LEFT, padx=10)
        
        # 카테고리별 통계
        ttk.Separator(stats_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        
        category_frame = ttk.Frame(stats_frame)
        category_frame.pack(fill=tk.X)
        
        ttk.Label(category_frame, text="카테고리별 분류:", font=FONTS['normal']).pack(anchor=tk.W)
        self.label_categories = ttk.Label(category_frame, text="(분류 진행 중...)", font=FONTS['small'])
        self.label_categories.pack(anchor=tk.W, pady=5)
    
    def _create_status_bar(self) -> None:
        """
        상태 표시줄
        마지막 작업 정보 및 현재 시간을 표시합니다.
        """
        self.status_bar = ttk.Frame(self.root, relief=tk.SUNKEN, height=25)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.label_status_left = ttk.Label(self.status_bar, text="준비됨")
        self.label_status_left.pack(side=tk.LEFT, padx=10, pady=5)
        
        ttk.Separator(self.status_bar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        self.label_status_right = ttk.Label(self.status_bar, text=self._get_current_time())
        self.label_status_right.pack(side=tk.RIGHT, padx=10, pady=5)
    
    def browse_folder(self) -> None:
        """
        폴더 선택 대화상자
        filedialog.askdirectory()를 사용하여 폴더를 선택합니다.
        """
        folder = filedialog.askdirectory(title="분류할 폴더 선택")
        if folder:
            self.folder_path_var.set(folder)
            logger.info(f"폴더 선택됨: {folder}")
            self._update_status_bar(f"폴더 선택됨: {Path(folder).name}")
    
    def clear_selection(self) -> None:
        """
        선택한 폴더 제거
        """
        self.folder_path_var.set("")
        logger.info("폴더 선택 초기화")
        self._update_status_bar("폴더 선택 초기화됨")
    
    def start_monitoring(self) -> None:
        """
        파일 모니터링 시작
        폴더 유효성 검사 후 모니터링을 시작합니다.
        """
        folder = self.folder_path_var.get()
        if not folder or not Path(folder).exists():
            messagebox.showerror("오류", "유효한 폴더를 선택하세요.")
            return
        
        if self.is_monitoring:
            messagebox.showwarning("경고", "이미 모니터링 중입니다.")
            return
        
        self.is_monitoring = True
        self.is_paused = False
        self.update_status("모니터링 중...")
        self._update_button_states()
        logger.info(f"모니터링 시작: {folder}")
        self._update_status_bar("모니터링 시작됨")
        
        if self.on_start_monitoring:
            self.run_in_background(self.on_start_monitoring, (folder,))
    
    def stop_monitoring(self) -> None:
        """
        파일 모니터링 중지
        """
        if not self.is_monitoring:
            messagebox.showwarning("경고", "모니터링 중이 아닙니다.")
            return
        
        self.is_monitoring = False
        self.is_paused = False
        self.update_status("중지됨")
        self._update_button_states()
        logger.info("모니터링 중지")
        self._update_status_bar("모니터링 중지됨")
        
        if self.on_stop_monitoring:
            self.on_stop_monitoring()
    
    def pause_monitoring(self) -> None:
        """
        파일 모니터링 일시 중지
        """
        if not self.is_monitoring or self.is_paused:
            return
        
        self.is_paused = True
        self.update_status("일시 중지됨")
        self._update_button_states()
        logger.info("모니터링 일시 중지")
        self._update_status_bar("모니터링 일시 중지됨")
    
    def resume_monitoring(self) -> None:
        """
        파일 모니터링 재개
        """
        if not self.is_monitoring or not self.is_paused:
            return
        
        self.is_paused = False
        self.update_status("모니터링 중...")
        self._update_button_states()
        logger.info("모니터링 재개")
        self._update_status_bar("모니터링 재개됨")
    
    def _undo_operation(self) -> None:
        """
        마지막 작업 취소 (undo_manager 연동)
        """
        if self.on_undo:
            self.on_undo()
            self.update_status("작업 취소됨")
            self._update_status_bar("작업 취소됨")
        else:
            messagebox.showinfo("정보", "취소할 작업이 없습니다.")
    
    def _redo_operation(self) -> None:
        """
        취소된 작업 복원 (undo_manager 연동)
        """
        if self.on_redo:
            self.on_redo()
            self.update_status("작업 복원됨")
            self._update_status_bar("작업 복원됨")
        else:
            messagebox.showinfo("정보", "복원할 작업이 없습니다.")
    
    def on_file_processed_event(self, filename: str, folder_name: str, status: str = "✓") -> None:
        """
        파일 처리 완료 시 콜백
        파일 목록, 통계 업데이트, UI 새로 고침을 수행합니다.
        
        Args:
            filename (str): 파일명
            folder_name (str): 분류된 폴더명
            status (str): 상태 (✓, ✗ 등)
        """
        self.add_file_to_list(filename, folder_name, status)
        self.update_statistics()
        logger.info(f"파일 처리: {filename} → {folder_name}")
    
    def add_file_to_list(self, filename: str, folder: str, status: str = "✓") -> None:
        """
        파일 목록에 항목 추가
        
        Args:
            filename (str): 파일명
            folder (str): 분류된 폴더
            status (str): 상태
        """
        entry = f"[{status}] {filename} → {folder}"
        self.file_listbox.insert(tk.END, entry)
        self.file_listbox.see(tk.END)  # 자동으로 마지막 항목으로 스크롤
        self.file_list_data.append((filename, folder, status))
    
    def remove_file_from_list(self, index: int) -> None:
        """
        파일 목록에서 항목 제거
        
        Args:
            index (int): 제거할 항목의 인덱스
        """
        if 0 <= index < len(self.file_list_data):
            self.file_listbox.delete(index)
            self.file_list_data.pop(index)
    
    def clear_file_list(self) -> None:
        """
        파일 목록 초기화
        """
        self.file_listbox.delete(0, tk.END)
        self.file_list_data.clear()
        logger.info("파일 목록 초기화")
    
    def update_statistics(self, **kwargs) -> None:
        """
        통계 정보 업데이트 및 표시
        
        Kwargs:
            total (int): 처리된 파일 수
            speed (float): 처리 속도 (files/min)
            categories (dict): 카테고리별 통계
        """
        if 'total' in kwargs:
            self.stats['total_processed'] = kwargs['total']
        else:
            self.stats['total_processed'] = len(self.file_list_data)
        
        if 'speed' in kwargs:
            self.stats['processing_speed'] = kwargs['speed']
        
        if 'categories' in kwargs:
            self.stats['categories'] = kwargs['categories']
        else:
            # 자동으로 파일 목록에서 카테고리 통계 생성
            self.stats['categories'].clear()
            for _, folder, _ in self.file_list_data:
                self.stats['categories'][folder] = self.stats['categories'].get(folder, 0) + 1
        
        # UI 업데이트
        self.label_total.config(text=f"{self.stats['total_processed']}개")
        self.label_speed.config(text=f"{self.stats['processing_speed']:.1f} files/min")
        
        # 카테고리별 통계 표시
        cat_text = " | ".join(
            f"{cat}: {count}개" for cat, count in sorted(self.stats['categories'].items())
        )
        if not cat_text:
            cat_text = "(분류 진행 중...)"
        self.label_categories.config(text=cat_text)
    
    def update_status(self, message: str) -> None:
        """
        상태 메시지 업데이트
        
        Args:
            message (str): 상태 메시지
        """
        self.status_var.set(message)
        self.root.update_idletasks()
    
    def update_progress(self, value: float) -> None:
        """
        진행률 업데이트
        
        Args:
            value (float): 진행률 (0-100)
        """
        self.progress_var.set(min(100, max(0, value)))
        self.root.update_idletasks()
    
    def _update_button_states(self) -> None:
        """
        모니터링 상태에 따라 버튼 활성화/비활성화
        """
        if self.is_monitoring:
            self.btn_start.config(state=tk.DISABLED)
            self.btn_stop.config(state=tk.NORMAL)
            if self.is_paused:
                self.btn_pause.config(state=tk.DISABLED)
                self.btn_resume.config(state=tk.NORMAL)
            else:
                self.btn_pause.config(state=tk.NORMAL)
                self.btn_resume.config(state=tk.DISABLED)
        else:
            self.btn_start.config(state=tk.NORMAL)
            self.btn_stop.config(state=tk.DISABLED)
            self.btn_pause.config(state=tk.DISABLED)
            self.btn_resume.config(state=tk.DISABLED)
    
    def _update_status_bar(self, message: str) -> None:
        """
        상태 표시줄 업데이트
        
        Args:
            message (str): 상태 메시지
        """
        self.label_status_left.config(text=message)
        self.label_status_right.config(text=self._get_current_time())
    
    def _get_current_time(self) -> str:
        """
        현재 시간 반환 (HH:MM:SS 형식)
        
        Returns:
            str: 현재 시간 문자열
        """
        return datetime.now().strftime("%H:%M:%S")
    
    def run_in_background(self, func: Callable, args: tuple = ()) -> None:
        """
        백그라운드 스레드에서 작업 실행
        무거운 작업이 UI를 블록하지 않도록 합니다.
        
        Args:
            func (Callable): 실행할 함수
            args (tuple): 함수에 전달할 인자
        """
        thread = threading.Thread(target=func, args=args, daemon=True)
        thread.start()
    
    def safe_update_ui(self, func: Callable, args: tuple = ()) -> None:
        """
        스레드 안전 UI 업데이트
        큐를 사용하여 메인 스레드에서 UI를 업데이트합니다.
        
        Args:
            func (Callable): 실행할 UI 업데이트 함수
            args (tuple): 함수에 전달할 인자
        """
        self.ui_queue.put((func, args))
    
    def _check_ui_queue(self) -> None:
        """
        UI 큐 확인 및 업데이트 실행
        메인 루프에서 주기적으로 호출됩니다.
        """
        try:
            while True:
                func, args = self.ui_queue.get_nowait()
                func(*args)
        except:
            pass
        
        # 100ms 후 다시 확인
        self.root.after(100, self._check_ui_queue)
    
    def _show_listbox_context_menu(self, event) -> None:
        """
        파일 목록 우클릭 컨텍스트 메뉴 표시
        """
        context_menu = tk.Menu(self.root, tearoff=0)
        context_menu.add_command(label="복사", command=lambda: self._copy_listbox_item(event))
        context_menu.add_command(label="삭제", command=lambda: self._delete_listbox_item(event))
        context_menu.add_separator()
        context_menu.add_command(label="모두 지우기", command=self.clear_file_list)
        
        context_menu.post(event.x_root, event.y_root)
    
    def _copy_listbox_item(self, event) -> None:
        """
        선택된 파일 목록 항목을 클립보드에 복사
        """
        selection = self.file_listbox.curselection()
        if selection:
            item = self.file_listbox.get(selection)
            self.root.clipboard_clear()
            self.root.clipboard_append(item)
            messagebox.showinfo("정보", "클립보드에 복사되었습니다.")
    
    def _delete_listbox_item(self, event) -> None:
        """
        선택된 파일 목록 항목 삭제
        """
        selection = self.file_listbox.curselection()
        if selection:
            self.remove_file_from_list(selection)
            self.update_statistics()
    
    def _show_settings(self) -> None:
        """
        설정 대화 표시
        """
        SettingsDialog(self)
    
    def _show_history(self) -> None:
        """
        작업 히스토리 대화 표시
        """
        messagebox.showinfo(
            "작업 히스토리",
            f"처리된 파일: {len(self.file_list_data)}개\n\n"
            "상세 히스토리를 보려면 통계를 확인하세요."
        )
    
    def _clear_history(self) -> None:
        """
        작업 히스토리 초기화
        """
        if messagebox.askyesno("확인", "히스토리를 모두 초기화하시겠습니까?"):
            self.clear_file_list()
            self.stats['categories'].clear()
            self.update_statistics(total=0, speed=0.0)
            self._update_status_bar("히스토리 초기화됨")
            logger.info("히스토리 초기화")
    
    def _refresh(self) -> None:
        """
        UI 새로 고침 (F5)
        """
        self.root.update()
        self._update_status_bar("새로 고침됨")
    
    def _show_statistics(self) -> None:
        """
        통계 표시 팝업
        """
        stats_text = (
            f"파일 분류 통계\n\n"
            f"총 처리된 파일: {self.stats['total_processed']}개\n"
            f"처리 속도: {self.stats['processing_speed']:.1f} files/min\n\n"
            f"카테고리별 분류:\n"
        )
        for cat, count in sorted(self.stats['categories'].items()):
            stats_text += f"  - {cat}: {count}개\n"
        
        messagebox.showinfo("통계", stats_text)
    
    def _export_log(self) -> None:
        """
        작업 로그 내보내기
        """
        file_path = filedialog.asksaveasfilename(
            defaultextension=".log",
            filetypes=[("Log files", "*.log"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        if file_path:
            if self.on_export_log:
                self.on_export_log(file_path)
            else:
                # 간단한 로그 내보내기
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("파일 분류 로그\n")
                    f.write(f"생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                    f.write(f"총 처리 파일: {len(self.file_list_data)}개\n\n")
                    f.write("처리된 파일:\n")
                    for filename, folder, status in self.file_list_data:
                        f.write(f"[{status}] {filename} → {folder}\n")
                messagebox.showinfo("완료", f"로그가 저장되었습니다.\n{file_path}")
            logger.info(f"로그 내보내기: {file_path}")
    
    def _show_help(self) -> None:
        """
        도움말 및 설명서 표시
        """
        help_text = (
            "LLM 기반 파일 자동 분류 프로그램\n\n"
            "주요 기능:\n"
            "1. 폴더 선택: 정리할 대상 폴더를 선택합니다.\n"
            "2. 모니터링 시작: 폴더의 파일을 LLM으로 자동 분류합니다.\n"
            "3. 일시중지/재개: 모니터링을 일시중지했다가 재개할 수 있습니다.\n"
            "4. 실행 취소/복원: 분류 작업을 취소하고 복원할 수 있습니다.\n"
            "5. 통계 확인: 처리된 파일 수와 카테고리별 분류 현황을 확인합니다.\n"
            "6. 로그 내보내기: 작업 로그를 파일로 저장합니다.\n\n"
            "단축키:\n"
            "Ctrl+Z: 실행 취소\n"
            "Ctrl+Y: 다시 실행\n"
            "F5: 새로 고침"
        )
        messagebox.showinfo("도움말", help_text)
    
    def _show_about(self) -> None:
        """
        프로그램 정보 표시
        """
        about_text = (
            "LLM 기반 파일 자동 분류 프로그램\n\n"
            "버전: 1.0.0\n"
            "작성자: AI File Classifier Team\n\n"
            "이 프로그램은 LLM(대규모 언어 모델)을 사용하여\n"
            "파일을 자동으로 분류합니다.\n\n"
            "© 2025. All rights reserved."
        )
        messagebox.showinfo("정보", about_text)
    
    def _on_exit(self) -> None:
        """
        프로그램 종료
        """
        if self.is_monitoring:
            if messagebox.askyesno("확인", "모니터링 중입니다. 종료하시겠습니까?"):
                self.stop_monitoring()
                self.root.quit()
        else:
            if messagebox.askyesno("확인", "프로그램을 종료하시겠습니까?"):
                self.root.quit()
    
    def show_error_dialog(self, title: str, message: str) -> None:
        """
        오류 대화 표시
        
        Args:
            title (str): 제목
            message (str): 메시지
        """
        messagebox.showerror(title, message)
    
    def show_warning_dialog(self, title: str, message: str) -> None:
        """
        경고 대화 표시
        
        Args:
            title (str): 제목
            message (str): 메시지
        """
        messagebox.showwarning(title, message)
    
    def show_info_dialog(self, title: str, message: str) -> None:
        """
        정보 대화 표시
        
        Args:
            title (str): 제목
            message (str): 메시지
        """
        messagebox.showinfo(title, message)
    
    def show_confirmation_dialog(self, title: str, message: str) -> bool:
        """
        확인 대화 표시
        
        Args:
            title (str): 제목
            message (str): 메시지
        
        Returns:
            bool: 확인(True) 또는 취소(False)
        """
        return messagebox.askyesno(title, message)
    
    def run(self) -> None:
        """
        GUI 실행
        Tkinter 메인 루프를 시작합니다.
        """
        logger.info("GUI 시작")
        self.root.mainloop()
    
    def set_on_file_processed(self, callback: Callable) -> None:
        """
        파일 처리 콜백 설정
        
        Args:
            callback (Callable): 콜백 함수
        """
        self.on_file_processed = callback
    
    def set_on_start_monitoring(self, callback: Callable) -> None:
        """
        모니터링 시작 콜백 설정
        
        Args:
            callback (Callable): 콜백 함수
        """
        self.on_start_monitoring = callback
    
    def set_on_stop_monitoring(self, callback: Callable) -> None:
        """
        모니터링 중지 콜백 설정
        
        Args:
            callback (Callable): 콜백 함수
        """
        self.on_stop_monitoring = callback
    
    def set_on_undo(self, callback: Callable) -> None:
        """
        실행 취소 콜백 설정
        
        Args:
            callback (Callable): 콜백 함수
        """
        self.on_undo = callback
    
    def set_on_redo(self, callback: Callable) -> None:
        """
        다시 실행 콜백 설정
        
        Args:
            callback (Callable): 콜백 함수
        """
        self.on_redo = callback
    
    def set_on_export_log(self, callback: Callable) -> None:
        """
        로그 내보내기 콜백 설정
        
        Args:
            callback (Callable): 콜백 함수
        """
        self.on_export_log = callback

    def set_on_settings_changed(self, callback: Callable) -> None:
        """
        설정 변경 콜백 설정
        """
        self.on_settings_changed = callback


if __name__ == "__main__":
    # 테스트 코드
    root = tk.Tk()
    gui = FileClassifierGUI(root)
    gui.show_info_dialog("정보", "GUI가 초기화되었습니다.")
    
    # 테스트 데이터 추가
    gui.add_file_to_list("test.pdf", "문서", "✓")
    gui.add_file_to_list("image.jpg", "이미지", "✓")
    gui.update_statistics()
    
    gui.run()
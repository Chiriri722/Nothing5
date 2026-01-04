# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinterdnd2 import DND_FILES
import logging
import config.config as cfg
from typing import Callable, Optional, List, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

class MainPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        # Variables
        self.folder_path_var = tk.StringVar()
        self.status_var = tk.StringVar(value="준비됨")
        self.progress_var = tk.DoubleVar()
        self.log_data: List[Tuple[str, str, str]] = []

        self._init_ui()

    def _init_ui(self):
        # Title
        ttk.Label(self, text="파일 분류 메인", style="Title.TLabel").pack(anchor="w", pady=(0, 20))

        # 1. Path Selection & DnD
        path_frame = ttk.LabelFrame(self, text="작업 폴더 (여기에 폴더 드래그 앤 드롭)", padding=10)
        path_frame.pack(fill=tk.X, pady=(0, 10))

        entry = ttk.Entry(path_frame, textvariable=self.folder_path_var)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        try:
            entry.drop_target_register(DND_FILES)
            entry.dnd_bind('<<Drop>>', self._on_drop)
            path_frame.drop_target_register(DND_FILES)
            path_frame.dnd_bind('<<Drop>>', self._on_drop)
        except Exception as e:
            logger.warning(f"DnD registration failed: {e}")

        ttk.Button(path_frame, text="찾기", command=self._select_folder).pack(side=tk.LEFT)

        # 2. Control Buttons
        control_frame = ttk.Frame(self)
        control_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(control_frame, text="▶ 모니터링 시작", command=self._on_monitor_start_clicked).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(control_frame, text="⏹ 모니터링 중지", command=self._on_monitor_stop_clicked).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Separator(control_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        ttk.Button(control_frame, text="⚡ 지금 분류 실행", command=self._on_classify_clicked).pack(side=tk.LEFT, padx=(0, 5))

        ttk.Separator(control_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        ttk.Button(control_frame, text="↩ 실행 취소", command=self._on_undo_clicked).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(control_frame, text="↪ 다시 실행", command=self._on_redo_clicked).pack(side=tk.LEFT, padx=(0, 5))

        # 3. Status & Progress
        status_frame = ttk.Frame(self)
        status_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(status_frame, text="상태: ").pack(side=tk.LEFT)
        ttk.Label(status_frame, textvariable=self.status_var, foreground="blue").pack(side=tk.LEFT)

        progress = ttk.Progressbar(self, variable=self.progress_var, maximum=100)
        progress.pack(fill=tk.X, pady=(0, 10))

        # 4. File List (Treeview)
        list_frame = ttk.LabelFrame(self, text="처리 내역", padding=10)
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

    def _on_drop(self, event):
        path = event.data
        if path.startswith('{') and path.endswith('}'):
            path = path[1:-1]
        if Path(path).is_dir():
            self.folder_path_var.set(path)
            logger.info(f"DnD 폴더 선택됨: {path}")
        else:
            messagebox.showwarning("경고", "폴더를 드롭해주세요.")

    def _select_folder(self):
        folder = filedialog.askdirectory(title="분류할 폴더 선택")
        if folder:
            self.folder_path_var.set(folder)

    def _on_monitor_start_clicked(self):
        folder = self.folder_path_var.get()
        if not folder:
            messagebox.showerror("오류", "폴더를 선택해주세요.")
            return
        if self.controller.on_monitor_start:
            self.controller.on_monitor_start(folder)

    def _on_monitor_stop_clicked(self):
        if self.controller.on_monitor_stop:
            self.controller.on_monitor_stop()

    def _on_classify_clicked(self):
        folder = self.folder_path_var.get()
        if not folder:
            messagebox.showerror("오류", "폴더를 선택해주세요.")
            return
        if self.controller.on_classify:
            self.controller.on_classify(folder, cfg.DEFAULT_CATEGORIES)

    def _on_undo_clicked(self):
        if self.controller.on_undo:
            self.controller.on_undo()

    def _on_redo_clicked(self):
        if self.controller.on_redo:
            self.controller.on_redo()

    def update_status(self, message: str):
        self.status_var.set(message)

    def update_progress(self, value: float):
        self.progress_var.set(value)

    def add_log_entry(self, filename: str, folder: str, status: str):
        self.log_data.append((filename, folder, status))
        if len(self.log_data) > 1000:
            self.log_data.pop(0)

        if self.winfo_exists():
            self.tree.insert("", 0, values=(filename, folder, status))
            children = self.tree.get_children()
            if len(children) > 100:
                self.tree.delete(children[-1])

    def restore_logs(self, log_data):
        self.log_data = log_data
        if self.winfo_exists():
            for item in self.tree.get_children():
                self.tree.delete(item)
            for item in self.log_data:
                self.tree.insert("", 0, values=item)

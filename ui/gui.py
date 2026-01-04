# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox
from tkinterdnd2 import TkinterDnD
import logging
from typing import Callable, Optional, Tuple, List

from ui.pages.main_page import MainPage
from ui.pages.settings_page import SettingsPage
from ui.pages.env_settings_page import EnvSettingsPage
import config.config as cfg

logger = logging.getLogger(__name__)

class FileClassifierGUI:
    def __init__(self, window_width: int = 900, window_height: int = 700):
        self.root = TkinterDnD.Tk()
        self.root.title("LLM 기반 파일 자동 분류 프로그램")
        self.root.geometry(f"{window_width}x{window_height}")
        
        # Callbacks
        self.on_classify: Optional[Callable] = None
        self.on_monitor_start: Optional[Callable] = None
        self.on_monitor_stop: Optional[Callable] = None
        self.on_undo: Optional[Callable] = None
        self.on_redo: Optional[Callable] = None
        self.on_settings_changed: Optional[Callable] = None
        self.on_export_log: Optional[Callable] = None
        
        self._setup_styles()
        self._init_layout()

        # Pages
        self.pages = {}
        self.current_page_name = None

        self._show_page("main")

    def _setup_styles(self):
        style = ttk.Style()
        style.configure("Sidebar.TFrame", background="#f0f0f0")
        style.configure("Sidebar.TButton", anchor="w", padding=10)
        style.configure("Title.TLabel", font=("Arial", 16, "bold"))
        style.configure("Section.TLabel", font=("Arial", 12, "bold"))

    def _init_layout(self):
        self.main_container = ttk.Frame(self.root)
        self.main_container.pack(fill=tk.BOTH, expand=True)

        # Sidebar
        self.sidebar = ttk.Frame(self.main_container, style="Sidebar.TFrame", width=200)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        ttk.Label(self.sidebar, text="메뉴", style="Section.TLabel", background="#f0f0f0").pack(pady=20, padx=10, anchor="w")

        ttk.Button(self.sidebar, text="🏠 메인 화면", style="Sidebar.TButton",
                   command=lambda: self._show_page("main")).pack(fill=tk.X, padx=5, pady=2)
        ttk.Button(self.sidebar, text="⚙️ LLM 설정", style="Sidebar.TButton",
                   command=lambda: self._show_page("settings")).pack(fill=tk.X, padx=5, pady=2)
        ttk.Button(self.sidebar, text="🛠 환경 설정", style="Sidebar.TButton",
                   command=lambda: self._show_page("env_settings")).pack(fill=tk.X, padx=5, pady=2)

        # Content Area
        self.content_area = ttk.Frame(self.main_container, padding=20)
        self.content_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def _show_page(self, page_name: str):
        # Hide current page
        if self.current_page_name and self.current_page_name in self.pages:
            self.pages[self.current_page_name].pack_forget()

        # Create or show new page
        if page_name not in self.pages:
            if page_name == "main":
                self.pages[page_name] = MainPage(self.content_area, self)
            elif page_name == "settings":
                self.pages[page_name] = SettingsPage(self.content_area, self)
            elif page_name == "env_settings":
                self.pages[page_name] = EnvSettingsPage(self.content_area, self)
        
        self.pages[page_name].pack(fill=tk.BOTH, expand=True)
        self.current_page_name = page_name

    # Public API for main.py integration
    def set_on_classify(self, callback: Callable): self.on_classify = callback
    def set_on_start_monitoring(self, callback: Callable): self.on_monitor_start = callback
    def set_on_stop_monitoring(self, callback: Callable): self.on_monitor_stop = callback
    def set_on_undo(self, callback: Callable): self.on_undo = callback
    def set_on_redo(self, callback: Callable): self.on_redo = callback
    def set_on_export_log(self, callback: Callable): self.on_export_log = callback
    def set_on_settings_changed(self, callback: Callable): self.on_settings_changed = callback

    def update_status(self, message: str):
        if "main" in self.pages:
            self.pages["main"].update_status(message)

    def update_progress(self, value: float):
        if "main" in self.pages:
            self.pages["main"].update_progress(value)

    def on_file_processed_event(self, filename: str, folder: str, status: str):
        if "main" in self.pages:
            self.pages["main"].add_log_entry(filename, folder, status)

    def show_info_dialog(self, title: str, message: str):
        messagebox.showinfo(title, message)
        
    def show_error_dialog(self, title: str, message: str):
        messagebox.showerror(title, message)

    def show_warning_dialog(self, title: str, message: str):
        messagebox.showwarning(title, message)

    def safe_update_ui(self, func: Callable, args: Tuple = ()):
        self.root.after(0, lambda: func(*args))

    def run(self):
        self.root.mainloop()

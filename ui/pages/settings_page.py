# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox
import config.config as cfg

class SettingsPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self._init_ui()

    def _init_ui(self):
        ttk.Label(self, text="LLM API 설정", style="Title.TLabel").pack(anchor="w", pady=(0, 20))

        form_frame = ttk.Frame(self)
        form_frame.pack(anchor="w", fill=tk.X)

        # API Key
        ttk.Label(form_frame, text="API Key:").grid(row=1, column=0, sticky="w", pady=5)
        self.api_key_entry = ttk.Entry(form_frame, width=50, show="*")
        self.api_key_entry.grid(row=1, column=1, sticky="w", pady=5, padx=10)
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
        ttk.Button(self, text="저장 및 적용", command=self._save_llm_settings).pack(anchor="w", pady=20)
        ttk.Label(self, text="* 설정 저장 시 .env 파일이 업데이트됩니다.", foreground="gray").pack(anchor="w")

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
            if self.controller.on_settings_changed:
                self.controller.on_settings_changed()
        except Exception as e:
            messagebox.showerror("오류", f"설정 저장 실패: {e}")

# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox

class EnvSettingsPage(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self._init_ui()

    def _init_ui(self):
        ttk.Label(self, text="환경 설정", style="Title.TLabel").pack(anchor="w", pady=(0, 20))

        form_frame = ttk.Frame(self)
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

        # Save Button
        ttk.Button(self, text="설정 저장", command=lambda: messagebox.showinfo("저장", "환경 설정이 저장되었습니다.")).pack(anchor="w", pady=20)

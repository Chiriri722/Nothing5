# -*- coding: utf-8 -*-
"""
설정 대화상자 모듈

사용자 설정을 변경할 수 있는 대화상자를 제공합니다.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging
from typing import Dict, Any, Optional

import json
import config.config as cfg
from modules.credential_manager import CredentialManager

logger = logging.getLogger(__name__)

class SettingsDialog(tk.Toplevel):
    """
    설정 대화상자 클래스
    """

    def __init__(self, parent: tk.Tk):
        """
        SettingsDialog 초기화

        Args:
            parent (tk.Tk): 부모 윈도우
        """
        super().__init__(parent)
        self.title("설정")
        self.geometry("600x500")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.cred_manager = CredentialManager()

        # 현재 설정 값 로드
        self.current_source = tk.StringVar(value=cfg.CREDENTIAL_SOURCE)
        self.manual_key = tk.StringVar(value=cfg.MANUAL_API_KEY)
        self.detected_creds = {}

        self._create_ui()
        self._refresh_credentials()

        # 화면 중앙 배치
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')

    def _create_ui(self):
        """UI 구성"""
        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 탭 1: LLM / 자격 증명
        cred_frame = ttk.Frame(notebook, padding="10")
        notebook.add(cred_frame, text="LLM 자격 증명")
        self._create_credential_tab(cred_frame)

        # 탭 2: 일반 설정 (플레이스홀더)
        general_frame = ttk.Frame(notebook, padding="10")
        notebook.add(general_frame, text="일반")
        ttk.Label(general_frame, text="추가 설정 예정").pack(pady=20)

        # 하단 버튼
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(btn_frame, text="저장", command=self._save_settings).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="취소", command=self.destroy).pack(side=tk.RIGHT, padx=5)

    def _create_credential_tab(self, parent):
        """자격 증명 탭 UI"""
        # 설명
        ttk.Label(parent, text="LLM 사용을 위한 API Key 소스를 선택하세요.", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(0, 10))

        # 소스 선택 프레임
        source_frame = ttk.LabelFrame(parent, text="자격 증명 소스", padding="10")
        source_frame.pack(fill=tk.X, pady=5)

        # 라디오 버튼들
        self.radio_env = ttk.Radiobutton(source_frame, text="환경 변수 (OPENAI_API_KEY)", variable=self.current_source, value="openai", command=self._on_source_change)
        self.radio_env.pack(anchor=tk.W, pady=2)

        self.radio_gemini = ttk.Radiobutton(source_frame, text="Gemini CLI (감지됨)", variable=self.current_source, value="gemini", command=self._on_source_change)
        self.radio_gemini.pack(anchor=tk.W, pady=2)

        self.radio_claude = ttk.Radiobutton(source_frame, text="Claude Code (감지됨)", variable=self.current_source, value="claude", command=self._on_source_change)
        self.radio_claude.pack(anchor=tk.W, pady=2)

        self.radio_manual = ttk.Radiobutton(source_frame, text="수동 입력", variable=self.current_source, value="manual", command=self._on_source_change)
        self.radio_manual.pack(anchor=tk.W, pady=2)

        # 수동 입력 필드
        self.manual_frame = ttk.Frame(source_frame)
        self.manual_frame.pack(fill=tk.X, pady=(5, 0))
        ttk.Label(self.manual_frame, text="API Key:").pack(side=tk.LEFT, padx=5)
        self.entry_manual = ttk.Entry(self.manual_frame, textvariable=self.manual_key, width=40, show="*")
        self.entry_manual.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # 감지 버튼
        ttk.Button(parent, text="자격 증명 다시 감지", command=self._refresh_credentials).pack(anchor=tk.E, pady=5)

        # 상태 표시
        self.status_label = ttk.Label(parent, text="", foreground="blue")
        self.status_label.pack(anchor=tk.W, pady=5)

    def _refresh_credentials(self):
        """자격 증명 감지 및 UI 업데이트"""
        self.detected_creds = self.cred_manager.get_available_credentials()

        # 상태 업데이트
        gemini = self.detected_creds.get("gemini")
        claude = self.detected_creds.get("claude")
        openai = self.detected_creds.get("openai")

        # 라디오 버튼 텍스트/상태 업데이트
        gemini_text = f"Gemini CLI ({'감지됨: ' + gemini['masked'] if gemini else '감지되지 않음'})"
        self.radio_gemini.config(text=gemini_text, state="normal" if gemini else "disabled")

        claude_text = f"Claude Code ({'감지됨: ' + claude['masked'] if claude else '감지되지 않음'})"
        self.radio_claude.config(text=claude_text, state="normal" if claude else "disabled")

        openai_text = f"환경 변수 ({'감지됨: ' + openai['masked'] if openai else '감지되지 않음'})"
        self.radio_env.config(text=openai_text, state="normal" if openai else "disabled")

        self._on_source_change()
        messagebox.showinfo("완료", "자격 증명을 다시 스캔했습니다.")

    def _on_source_change(self):
        """소스 변경 시 UI 처리"""
        source = self.current_source.get()

        # 수동 입력 활성화/비활성화
        if source == "manual":
            self.entry_manual.config(state="normal")
        else:
            self.entry_manual.config(state="disabled")

        # 선택된 키 정보 표시
        if source == "manual":
            pass # 입력 필드가 있음
        elif source in self.detected_creds:
            cred = self.detected_creds[source]
            self.status_label.config(text=f"선택됨: {cred['name']} (Key: {cred['masked']})")
        else:
            self.status_label.config(text="선택된 소스에서 키를 찾을 수 없습니다.")

    def _save_settings(self):
        """설정 저장"""
        source = self.current_source.get()
        manual_key = self.manual_key.get()

        # 유효성 검사
        if source == "manual" and not manual_key.strip():
            messagebox.showerror("오류", "수동 입력 모드에서는 API Key를 입력해야 합니다.")
            return

        if source != "manual" and source not in self.detected_creds:
             messagebox.showerror("오류", f"{source} 소스에서 유효한 자격 증명을 찾을 수 없습니다.")
             return

        # 설정 업데이트 (메모리)
        # 실제 파일 저장은 config 모듈이 지원해야 함 (현재는 상수로 정의됨)
        # 여기서는 런타임 변수만 수정하고, 필요하다면 .env 업데이트 로직을 추가해야 함.
        # 이 프로젝트의 config.py는 상수로 되어 있어 런타임 변경이 제한적일 수 있으나,
        # 모듈 변수 자체를 업데이트하여 반영 시도.

        cfg.CREDENTIAL_SOURCE = source
        cfg.MANUAL_API_KEY = manual_key

        # 실제 사용할 키 결정
        final_key = ""
        if source == "manual":
            final_key = manual_key
        elif source in self.detected_creds:
            final_key = self.detected_creds[source]["key"]

        # OPENAI_API_KEY 업데이트 (호환성 유지)
        cfg.OPENAI_API_KEY = final_key

        # 파일로 저장 (Persistence)
        try:
            # 모델 설정 자동 업데이트
            if source == "gemini" and cfg.LLM_MODEL.startswith("gpt-"):
                cfg.LLM_MODEL = "gemini-pro"
            elif source == "claude" and cfg.LLM_MODEL.startswith("gpt-"):
                cfg.LLM_MODEL = "claude-3-opus-20240229"
            elif source in ["openai", "manual"] and (
                "gemini" in cfg.LLM_MODEL or "claude" in cfg.LLM_MODEL
            ):
                cfg.LLM_MODEL = "gpt-3.5-turbo"

            settings = {
                "CREDENTIAL_SOURCE": source,
                "MANUAL_API_KEY": manual_key,
                "LLM_MODEL": cfg.LLM_MODEL
            }
            with open(cfg.USER_SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=4)
            logger.info(f"Settings saved to {cfg.USER_SETTINGS_FILE}")
            messagebox.showinfo("저장됨", "설정이 저장되었습니다.\n(모델이 공급자에 맞춰 변경되었을 수 있습니다)")
        except Exception as e:
            logger.error(f"Failed to save settings file: {e}")
            messagebox.showwarning("경고", f"설정을 파일로 저장하는데 실패했습니다: {e}\n(이번 세션에는 적용됩니다)")

        self.destroy()

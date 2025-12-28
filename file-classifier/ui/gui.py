# -*- coding: utf-8 -*-
"""
GUI 모듈

Tkinter를 사용하여 사용자 친화적인 그래픽 인터페이스를 제공합니다.
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import logging
from typing import Callable, Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class FileClassifierGUI:
    """
    파일 분류 프로그램 GUI 클래스
    
    Tkinter 기반 사용자 인터페이스를 제공합니다.
    """
    
    def __init__(self, window_width: int = 800, window_height: int = 600):
        """
        FileClassifierGUI 초기화
        
        Args:
            window_width (int): 창 너비
            window_height (int): 창 높이
        """
        self.root = tk.Tk()
        self.root.title("LLM 기반 파일 자동 분류 프로그램")
        self.root.geometry(f"{window_width}x{window_height}")
        
        # 콜백 함수
        self.on_classify: Optional[Callable] = None
        self.on_monitor: Optional[Callable] = None
        self.on_undo: Optional[Callable] = None
        self.on_redo: Optional[Callable] = None
        
        # UI 요소
        self.folder_path_var = tk.StringVar()
        self.status_var = tk.StringVar(value="준비됨")
        self.progress_var = tk.DoubleVar()
        
        self._create_ui()
    
    def _create_ui(self) -> None:
        """UI 구성"""
        # 상단 프레임
        top_frame = ttk.Frame(self.root, padding="10")
        top_frame.pack(fill=tk.X)
        
        # 폴더 선택
        ttk.Label(top_frame, text="폴더 선택:").pack(side=tk.LEFT, padx=5)
        ttk.Entry(top_frame, textvariable=self.folder_path_var, width=50).pack(
            side=tk.LEFT, padx=5, fill=tk.X, expand=True
        )
        ttk.Button(top_frame, text="찾기", command=self._select_folder).pack(
            side=tk.LEFT, padx=5
        )
        
        # 중앙 프레임
        middle_frame = ttk.Frame(self.root, padding="10")
        middle_frame.pack(fill=tk.BOTH, expand=True)
        
        # 카테고리 설정
        ttk.Label(middle_frame, text="분류 카테고리:").pack(anchor=tk.W)
        self.category_text = tk.Text(middle_frame, height=8, width=80)
        self.category_text.pack(fill=tk.BOTH, expand=True, pady=10)
        self.category_text.insert(
            tk.END,
            "문서\n이미지\n비디오\n오디오\n압축파일\n코드\n기타"
        )
        
        # 진행률
        ttk.Label(middle_frame, text="진행률:").pack(anchor=tk.W)
        progress_bar = ttk.Progressbar(
            middle_frame,
            variable=self.progress_var,
            maximum=100
        )
        progress_bar.pack(fill=tk.X, pady=5)
        
        # 상태
        ttk.Label(middle_frame, text="상태:").pack(anchor=tk.W)
        ttk.Label(middle_frame, textvariable=self.status_var).pack(
            anchor=tk.W, pady=5
        )
        
        # 하단 프레임
        bottom_frame = ttk.Frame(self.root, padding="10")
        bottom_frame.pack(fill=tk.X)
        
        # 버튼
        ttk.Button(
            bottom_frame,
            text="분류 시작",
            command=self._on_classify_clicked
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            bottom_frame,
            text="모니터링 시작",
            command=self._on_monitor_clicked
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            bottom_frame,
            text="실행 취소",
            command=self._on_undo_clicked
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            bottom_frame,
            text="다시 실행",
            command=self._on_redo_clicked
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            bottom_frame,
            text="종료",
            command=self._on_exit_clicked
        ).pack(side=tk.RIGHT, padx=5)
    
    def _select_folder(self) -> None:
        """폴더 선택 대화상자"""
        folder = filedialog.askdirectory(title="분류할 폴더 선택")
        if folder:
            self.folder_path_var.set(folder)
            logger.info(f"폴더 선택됨: {folder}")
    
    def _on_classify_clicked(self) -> None:
        """분류 시작 버튼 클릭"""
        folder = self.folder_path_var.get()
        if not folder or not Path(folder).exists():
            messagebox.showerror("오류", "유효한 폴더를 선택하세요.")
            return
        
        categories = self.category_text.get("1.0", tk.END).strip().split("\n")
        categories = [c.strip() for c in categories if c.strip()]
        
        self.update_status("분류 중...")
        logger.info(f"분류 시작: {folder}")
        
        if self.on_classify:
            self.on_classify(folder, categories)
    
    def _on_monitor_clicked(self) -> None:
        """모니터링 시작 버튼 클릭"""
        folder = self.folder_path_var.get()
        if not folder or not Path(folder).exists():
            messagebox.showerror("오류", "유효한 폴더를 선택하세요.")
            return
        
        self.update_status("모니터링 중...")
        logger.info(f"모니터링 시작: {folder}")
        
        if self.on_monitor:
            self.on_monitor(folder)
    
    def _on_undo_clicked(self) -> None:
        """실행 취소 버튼 클릭"""
        if self.on_undo:
            self.on_undo()
        self.update_status("작업 실행 취소됨")
    
    def _on_redo_clicked(self) -> None:
        """다시 실행 버튼 클릭"""
        if self.on_redo:
            self.on_redo()
        self.update_status("작업 다시 실행됨")
    
    def _on_exit_clicked(self) -> None:
        """종료 버튼 클릭"""
        if messagebox.askokcancel("종료", "프로그램을 종료하시겠습니까?"):
            self.root.quit()
    
    def update_status(self, message: str) -> None:
        """
        상태 메시지 업데이트
        
        Args:
            message (str): 상태 메시지
        """
        self.status_var.set(message)
        self.root.update()
    
    def update_progress(self, value: float) -> None:
        """
        진행률 업데이트
        
        Args:
            value (float): 진행률 (0-100)
        """
        self.progress_var.set(value)
        self.root.update()
    
    def show_message(self, title: str, message: str, message_type: str = "info") -> None:
        """
        메시지 대화상자 표시
        
        Args:
            title (str): 제목
            message (str): 메시지
            message_type (str): 메시지 유형 (info, warning, error)
        """
        if message_type == "info":
            messagebox.showinfo(title, message)
        elif message_type == "warning":
            messagebox.showwarning(title, message)
        elif message_type == "error":
            messagebox.showerror(title, message)
    
    def set_on_classify(self, callback: Callable) -> None:
        """분류 콜백 설정"""
        self.on_classify = callback
    
    def set_on_monitor(self, callback: Callable) -> None:
        """모니터링 콜백 설정"""
        self.on_monitor = callback
    
    def set_on_undo(self, callback: Callable) -> None:
        """실행 취소 콜백 설정"""
        self.on_undo = callback
    
    def set_on_redo(self, callback: Callable) -> None:
        """다시 실행 콜백 설정"""
        self.on_redo = callback
    
    def run(self) -> None:
        """GUI 실행"""
        logger.info("GUI 시작")
        self.root.mainloop()


if __name__ == "__main__":
    gui = FileClassifierGUI()
    gui.show_message("정보", "GUI가 초기화되었습니다.")
    gui.run()
# -*- coding: utf-8 -*-
"""
UI 패키지 (ui)

LLM 기반 파일 분류 프로그램의 사용자 인터페이스 모듈들입니다.
GUI 및 CLI 인터페이스를 제공합니다.
"""

try:
    from .ui import FileClassifierGUI
    __all__ = ['FileClassifierGUI']
except ImportError:
    # GUI 라이브러리가 없는 경우 빈 __all__
    __all__ = []

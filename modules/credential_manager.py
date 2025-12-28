# -*- coding: utf-8 -*-
"""
자격 증명 관리 모듈

외부 CLI 도구의 설정 파일에서 API Key를 감지하고 추출합니다.
"""

import os
import json
import logging
import platform
from pathlib import Path
from typing import Dict, Optional, List, Any

logger = logging.getLogger(__name__)

class CredentialManager:
    """
    다양한 소스(CLI 도구, 환경 변수 등)에서 자격 증명을 관리하고 추출하는 클래스
    """

    def __init__(self):
        self.home_dir = Path.home()
        self.system = platform.system()

    def detect_gemini_credentials(self) -> Optional[str]:
        """
        Gemini CLI 설정에서 API Key를 찾습니다.

        검색 경로:
        1. ~/.gemini/settings.json
        2. ~/.config/gemini/settings.json

        Returns:
            Optional[str]: 발견된 API Key 또는 None
        """
        paths = [
            self.home_dir / ".gemini" / "settings.json",
            self.home_dir / ".config" / "gemini" / "settings.json"
        ]

        for path in paths:
            if path.exists():
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        # settings.json 구조에 따라 키 위치가 다를 수 있음
                        # 일반적인 구조 가정: {"apiKey": "..."} 또는 {"authentication": {"apiKey": "..."}}
                        if "apiKey" in data:
                            logger.info(f"Gemini credentials found at {path}")
                            return data["apiKey"]
                        if "authentication" in data and "apiKey" in data["authentication"]:
                            logger.info(f"Gemini credentials found at {path}")
                            return data["authentication"]["apiKey"]
                except Exception as e:
                    logger.warning(f"Failed to read Gemini config at {path}: {e}")

        return None

    def detect_claude_credentials(self) -> Optional[str]:
        """
        Claude Code CLI 설정에서 API Key를 찾습니다.

        검색 경로:
        1. ~/.claude/config.json
        2. ~/.config/claude/config.json

        Returns:
            Optional[str]: 발견된 API Key 또는 None
        """
        paths = [
            self.home_dir / ".claude" / "config.json",
            self.home_dir / ".config" / "claude" / "config.json"
        ]

        for path in paths:
            if path.exists():
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        # 구조 가정: {"apiKey": "..."}
                        # Claude Code의 정확한 구조는 문서에 따라 다를 수 있으나,
                        # 일반적인 키 이름을 시도
                        possible_keys = ["apiKey", "api_key", "anthropic_api_key"]
                        for key in possible_keys:
                            if key in data:
                                logger.info(f"Claude credentials found at {path}")
                                return data[key]
                except Exception as e:
                    logger.warning(f"Failed to read Claude config at {path}: {e}")

        return None

    def detect_openai_credentials(self) -> Optional[str]:
        """
        환경 변수에서 OpenAI API Key를 찾습니다.

        Returns:
            Optional[str]: 발견된 API Key 또는 None
        """
        api_key = os.environ.get("OPENAI_API_KEY")
        if api_key:
            logger.info("OpenAI credentials found in environment variables")
            return api_key
        return None

    def get_available_credentials(self) -> Dict[str, Dict[str, Any]]:
        """
        사용 가능한 모든 자격 증명을 검색합니다.

        Returns:
            Dict[str, Dict[str, Any]]:
                {
                    "gemini": {"source": "Gemini CLI", "key": "...", "masked": "sk-...1234"},
                    "claude": {"source": "Claude Code", "key": "...", "masked": "sk-...5678"},
                    "openai": {"source": "Environment (OPENAI_API_KEY)", "key": "...", "masked": "sk-...9012"}
                }
        """
        credentials = {}

        # Gemini
        gemini_key = self.detect_gemini_credentials()
        if gemini_key:
            credentials["gemini"] = {
                "name": "Gemini CLI",
                "key": gemini_key,
                "masked": self._mask_key(gemini_key)
            }

        # Claude
        claude_key = self.detect_claude_credentials()
        if claude_key:
            credentials["claude"] = {
                "name": "Claude Code",
                "key": claude_key,
                "masked": self._mask_key(claude_key)
            }

        # OpenAI (Env)
        openai_key = self.detect_openai_credentials()
        if openai_key:
            credentials["openai"] = {
                "name": "Environment (OPENAI_API_KEY)",
                "key": openai_key,
                "masked": self._mask_key(openai_key)
            }

        return credentials

    def _mask_key(self, key: str) -> str:
        """API 키를 마스킹합니다 (예: sk-ab...1234)"""
        if not key or len(key) < 8:
            return "****"
        return f"{key[:4]}...{key[-4:]}"

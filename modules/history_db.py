# -*- coding: utf-8 -*-
"""
파일 처리 이력 데이터베이스 모듈

이미 처리된 파일의 결과를 저장하여 중복 API 호출을 방지합니다.
"""

import sqlite3
import hashlib
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import json
import asyncio

logger = logging.getLogger(__name__)

class ProcessingHistory:
    """
    파일 처리 이력을 관리하는 클래스 (SQLite 기반)
    """

    def __init__(self, db_path: str = "processed_files.db"):
        """
        ProcessingHistory 초기화

        Args:
            db_path (str): 데이터베이스 파일 경로
        """
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """데이터베이스 및 테이블 초기화"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS processed_files (
                        file_hash TEXT PRIMARY KEY,
                        filename TEXT,
                        file_size INTEGER,
                        folder_name TEXT,
                        category TEXT,
                        reason TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.error(f"DB 초기화 실패: {e}")

    def get_file_hash(self, file_path: str) -> str:
        """
        파일의 SHA-256 해시를 계산합니다.

        Args:
            file_path (str): 파일 경로

        Returns:
            str: 파일 해시값
        """
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                # 4K 블록 단위로 읽기
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.error(f"해시 계산 실패 ({file_path}): {e}")
            return ""

    async def get_file_hash_async(self, file_path: str) -> str:
        """
        비동기적으로 파일 해시를 계산합니다.
        """
        return await asyncio.to_thread(self.get_file_hash, file_path)

    def get_result(self, file_hash: str) -> Optional[Dict[str, Any]]:
        """
        해시값으로 저장된 결과를 조회합니다.

        Args:
            file_hash (str): 파일 해시

        Returns:
            Optional[Dict[str, Any]]: 저장된 결과 (없으면 None)
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT folder_name, category, reason FROM processed_files WHERE file_hash = ?",
                    (file_hash,)
                )
                row = cursor.fetchone()
                if row:
                    return {
                        "folder_name": row[0],
                        "category": row[1],
                        "reason": row[2],
                        "cached": True
                    }
        except Exception as e:
            logger.error(f"DB 조회 실패: {e}")
        return None

    async def get_result_async(self, file_hash: str) -> Optional[Dict[str, Any]]:
        """비동기 DB 조회"""
        return await asyncio.to_thread(self.get_result, file_hash)

    def save_result(self, file_hash: str, filename: str, file_size: int, result: Dict[str, Any]):
        """
        처리 결과를 저장합니다.

        Args:
            file_hash (str): 파일 해시
            filename (str): 파일명
            file_size (int): 파일 크기
            result (Dict[str, Any]): 분류 결과
        """
        try:
            folder_name = result.get("folder_name", "기타")
            category = result.get("category", "기타")
            reason = result.get("reason", "")

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO processed_files
                    (file_hash, filename, file_size, folder_name, category, reason)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (file_hash, filename, file_size, folder_name, category, reason)
                )
                conn.commit()
        except Exception as e:
            logger.error(f"DB 저장 실패: {e}")

    async def save_result_async(self, file_hash: str, filename: str, file_size: int, result: Dict[str, Any]):
        """비동기 DB 저장"""
        await asyncio.to_thread(self.save_result, file_hash, filename, file_size, result)

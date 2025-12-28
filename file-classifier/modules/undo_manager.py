# -*- coding: utf-8 -*-
"""
실행 취소 관리 모듈

파일 이동 작업의 히스토리를 관리하고 이전 상태로 복원하는 기능을 제공합니다.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class UndoManager:
    """
    파일 작업 실행 취소 관리 클래스
    
    파일 이동/복사 작업의 히스토리를 저장하고
    이전 상태로 복원할 수 있습니다.
    """
    
    def __init__(self, history_file: Optional[str] = None):
        """
        UndoManager 초기화
        
        Args:
            history_file (Optional[str]): 히스토리 저장 파일 경로
        """
        self.history_file = Path(history_file) if history_file else None
        self.history: List[Dict] = []
        self.current_index = -1
        
        # 기존 히스토리 파일 로드
        if self.history_file and self.history_file.exists():
            self._load_history()
    
    def add_action(self, action: Dict) -> None:
        """
        작업을 히스토리에 추가
        
        Args:
            action (Dict): 작업 정보
                - action_type: "move" 또는 "copy"
                - source: 원본 파일 경로
                - destination: 목표 파일 경로
                - timestamp: 작업 시간
        """
        # 현재 위치 이후의 히스토리 제거
        self.history = self.history[:self.current_index + 1]
        
        # 타임스탬프 추가
        action["timestamp"] = datetime.now().isoformat()
        self.history.append(action)
        self.current_index += 1
        
        logger.info(f"작업 추가됨: {action['action_type']} - {action['source']}")
        
        # 파일에 저장
        if self.history_file:
            self._save_history()
    
    def undo(self) -> Optional[Dict]:
        """
        마지막 작업 실행 취소
        
        Returns:
            Optional[Dict]: 실행 취소된 작업 정보
        """
        if self.current_index <= 0:
            logger.warning("실행 취소할 작업이 없습니다.")
            return None
        
        self.current_index -= 1
        action = self.history[self.current_index + 1]
        logger.info(f"작업 실행 취소: {action}")
        
        return action
    
    def redo(self) -> Optional[Dict]:
        """
        실행 취소된 작업 다시 실행
        
        Returns:
            Optional[Dict]: 다시 실행된 작업 정보
        """
        if self.current_index >= len(self.history) - 1:
            logger.warning("다시 실행할 작업이 없습니다.")
            return None
        
        self.current_index += 1
        action = self.history[self.current_index]
        logger.info(f"작업 다시 실행: {action}")
        
        return action
    
    def can_undo(self) -> bool:
        """
        실행 취소 가능 여부
        
        Returns:
            bool: 실행 취소 가능하면 True
        """
        return self.current_index > 0
    
    def can_redo(self) -> bool:
        """
        다시 실행 가능 여부
        
        Returns:
            bool: 다시 실행 가능하면 True
        """
        return self.current_index < len(self.history) - 1
    
    def get_history(self) -> List[Dict]:
        """
        전체 히스토리 조회
        
        Returns:
            List[Dict]: 작업 히스토리 목록
        """
        return self.history.copy()
    
    def get_current_history(self) -> List[Dict]:
        """
        현재 위치까지의 히스토리 조회
        
        Returns:
            List[Dict]: 현재 위치까지의 작업 목록
        """
        return self.history[:self.current_index + 1]
    
    def clear_history(self) -> None:
        """전체 히스토리 초기화"""
        self.history.clear()
        self.current_index = -1
        logger.info("히스토리가 초기화되었습니다.")
        
        if self.history_file:
            self._save_history()
    
    def _save_history(self) -> None:
        """히스토리를 파일에 저장"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "history": self.history,
                    "current_index": self.current_index
                }, f, ensure_ascii=False, indent=2)
            logger.debug(f"히스토리 저장됨: {self.history_file}")
        except Exception as e:
            logger.error(f"히스토리 저장 실패: {e}")
    
    def _load_history(self) -> None:
        """파일에서 히스토리 로드"""
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.history = data.get("history", [])
                self.current_index = data.get("current_index", -1)
            logger.info(f"히스토리 로드됨: {self.history_file}")
        except Exception as e:
            logger.error(f"히스토리 로드 실패: {e}")


if __name__ == "__main__":
    manager = UndoManager()
    print("실행 취소 관리자 초기화됨")
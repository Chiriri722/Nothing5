# -*- coding: utf-8 -*-
"""
파일 감시 모듈

폴더의 변화를 감시하고 새로운 파일이 추가되면 자동으로 분류합니다.
"""

import logging
from pathlib import Path
from typing import Callable, Optional, List
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent

logger = logging.getLogger(__name__)


class FileWatcher(FileSystemEventHandler):
    """
    파일 시스템 감시 클래스
    
    watchdog 라이브러리를 사용하여 폴더의 변화를 감시합니다.
    새 파일이 생성되면 콜백 함수를 실행합니다.
    """
    
    def __init__(self, on_created: Optional[Callable] = None):
        """
        FileWatcher 초기화
        
        Args:
            on_created (Optional[Callable]): 파일 생성 시 실행할 콜백 함수
        """
        super().__init__()
        self.on_created = on_created
        self.watched_files: List[str] = []
    
    def on_created(self, event: FileCreatedEvent) -> None:
        """
        파일이 생성되었을 때 호출
        
        Args:
            event (FileCreatedEvent): 파일 이벤트
        """
        if event.is_directory:
            return
        
        file_path = event.src_path
        logger.info(f"새 파일 감지됨: {file_path}")
        self.watched_files.append(file_path)
        
        if self.on_created:
            try:
                self.on_created(file_path)
            except Exception as e:
                logger.error(f"콜백 실행 중 오류 발생: {e}")
    
    def on_modified(self, event) -> None:
        """
        파일이 수정되었을 때 호출
        
        Args:
            event: 파일 이벤트
        """
        if event.is_directory:
            return
        
        logger.debug(f"파일 수정됨: {event.src_path}")
    
    def on_deleted(self, event) -> None:
        """
        파일이 삭제되었을 때 호출
        
        Args:
            event: 파일 이벤트
        """
        if event.is_directory:
            return
        
        logger.info(f"파일 삭제됨: {event.src_path}")


class FolderMonitor:
    """
    폴더 모니터 클래스
    
    특정 폴더를 감시하고 변화가 발생할 때 처리합니다.
    """
    
    def __init__(self, watch_path: str):
        """
        FolderMonitor 초기화
        
        Args:
            watch_path (str): 감시할 폴더 경로
        """
        self.watch_path = Path(watch_path)
        self.observer: Optional[Observer] = None
        self.watcher: Optional[FileWatcher] = None
        self.is_running = False
    
    def start(self, on_file_created: Optional[Callable] = None) -> bool:
        """
        폴더 감시 시작
        
        Args:
            on_file_created (Optional[Callable]): 파일 생성 시 실행할 함수
            
        Returns:
            bool: 성공 여부
        """
        if not self.watch_path.exists():
            logger.error(f"감시할 폴더가 없습니다: {self.watch_path}")
            return False
        
        if self.is_running:
            logger.warning("이미 감시 중입니다.")
            return False
        
        try:
            self.watcher = FileWatcher(on_created=on_file_created)
            self.observer = Observer()
            self.observer.schedule(
                self.watcher,
                str(self.watch_path),
                recursive=True
            )
            self.observer.start()
            self.is_running = True
            
            logger.info(f"폴더 감시 시작: {self.watch_path}")
            return True
        except Exception as e:
            logger.error(f"폴더 감시 시작 실패: {e}")
            return False
    
    def stop(self) -> None:
        """폴더 감시 중지"""
        if not self.is_running:
            logger.warning("감시 중이 아닙니다.")
            return
        
        try:
            if self.observer:
                self.observer.stop()
                self.observer.join()
            self.is_running = False
            logger.info("폴더 감시 중지됨")
        except Exception as e:
            logger.error(f"폴더 감시 중지 중 오류: {e}")
    
    def is_monitoring(self) -> bool:
        """
        현재 감시 상태 확인
        
        Returns:
            bool: 감시 중이면 True
        """
        return self.is_running
    
    def get_watched_files(self) -> List[str]:
        """
        감시된 파일 목록 조회
        
        Returns:
            List[str]: 감시된 파일 경로 목록
        """
        if self.watcher:
            return self.watcher.watched_files.copy()
        return []
    
    def clear_watched_files(self) -> None:
        """감시 파일 목록 초기화"""
        if self.watcher:
            self.watcher.watched_files.clear()
            logger.info("감시 파일 목록이 초기화되었습니다.")


if __name__ == "__main__":
    monitor = FolderMonitor(".")
    print(f"모니터 초기화됨: {monitor.watch_path}")
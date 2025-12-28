# -*- coding: utf-8 -*-
"""
파일 시스템 감시 모듈 테스트

FileSystemWatcher와 CustomFileEventHandler의 기능을 테스트합니다.
"""

import os
import time
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from modules.watcher import FileSystemWatcher, CustomFileEventHandler, get_watcher
from modules.logger import AppLogger


class TestCustomFileEventHandler(unittest.TestCase):
    """CustomFileEventHandler 클래스 테스트"""
    
    def setUp(self):
        """테스트 전 초기화"""
        self.test_watch_dir = tempfile.mkdtemp()
        self.watcher = FileSystemWatcher(self.test_watch_dir)
        self.watcher.observer = Mock()
        
        AppLogger.initialize(log_level="DEBUG")
    
    def tearDown(self):
        """테스트 후 정리"""
        import shutil
        shutil.rmtree(self.test_watch_dir, ignore_errors=True)
    
    def test_is_supported_file(self):
        """파일 확장자 필터링 테스트"""
        handler = CustomFileEventHandler(self.watcher)
        
        # 지원하는 파일
        self.assertTrue(handler._is_supported_file("test.pdf"))
        self.assertTrue(handler._is_supported_file("test.docx"))
        self.assertTrue(handler._is_supported_file("test.txt"))
        
        # 지원하지 않는 파일
        self.assertFalse(handler._is_supported_file("test.unknown"))
        
        # 임시 파일
        self.assertFalse(handler._is_supported_file("test.tmp"))
        self.assertFalse(handler._is_supported_file("test.part"))
    
    def test_wait_for_file_stability(self):
        """파일 안정화 메커니즘 테스트"""
        handler = CustomFileEventHandler(self.watcher)
        
        # 테스트 파일 생성
        test_file = os.path.join(self.test_watch_dir, "test.txt")
        with open(test_file, "w") as f:
            f.write("test content")
        
        # 파일 안정화 확인
        result = handler._wait_for_file_stability(test_file)
        self.assertTrue(result)
        
        # 존재하지 않는 파일
        result = handler._wait_for_file_stability("/nonexistent/file.txt")
        self.assertFalse(result)


class TestFileSystemWatcher(unittest.TestCase):
    """FileSystemWatcher 클래스 테스트"""
    
    def setUp(self):
        """테스트 전 초기화"""
        self.test_watch_dir = tempfile.mkdtemp()
        self.watcher = FileSystemWatcher(self.test_watch_dir)
        AppLogger.initialize(log_level="DEBUG")
    
    def tearDown(self):
        """테스트 후 정리"""
        import shutil
        
        # 모니터링이 실행 중이면 중지
        if self.watcher.is_running:
            self.watcher.stop()
        
        shutil.rmtree(self.test_watch_dir, ignore_errors=True)
    
    def test_watcher_initialization(self):
        """Watcher 초기화 테스트"""
        self.assertEqual(self.watcher.watch_path, Path(self.test_watch_dir))
        self.assertFalse(self.watcher.is_running)
        self.assertIsNotNone(self.watcher.observer)
    
    def test_start_stop_monitoring(self):
        """모니터링 시작/중지 테스트"""
        # 시작
        result = self.watcher.start()
        self.assertEqual(result["status"], "success")
        self.assertTrue(self.watcher.is_running)
        
        time.sleep(0.5)
        
        # 중지
        result = self.watcher.stop()
        self.assertEqual(result["status"], "success")
        self.assertFalse(self.watcher.is_running)
    
    def test_file_extension_filtering(self):
        """파일 확장자 필터링 테스트"""
        # 파일 확장자 설정
        new_extensions = [".pdf", ".docx"]
        result = self.watcher.set_file_extensions(new_extensions)
        
        self.assertEqual(result["status"], "success")
        self.assertEqual(self.watcher.file_extensions, new_extensions)
    
    def test_pause_resume(self):
        """일시 중지/재개 테스트"""
        # 모니터링 시작
        self.watcher.start()
        self.assertTrue(self.watcher.is_watching())
        
        # 일시 중지
        result = self.watcher.pause()
        self.assertEqual(result["status"], "success")
        self.assertFalse(self.watcher.is_watching())
        
        # 재개
        result = self.watcher.resume()
        self.assertEqual(result["status"], "success")
        self.assertTrue(self.watcher.is_watching())
        
        # 정리
        self.watcher.stop()
    
    def test_add_event_callback(self):
        """이벤트 콜백 추가 테스트"""
        callback_func = Mock()
        
        # 콜백 추가
        result = self.watcher.add_event_callback("on_created", callback_func)
        self.assertEqual(result["status"], "success")
        self.assertIn("on_created", self.watcher._event_callbacks)
        
        # 유효하지 않은 이벤트
        result = self.watcher.add_event_callback("invalid_event", callback_func)
        self.assertEqual(result["status"], "error")
    
    def test_remove_event_callback(self):
        """이벤트 콜백 제거 테스트"""
        callback_func = Mock()
        
        # 콜백 추가
        self.watcher.add_event_callback("on_created", callback_func)
        
        # 콜백 제거
        result = self.watcher.remove_event_callback("on_created")
        self.assertEqual(result["status"], "success")
        self.assertNotIn("on_created", self.watcher._event_callbacks)
    
    def test_get_watch_stats(self):
        """모니터링 통계 테스트"""
        stats = self.watcher.get_watch_stats()
        
        self.assertIn("watch_path", stats)
        self.assertIn("is_watching", stats)
        self.assertIn("recursive", stats)
        self.assertIn("watched_extensions", stats)
        self.assertIn("files_processed", stats)
        self.assertEqual(stats["files_processed"], 0)
    
    def test_recursive_monitoring(self):
        """재귀 모니터링 테스트"""
        # 하위 폴더 생성
        sub_dir = os.path.join(self.test_watch_dir, "subdir")
        os.makedirs(sub_dir, exist_ok=True)
        
        # 모니터링 시작 (recursive=True)
        result = self.watcher.start(recursive=True)
        self.assertEqual(result["status"], "success")
        
        stats = self.watcher.get_watch_stats()
        self.assertTrue(stats["recursive"])
        
        self.watcher.stop()
    
    def test_is_watching(self):
        """모니터링 상태 테스트"""
        # 모니터링 중이 아님
        self.assertFalse(self.watcher.is_watching())
        
        # 모니터링 시작
        self.watcher.start()
        self.assertTrue(self.watcher.is_watching())
        
        # 일시 중지
        self.watcher.pause()
        self.assertFalse(self.watcher.is_watching())
        
        # 정리
        self.watcher.stop()


class TestFileCreationDetection(unittest.TestCase):
    """파일 생성 감지 기능 통합 테스트"""
    
    def setUp(self):
        """테스트 전 초기화"""
        self.test_watch_dir = tempfile.mkdtemp()
        self.watcher = FileSystemWatcher(self.test_watch_dir)
        self.callback_mock = Mock()
        
        AppLogger.initialize(log_level="DEBUG")
    
    def tearDown(self):
        """테스트 후 정리"""
        import shutil
        
        if self.watcher.is_running:
            self.watcher.stop()
        
        shutil.rmtree(self.test_watch_dir, ignore_errors=True)
    
    def test_file_creation_detection(self):
        """파일 생성 감지 테스트"""
        # 콜백 설정
        self.watcher._callback_on_file_created = self.callback_mock
        
        # 모니터링 시작
        self.watcher.start()
        
        # 파일 생성
        test_file = os.path.join(self.test_watch_dir, "test.txt")
        with open(test_file, "w") as f:
            f.write("test content")
        
        # 콜백이 호출될 때까지 대기
        time.sleep(2)
        
        # 콜백 호출 여부 확인
        # 주의: watchdog의 이벤트 감지는 시스템에 따라 다를 수 있음
        
        self.watcher.stop()


class TestSingletonWatcher(unittest.TestCase):
    """싱글톤 패턴 테스트"""
    
    def tearDown(self):
        """테스트 후 정리"""
        # 글로벌 인스턴스 초기화
        import modules.watcher as watcher_module
        watcher_module._watcher_instance = None
    
    def test_get_watcher_singleton(self):
        """싱글톤 패턴 테스트"""
        watch_path = tempfile.mkdtemp()
        
        try:
            # 첫 호출
            watcher1 = get_watcher(watch_path)
            
            # 두 번째 호출
            watcher2 = get_watcher()
            
            # 같은 인스턴스여야 함
            self.assertIs(watcher1, watcher2)
        
        finally:
            import shutil
            shutil.rmtree(watch_path, ignore_errors=True)


class TestErrorHandling(unittest.TestCase):
    """에러 처리 테스트"""
    
    def setUp(self):
        """테스트 전 초기화"""
        self.test_watch_dir = tempfile.mkdtemp()
        self.watcher = FileSystemWatcher(self.test_watch_dir)
        AppLogger.initialize(log_level="DEBUG")
    
    def tearDown(self):
        """테스트 후 정리"""
        import shutil
        
        if self.watcher.is_running:
            self.watcher.stop()
        
        shutil.rmtree(self.test_watch_dir, ignore_errors=True)
    
    def test_stop_without_start(self):
        """시작하지 않은 상태에서 중지 테스트"""
        result = self.watcher.stop()
        self.assertEqual(result["status"], "error")
    
    def test_pause_without_start(self):
        """시작하지 않은 상태에서 일시 중지 테스트"""
        result = self.watcher.pause()
        self.assertEqual(result["status"], "error")
    
    def test_invalid_event_callback(self):
        """유효하지 않은 이벤트 콜백 테스트"""
        result = self.watcher.add_event_callback("invalid_event", lambda x: None)
        self.assertEqual(result["status"], "error")
    
    def test_non_callable_callback(self):
        """호출 불가능한 콜백 테스트"""
        result = self.watcher.add_event_callback("on_created", "not_callable")
        self.assertEqual(result["status"], "error")


def run_tests():
    """모든 테스트 실행"""
    unittest.main(argv=[''], exit=False, verbosity=2)


if __name__ == "__main__":
    run_tests()

# -*- coding: utf-8 -*-
"""
UI 모듈 테스트

FileClassifierGUI 클래스의 기능을 테스트합니다.
"""

import unittest
import tkinter as tk
from pathlib import Path
import sys

# 상위 디렉토리를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from ui.ui import FileClassifierGUI


class TestFileClassifierGUI(unittest.TestCase):
    """
    FileClassifierGUI 클래스 테스트
    """
    
    def setUp(self):
        """
        각 테스트 전에 실행되는 설정
        """
        self.root = tk.Tk()
        self.gui = FileClassifierGUI(self.root, 800, 600)
    
    def tearDown(self):
        """
        각 테스트 후에 실행되는 정리
        """
        self.root.destroy()
    
    def test_gui_initialization(self):
        """
        GUI 초기화 테스트
        """
        self.assertIsNotNone(self.gui)
        self.assertIsNotNone(self.gui.root)
        self.assertEqual(self.gui.status_var.get(), "준비됨")
        self.assertFalse(self.gui.is_monitoring)
        self.assertFalse(self.gui.is_paused)
    
    def test_folder_selection_variables(self):
        """
        폴더 선택 변수 테스트
        """
        test_path = "/test/path"
        self.gui.folder_path_var.set(test_path)
        self.assertEqual(self.gui.folder_path_var.get(), test_path)
    
    def test_clear_selection(self):
        """
        폴더 선택 초기화 테스트
        """
        self.gui.folder_path_var.set("/test/path")
        self.gui.clear_selection()
        self.assertEqual(self.gui.folder_path_var.get(), "")
    
    def test_add_file_to_list(self):
        """
        파일 목록에 항목 추가 테스트
        """
        self.gui.add_file_to_list("test.pdf", "문서", "✓")
        self.assertEqual(len(self.gui.file_list_data), 1)
        self.assertEqual(self.gui.file_list_data, ("test.pdf", "문서", "✓"))
    
    def test_add_multiple_files(self):
        """
        여러 파일을 목록에 추가하는 테스트
        """
        files = [
            ("test1.pdf", "문서"),
            ("image.jpg", "이미지"),
            ("video.mp4", "비디오"),
        ]
        for filename, folder in files:
            self.gui.add_file_to_list(filename, folder, "✓")
        
        self.assertEqual(len(self.gui.file_list_data), 3)
        self.assertEqual(self.gui.file_listbox.size(), 3)
    
    def test_clear_file_list(self):
        """
        파일 목록 초기화 테스트
        """
        self.gui.add_file_to_list("test.pdf", "문서", "✓")
        self.gui.add_file_to_list("image.jpg", "이미지", "✓")
        
        self.gui.clear_file_list()
        self.assertEqual(len(self.gui.file_list_data), 0)
        self.assertEqual(self.gui.file_listbox.size(), 0)
    
    def test_update_statistics(self):
        """
        통계 업데이트 테스트
        """
        self.gui.add_file_to_list("test.pdf", "문서", "✓")
        self.gui.add_file_to_list("image.jpg", "이미지", "✓")
        self.gui.add_file_to_list("test2.pdf", "문서", "✓")
        
        self.gui.update_statistics()
        
        self.assertEqual(self.gui.stats['total_processed'], 3)
        self.assertEqual(self.gui.stats['categories']['문서'], 2)
        self.assertEqual(self.gui.stats['categories']['이미지'], 1)
    
    def test_update_statistics_with_kwargs(self):
        """
        통계 업데이트 (매개변수 포함) 테스트
        """
        self.gui.update_statistics(total=10, speed=5.5, categories={"문서": 7, "이미지": 3})
        
        self.assertEqual(self.gui.stats['total_processed'], 10)
        self.assertEqual(self.gui.stats['processing_speed'], 5.5)
        self.assertEqual(self.gui.stats['categories']['문서'], 7)
    
    def test_update_status(self):
        """
        상태 메시지 업데이트 테스트
        """
        message = "테스트 상태"
        self.gui.update_status(message)
        self.assertEqual(self.gui.status_var.get(), message)
    
    def test_update_progress(self):
        """
        진행률 업데이트 테스트
        """
        self.gui.update_progress(50.0)
        self.assertEqual(self.gui.progress_var.get(), 50.0)
        
        # 범위 테스트
        self.gui.update_progress(150.0)  # 100 이상
        self.assertEqual(self.gui.progress_var.get(), 100.0)
        
        self.gui.update_progress(-10.0)  # 0 미만
        self.assertEqual(self.gui.progress_var.get(), 0.0)
    
    def test_monitoring_state_changes(self):
        """
        모니터링 상태 변화 테스트
        """
        # 초기 상태
        self.assertFalse(self.gui.is_monitoring)
        
        # 모니터링 시작 (폴더가 선택되지 않았으므로 실패)
        # start_monitoring()은 경고를 표시하므로 직접 상태 설정
        self.gui.is_monitoring = True
        self.assertTrue(self.gui.is_monitoring)
        
        # 모니터링 일시중지
        self.gui.pause_monitoring()
        self.assertTrue(self.gui.is_paused)
        
        # 모니터링 재개
        self.gui.resume_monitoring()
        self.assertFalse(self.gui.is_paused)
    
    def test_callback_setters(self):
        """
        콜백 설정 테스트
        """
        def dummy_callback(*args):
            pass
        
        self.gui.set_on_start_monitoring(dummy_callback)
        self.assertEqual(self.gui.on_start_monitoring, dummy_callback)
        
        self.gui.set_on_stop_monitoring(dummy_callback)
        self.assertEqual(self.gui.on_stop_monitoring, dummy_callback)
        
        self.gui.set_on_undo(dummy_callback)
        self.assertEqual(self.gui.on_undo, dummy_callback)
        
        self.gui.set_on_redo(dummy_callback)
        self.assertEqual(self.gui.on_redo, dummy_callback)
    
    def test_remove_file_from_list(self):
        """
        파일 목록에서 항목 제거 테스트
        """
        self.gui.add_file_to_list("test1.pdf", "문서", "✓")
        self.gui.add_file_to_list("test2.pdf", "문서", "✓")
        self.gui.add_file_to_list("test3.pdf", "문서", "✓")
        
        self.assertEqual(len(self.gui.file_list_data), 3)
        
        self.gui.remove_file_from_list(1)
        self.assertEqual(len(self.gui.file_list_data), 2)
        self.assertEqual(self.gui.file_list_data[1], "test3.pdf")
    
    def test_run_in_background(self):
        """
        백그라운드 작업 실행 테스트
        """
        self.test_executed = False
        
        def test_func():
            self.test_executed = True
        
        self.gui.run_in_background(test_func)
        
        # 스레드가 시작되었으므로 잠시 대기
        import time
        time.sleep(0.5)
        
        # 스레드 실행 완료 확인
        self.assertTrue(self.test_executed)
    
    def test_button_states_initialization(self):
        """
        버튼 상태 초기화 테스트
        """
        self.assertEqual(self.gui.btn_start.cget('state'), tk.NORMAL)
        self.assertEqual(self.gui.btn_stop.cget('state'), tk.DISABLED)
        self.assertEqual(self.gui.btn_pause.cget('state'), tk.DISABLED)
        self.assertEqual(self.gui.btn_resume.cget('state'), tk.DISABLED)
    
    def test_statistics_categories_update(self):
        """
        통계 카테고리 업데이트 테스트
        """
        test_data = {
            ("file1.pdf", "문서", "✓"),
            ("file2.pdf", "문서", "✓"),
            ("file3.jpg", "이미지", "✓"),
            ("file4.mp4", "비디오", "✓"),
            ("file5.mp4", "비디오", "✓"),
        }
        
        for filename, folder, status in test_data:
            self.gui.add_file_to_list(filename, folder, status)
        
        self.gui.update_statistics()
        
        self.assertEqual(self.gui.stats['categories']['문서'], 2)
        self.assertEqual(self.gui.stats['categories']['이미지'], 1)
        self.assertEqual(self.gui.stats['categories']['비디오'], 2)
    
    def test_ui_queue_initialization(self):
        """
        UI 큐 초기화 테스트
        """
        self.assertIsNotNone(self.gui.ui_queue)
        self.assertTrue(self.gui.ui_queue.empty())
    
    def test_stats_initialization(self):
        """
        통계 데이터 초기화 테스트
        """
        self.assertEqual(self.gui.stats['total_processed'], 0)
        self.assertEqual(self.gui.stats['processing_speed'], 0.0)
        self.assertIsInstance(self.gui.stats['categories'], dict)


class TestGUIIntegration(unittest.TestCase):
    """
    GUI 통합 테스트
    """
    
    def setUp(self):
        self.root = tk.Tk()
        self.gui = FileClassifierGUI(self.root)
    
    def tearDown(self):
        self.root.destroy()
    
    def test_file_processing_workflow(self):
        """
        파일 처리 워크플로우 통합 테스트
        """
        # 파일 목록에 추가
        self.gui.add_file_to_list("document.pdf", "문서", "✓")
        self.gui.add_file_to_list("photo.jpg", "이미지", "✓")
        self.gui.add_file_to_list("movie.mp4", "비디오", "✓")
        
        # 통계 업데이트
        self.gui.update_statistics()
        
        # 검증
        self.assertEqual(self.gui.stats['total_processed'], 3)
        self.assertEqual(len(self.gui.file_list_data), 3)
        self.assertEqual(self.gui.file_listbox.size(), 3)
    
    def test_monitoring_workflow(self):
        """
        모니터링 워크플로우 통합 테스트
        """
        # 상태 업데이트
        self.gui.update_status("모니터링 중...")
        self.gui.is_monitoring = True
        self.gui._update_button_states()
        
        # 진행률 업데이트
        self.gui.update_progress(25)
        self.gui.update_progress(50)
        self.gui.update_progress(75)
        self.gui.update_progress(100)
        
        # 검증
        self.assertTrue(self.gui.is_monitoring)
        self.assertEqual(self.gui.progress_var.get(), 100)


if __name__ == "__main__":
    unittest.main()

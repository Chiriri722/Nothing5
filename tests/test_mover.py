# -*- coding: utf-8 -*-
"""
파일 이동 모듈 테스트

FileMover 클래스의 모든 기능을 테스트합니다.
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from datetime import datetime

# 프로젝트 루트를 sys.path에 추가
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.mover import FileMover, DuplicateHandlingStrategy
from modules.undo_manager import UndoManager


class TestFileMover(unittest.TestCase):
    """FileMover 클래스 테스트"""
    
    def setUp(self):
        """테스트 전 준비"""
        # 임시 디렉토리 생성
        self.test_dir = tempfile.mkdtemp()
        self.base_path = Path(self.test_dir) / "organize"
        self.base_path.mkdir(exist_ok=True)
        
        # 테스트 파일 생성
        self.source_dir = Path(self.test_dir) / "source"
        self.source_dir.mkdir(exist_ok=True)
        
        # FileMover 인스턴스 생성
        self.mover = FileMover(
            base_path=str(self.base_path),
            duplicate_strategy=DuplicateHandlingStrategy.RENAME_WITH_NUMBER
        )
    
    def tearDown(self):
        """테스트 후 정리"""
        # 임시 디렉토리 삭제
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def _create_test_file(self, filename: str, content: str = "test") -> Path:
        """테스트 파일 생성"""
        file_path = self.source_dir / filename
        file_path.write_text(content, encoding='utf-8')
        return file_path
    
    def test_move_single_file(self):
        """단일 파일 이동 테스트"""
        # 준비
        test_file = self._create_test_file("test.txt", "test content")
        
        # 실행
        result = self.mover.move_file(str(test_file), "Documents")
        
        # 검증
        self.assertEqual(result["status"], "success")
        self.assertIsNotNone(result["destination_path"])
        self.assertEqual(result["folder_name"], "Documents")
        self.assertFalse(result["duplicate_handled"])
        
        # 파일이 실제로 이동되었는지 확인
        self.assertFalse(test_file.exists())
        destination = Path(result["destination_path"])
        self.assertTrue(destination.exists())
        self.assertEqual(destination.read_text(encoding='utf-8'), "test content")
    
    def test_create_destination_folder(self):
        """목표 폴더 생성 테스트"""
        # 준비
        test_file = self._create_test_file("test.txt")
        
        # 실행
        result = self.mover.move_file(str(test_file), "새폴더")
        
        # 검증
        self.assertEqual(result["status"], "success")
        self.assertTrue(result["created_new_folder"])
        
        folder_path = self.base_path / "새폴더"
        self.assertTrue(folder_path.exists())
        self.assertTrue(folder_path.is_dir())
    
    def test_duplicate_file_handling_rename(self):
        """중복 파일 처리 (번호 추가) 테스트"""
        # 준비
        test_file1 = self._create_test_file("file.txt", "content1")
        test_file2 = self._create_test_file("file_copy.txt", "content2")
        
        folder_name = "Documents"
        
        # 첫 번째 파일 이동
        result1 = self.mover.move_file(str(test_file1), folder_name)
        self.assertEqual(result1["status"], "success")
        self.assertFalse(result1["duplicate_handled"])
        
        # 같은 이름의 파일을 같은 폴더로 이동
        # 먼저 같은 이름으로 파일을 생성
        dest_file = self.base_path / folder_name / "file.txt"
        self.assertTrue(dest_file.exists())
        
        # 같은 이름의 새 파일 생성
        test_file3 = self._create_test_file("file.txt", "content3")
        
        # 두 번째 파일 이동 (중복 처리)
        result2 = self.mover.move_file(str(test_file3), folder_name)
        
        # 검증
        self.assertEqual(result2["status"], "success")
        self.assertTrue(result2["duplicate_handled"])
        self.assertIn("(1)", result2["destination_path"])
    
    def test_invalid_folder_name(self):
        """잘못된 폴더명 처리 테스트"""
        # 준비
        test_file = self._create_test_file("test.txt")
        
        # 실행: 금지된 문자가 포함된 폴더명
        result = self.mover.move_file(str(test_file), "Test/Folder*Name")
        
        # 검증
        self.assertEqual(result["status"], "success")
        # 금지된 문자가 제거되거나 치환되어야 함
        self.assertNotIn("/", result["folder_name"])
        self.assertNotIn("*", result["folder_name"])
    
    def test_validate_folder_name_reserved_words(self):
        """시스템 예약어 폴더명 처리 테스트"""
        # 준비
        test_file = self._create_test_file("test.txt")
        
        # 실행: 시스템 예약어
        result = self.mover.move_file(str(test_file), "CON")
        
        # 검증
        self.assertEqual(result["status"], "success")
        self.assertNotEqual(result["folder_name"], "CON")
        self.assertIn("folder", result["folder_name"].lower())
    
    def test_validate_file_path_not_exists(self):
        """존재하지 않는 파일 처리 테스트"""
        # 준비
        non_existent_file = str(self.source_dir / "non_existent.txt")
        
        # 실행
        result = self.mover.move_file(non_existent_file, "Documents")
        
        # 검증
        self.assertEqual(result["status"], "error")
        self.assertIn("유효성 검사 실패", result["error"])
    
    def test_move_multiple_files(self):
        """여러 파일 이동 테스트"""
        # 준비
        test_file1 = self._create_test_file("file1.txt", "content1")
        test_file2 = self._create_test_file("file2.txt", "content2")
        test_file3 = self._create_test_file("file3.txt", "content3")
        
        file_list = [
            {"source": str(test_file1), "folder_name": "Documents"},
            {"source": str(test_file2), "folder_name": "Images"},
            {"source": str(test_file3), "folder_name": "Videos"}
        ]
        
        # 실행
        results = self.mover.move_multiple_files(file_list)
        
        # 검증
        self.assertEqual(len(results), 3)
        self.assertTrue(all(r["status"] == "success" for r in results))
        
        # 모든 파일이 이동되었는지 확인
        self.assertFalse(test_file1.exists())
        self.assertFalse(test_file2.exists())
        self.assertFalse(test_file3.exists())
        
        self.assertTrue((self.base_path / "Documents" / "file1.txt").exists())
        self.assertTrue((self.base_path / "Images" / "file2.txt").exists())
        self.assertTrue((self.base_path / "Videos" / "file3.txt").exists())
    
    def test_move_history_recording(self):
        """이동 히스토리 기록 테스트"""
        # 준비
        test_file1 = self._create_test_file("file1.txt")
        test_file2 = self._create_test_file("file2.txt")
        
        # 실행
        self.mover.move_file(str(test_file1), "Folder1")
        self.mover.move_file(str(test_file2), "Folder2")
        
        history = self.mover.get_move_history()
        
        # 검증
        self.assertEqual(len(history), 2)
        self.assertEqual(history["status"], "success")
        self.assertEqual(history[1]["status"], "success")
    
    def test_move_history_summary(self):
        """이동 히스토리 요약 테스트"""
        # 준비
        test_file1 = self._create_test_file("file1.txt")
        test_file2 = self._create_test_file("file2.txt")
        
        # 실행
        self.mover.move_file(str(test_file1), "Folder1")
        self.mover.move_file(str(test_file2), "Folder2")
        
        summary = self.mover.get_move_history_summary()
        
        # 검증
        self.assertEqual(summary["total_operations"], 2)
        self.assertEqual(summary["successful"], 2)
        self.assertEqual(summary["failed"], 0)
        self.assertEqual(summary["warnings"], 0)
        self.assertEqual(summary["success_rate"], "100.0%")
    
    def test_duplicate_handling_overwrite(self):
        """중복 파일 덮어쓰기 처리 테스트"""
        # 준비
        mover_overwrite = FileMover(
            base_path=str(self.base_path),
            duplicate_strategy=DuplicateHandlingStrategy.OVERWRITE
        )
        
        test_file1 = self._create_test_file("file.txt", "content1")
        test_file2 = self._create_test_file("file_copy.txt", "content2")
        
        folder_name = "Documents"
        
        # 첫 번째 파일 이동
        result1 = mover_overwrite.move_file(str(test_file1), folder_name)
        self.assertEqual(result1["status"], "success")
        
        # 같은 이름의 새 파일 생성
        test_file3 = self._create_test_file("file.txt", "new content")
        
        # 두 번째 파일 이동 (덮어쓰기)
        result2 = mover_overwrite.move_file(str(test_file3), folder_name)
        
        # 검증
        self.assertEqual(result2["status"], "success")
        dest_file = Path(result2["destination_path"])
        self.assertEqual(dest_file.read_text(encoding='utf-8'), "new content")
    
    def test_duplicate_handling_timestamp(self):
        """중복 파일 처리 (타임스탬프) 테스트"""
        # 준비
        mover_timestamp = FileMover(
            base_path=str(self.base_path),
            duplicate_strategy=DuplicateHandlingStrategy.RENAME_WITH_TIMESTAMP
        )
        
        test_file1 = self._create_test_file("file.txt", "content1")
        test_file2 = self._create_test_file("file_copy.txt", "content2")
        
        folder_name = "Documents"
        
        # 첫 번째 파일 이동
        result1 = mover_timestamp.move_file(str(test_file1), folder_name)
        self.assertEqual(result1["status"], "success")
        
        # 같은 이름의 새 파일 생성
        test_file3 = self._create_test_file("file.txt", "content3")
        
        # 두 번째 파일 이동 (타임스탬프 추가)
        result2 = mover_timestamp.move_file(str(test_file3), folder_name)
        
        # 검증
        self.assertEqual(result2["status"], "success")
        self.assertTrue(result2["duplicate_handled"])
        # 타임스탬프 형식 확인
        dest_path = Path(result2["destination_path"])
        self.assertRegex(dest_path.name, r"\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}")
    
    def test_folder_name_length_validation(self):
        """폴더명 길이 검증 테스트"""
        # 준비
        test_file = self._create_test_file("test.txt")
        
        # 매우 긴 폴더명
        long_folder_name = "a" * 500  # 최대 길이 초과
        
        # 실행
        result = self.mover.move_file(str(test_file), long_folder_name)
        
        # 검증
        self.assertEqual(result["status"], "success")
        self.assertLessEqual(len(result["folder_name"]), FileMover.MAX_FOLDER_NAME_LENGTH)
    
    def test_folder_name_with_dots(self):
        """점으로만 이루어진 폴더명 처리 테스트"""
        # 준비
        test_file = self._create_test_file("test.txt")
        
        # 실행
        result = self.mover.move_file(str(test_file), "...")
        
        # 검증
        self.assertEqual(result["status"], "success")
        self.assertNotEqual(result["folder_name"], "...")
    
    def test_clear_move_history(self):
        """이동 히스토리 초기화 테스트"""
        # 준비
        test_file = self._create_test_file("test.txt")
        self.mover.move_file(str(test_file), "Folder")
        
        # 히스토리 확인
        self.assertGreater(len(self.mover.get_move_history()), 0)
        
        # 실행
        self.mover.clear_move_history()
        
        # 검증
        self.assertEqual(len(self.mover.get_move_history()), 0)


class TestFileMoverWithUndoManager(unittest.TestCase):
    """UndoManager와의 통합 테스트"""
    
    def setUp(self):
        """테스트 전 준비"""
        self.test_dir = tempfile.mkdtemp()
        self.base_path = Path(self.test_dir) / "organize"
        self.base_path.mkdir(exist_ok=True)
        
        self.source_dir = Path(self.test_dir) / "source"
        self.source_dir.mkdir(exist_ok=True)
        
        self.undo_history_file = Path(self.test_dir) / "undo_history.json"
        self.undo_manager = UndoManager(str(self.undo_history_file))
        
        self.mover = FileMover(
            base_path=str(self.base_path),
            undo_manager=self.undo_manager
        )
    
    def tearDown(self):
        """테스트 후 정리"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def _create_test_file(self, filename: str, content: str = "test") -> Path:
        """테스트 파일 생성"""
        file_path = self.source_dir / filename
        file_path.write_text(content, encoding='utf-8')
        return file_path
    
    def test_undo_manager_integration(self):
        """UndoManager 통합 테스트"""
        # 준비
        test_file = self._create_test_file("test.txt", "content")
        
        # 실행
        result = self.mover.move_file(str(test_file), "Documents")
        
        # 검증
        self.assertEqual(result["status"], "success")
        self.assertIsNotNone(result["move_history_id"])
        
        # UndoManager에 기록되었는지 확인
        undo_history = self.undo_manager.get_history()
        self.assertGreater(len(undo_history), 0)
        last_action = undo_history[-1]
        self.assertEqual(last_action["operation"], "move_file")
        self.assertEqual(last_action["folder_name"], "Documents")


if __name__ == "__main__":
    unittest.main()

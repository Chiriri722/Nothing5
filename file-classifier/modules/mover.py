# -*- coding: utf-8 -*-
"""
파일 이동 관리 모듈

LLM이 추천한 폴더로 파일을 안전하게 이동시키는 기능을 제공합니다.
폴더 생성, 파일 이동, 중복 처리, 에러 관리를 포함합니다.
"""

import os
import shutil
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class DuplicateHandlingStrategy(Enum):
    """중복 파일 처리 전략"""
    RENAME_WITH_NUMBER = "rename_number"  # filename(1).txt
    RENAME_WITH_TIMESTAMP = "rename_timestamp"  # 2025-12-27_12-34-56_filename.txt
    OVERWRITE = "overwrite"  # 기존 파일 덮어쓰기
    SKIP = "skip"  # 이동 건너뛰기


class FileMover:
    """
    LLM 기반 파일 분류 시스템의 파일 이동 관리 클래스
    
    폴더 생성, 파일 이동, 중복 처리, 이동 이력 기록 등의 기능을 제공합니다.
    """
    
    # 금지된 폴더명 문자 (Windows, Linux 호환)
    FORBIDDEN_CHARS = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
    
    # 시스템 예약어 (Windows)
    SYSTEM_RESERVED_WORDS = [
        'CON', 'PRN', 'AUX', 'NUL',
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    ]
    
    # 최대 폴더명 길이
    MAX_FOLDER_NAME_LENGTH = 255
    
    def __init__(
        self,
        base_path: Optional[str] = None,
        duplicate_strategy: DuplicateHandlingStrategy = DuplicateHandlingStrategy.RENAME_WITH_NUMBER,
        undo_manager = None
    ):
        """
        FileMover 초기화
        
        Args:
            base_path: 파일 정리 대상 폴더 (기본값: 다운로드 폴더)
            duplicate_strategy: 중복 파일 처리 전략
            undo_manager: UndoManager 인스턴스 (선택사항)
        """
        if base_path is None:
            # 기본값: 사용자 다운로드 폴더
            base_path = str(Path.home() / "Downloads")
        
        self.base_path = Path(base_path)
        self.duplicate_strategy = duplicate_strategy
        self.undo_manager = undo_manager
        self.move_history: List[Dict] = []
        
        logger.info(f"FileMover 초기화됨 - base_path: {self.base_path}")
    
    def move_file(self, source_file_path: str, folder_name: str) -> Dict:
        """
        파일을 지정된 폴더로 이동합니다.
        
        Args:
            source_file_path: 원본 파일 경로
            folder_name: 대상 폴더명
        
        Returns:
            {
                "status": "success" | "error" | "warning",
                "source_path": "원본 파일 경로",
                "destination_path": "이동된 파일 경로",
                "folder_name": "생성/사용된 폴더명",
                "created_new_folder": True | False,
                "duplicate_handled": True | False,
                "error": "에러 메시지 (실패 시만)",
                "move_history_id": "undo_manager 기록 ID"
            }
        """
        result = {
            "status": "error",
            "source_path": source_file_path,
            "destination_path": None,
            "folder_name": folder_name,
            "created_new_folder": False,
            "duplicate_handled": False,
            "error": None,
            "move_history_id": None
        }
        
        try:
            # 1. 원본 파일 경로 유효성 검사
            if not self._validate_file_path(source_file_path):
                result["error"] = f"파일 경로 유효성 검사 실패: {source_file_path}"
                logger.error(result["error"])
                return result
            
            source_path = Path(source_file_path)
            
            # 2. 폴더명 유효성 검사 및 정제
            validated_folder_name = self._validate_folder_name(folder_name)
            if validated_folder_name is None:
                result["error"] = f"폴더명 유효성 검사 실패: {folder_name}"
                logger.error(result["error"])
                return result
            
            result["folder_name"] = validated_folder_name
            
            # 3. 대상 폴더 생성
            destination_folder = self._create_destination_folder(validated_folder_name)
            if destination_folder is None:
                result["error"] = f"대상 폴더 생성 실패: {validated_folder_name}"
                logger.error(result["error"])
                return result
            
            if not destination_folder.exists():
                result["created_new_folder"] = True
            
            # 4. 대상 파일 경로 결정
            destination_path = destination_folder / source_path.name
            
            # 5. 중복 파일 처리
            if destination_path.exists():
                result["duplicate_handled"] = True
                new_path = self._handle_duplicate_file(destination_path)
                if new_path is None:
                    result["status"] = "warning"
                    result["error"] = f"중복 파일 처리 실패: {destination_path}"
                    logger.warning(result["error"])
                    return result
                destination_path = new_path
            
            # 6. 파일 이동
            logger.info(f"파일 이동 시작: {source_path} -> {destination_path}")
            shutil.move(str(source_path), str(destination_path))
            
            result["status"] = "success"
            result["destination_path"] = str(destination_path)
            logger.info(f"파일 이동 완료: {destination_path}")
            
            # 7. undo_manager에 기록
            if self.undo_manager:
                undo_data = {
                    "operation": "move_file",
                    "source_path": str(source_path),
                    "destination_path": str(destination_path),
                    "timestamp": datetime.now().isoformat(),
                    "file_name": source_path.name,
                    "folder_name": validated_folder_name
                }
                self.undo_manager.add_action(undo_data)
                result["move_history_id"] = len(self.undo_manager.get_history()) - 1
            
            # 8. 로컬 히스토리에 기록
            self._record_move_history(result)
            
            return result
        
        except FileNotFoundError as e:
            result["error"] = f"파일 찾기 실패: {e}"
            logger.error(result["error"], exc_info=True)
            return result
        
        except PermissionError as e:
            result["error"] = f"권한 오류: {e}"
            logger.error(result["error"], exc_info=True)
            return result
        
        except OSError as e:
            if "space" in str(e).lower():
                result["error"] = f"디스크 용량 부족: {e}"
            else:
                result["error"] = f"OS 오류: {e}"
            logger.error(result["error"], exc_info=True)
            return result
        
        except shutil.Error as e:
            result["error"] = f"파일 이동 오류: {e}"
            logger.error(result["error"], exc_info=True)
            return result
        
        except Exception as e:
            result["error"] = f"예상치 못한 오류: {e}"
            logger.error(result["error"], exc_info=True)
            return result
    
    def move_multiple_files(self, file_list: List[Dict]) -> List[Dict]:
        """
        여러 파일을 동시에 이동합니다.
        
        Args:
            file_list: 파일 정보 리스트
                [
                    {"source": "path1", "folder_name": "folder1"},
                    {"source": "path2", "folder_name": "folder2"},
                    ...
                ]
        
        Returns:
            각 파일의 이동 결과 리스트
        """
        results = []
        logger.info(f"여러 파일 이동 시작: {len(file_list)}개")
        
        for file_info in file_list:
            source = file_info.get("source")
            folder_name = file_info.get("folder_name")
            
            if not source or not folder_name:
                logger.warning(f"불완전한 파일 정보: {file_info}")
                results.append({
                    "status": "error",
                    "source_path": source,
                    "folder_name": folder_name,
                    "error": "파일 경로 또는 폴더명이 없습니다."
                })
                continue
            
            result = self.move_file(source, folder_name)
            results.append(result)
        
        logger.info(f"여러 파일 이동 완료: 성공 {sum(1 for r in results if r['status'] == 'success')}/{len(results)}")
        return results
    
    def _validate_file_path(self, file_path: str) -> bool:
        """
        파일 경로 유효성 검사
        
        Args:
            file_path: 검사할 파일 경로
        
        Returns:
            유효하면 True, 아니면 False
        """
        try:
            path = Path(file_path)
            
            # 파일 존재 여부 확인
            if not path.exists():
                logger.error(f"파일이 존재하지 않습니다: {file_path}")
                return False
            
            # 파일인지 확인
            if not path.is_file():
                logger.error(f"파일이 아닙니다: {file_path}")
                return False
            
            # 읽기 권한 확인
            if not os.access(file_path, os.R_OK):
                logger.error(f"파일 읽기 권한이 없습니다: {file_path}")
                return False
            
            logger.debug(f"파일 경로 유효성 검사 통과: {file_path}")
            return True
        
        except Exception as e:
            logger.error(f"파일 경로 유효성 검사 중 오류: {e}")
            return False
    
    def _validate_folder_name(self, folder_name: str) -> Optional[str]:
        """
        폴더명 유효성 검사 및 정제
        
        Args:
            folder_name: 검사할 폴더명
        
        Returns:
            정제된 폴더명 (유효하면) 또는 None
        """
        if not folder_name:
            logger.error("폴더명이 비어있습니다.")
            return None
        
        # 공백 제거
        cleaned_name = folder_name.strip()
        
        # 길이 확인
        if len(cleaned_name) == 0:
            logger.error("폴더명이 비어있습니다.")
            return None
        
        if len(cleaned_name) > self.MAX_FOLDER_NAME_LENGTH:
            logger.warning(f"폴더명 길이 초과 ({len(cleaned_name)} > {self.MAX_FOLDER_NAME_LENGTH}): {cleaned_name}")
            cleaned_name = cleaned_name[:self.MAX_FOLDER_NAME_LENGTH]
            logger.info(f"폴더명 단축됨: {cleaned_name}")
        
        # 금지 문자 제거
        for char in self.FORBIDDEN_CHARS:
            if char in cleaned_name:
                logger.debug(f"금지 문자 제거: {char}")
                cleaned_name = cleaned_name.replace(char, "_")
        
        # 시스템 예약어 확인
        if cleaned_name.upper() in self.SYSTEM_RESERVED_WORDS:
            logger.warning(f"시스템 예약어 감지: {cleaned_name}")
            cleaned_name = f"{cleaned_name}_folder"
            logger.info(f"폴더명 변경됨: {cleaned_name}")
        
        # 점으로만 이루어진 폴더명 방지
        if all(c == '.' for c in cleaned_name):
            logger.warning(f"유효하지 않은 폴더명: {cleaned_name}")
            cleaned_name = "folder"
        
        logger.debug(f"폴더명 유효성 검사 통과: {cleaned_name}")
        return cleaned_name
    
    def _create_destination_folder(self, folder_name: str) -> Optional[Path]:
        """
        대상 폴더 생성 (이미 존재하면 재사용)
        
        Args:
            folder_name: 생성할 폴더명
        
        Returns:
            생성된 폴더 경로 또는 None
        """
        try:
            destination_path = self.base_path / folder_name
            
            logger.debug(f"대상 폴더 생성 시도: {destination_path}")
            
            # 폴더 생성 (이미 존재하면 무시)
            destination_path.mkdir(parents=True, exist_ok=True)
            
            # 쓰기 권한 확인
            if not os.access(str(destination_path), os.W_OK):
                logger.error(f"폴더 쓰기 권한이 없습니다: {destination_path}")
                return None
            
            logger.info(f"대상 폴더 준비됨: {destination_path}")
            return destination_path
        
        except PermissionError as e:
            logger.error(f"폴더 생성 권한 오류: {e}")
            return None
        
        except OSError as e:
            logger.error(f"폴더 생성 OS 오류: {e}")
            return None
        
        except Exception as e:
            logger.error(f"폴더 생성 중 예상치 못한 오류: {e}")
            return None
    
    def _handle_duplicate_file(self, destination_path: Path) -> Optional[Path]:
        """
        중복 파일 처리
        
        Args:
            destination_path: 목표 파일 경로
        
        Returns:
            처리된 파일 경로 또는 None
        """
        if self.duplicate_strategy == DuplicateHandlingStrategy.SKIP:
            logger.warning(f"중복 파일 건너뜀: {destination_path}")
            return None
        
        elif self.duplicate_strategy == DuplicateHandlingStrategy.OVERWRITE:
            logger.warning(f"중복 파일 덮어쓰기: {destination_path}")
            try:
                destination_path.unlink()
                return destination_path
            except Exception as e:
                logger.error(f"파일 삭제 실패: {e}")
                return None
        
        elif self.duplicate_strategy == DuplicateHandlingStrategy.RENAME_WITH_NUMBER:
            return self._rename_with_number(destination_path)
        
        elif self.duplicate_strategy == DuplicateHandlingStrategy.RENAME_WITH_TIMESTAMP:
            return self._rename_with_timestamp(destination_path)
        
        else:
            logger.error(f"알 수 없는 중복 처리 전략: {self.duplicate_strategy}")
            return None
    
    def _rename_with_number(self, original_path: Path) -> Path:
        """
        번호를 추가하여 파일명 변경
        예: filename.txt -> filename(1).txt
        
        Args:
            original_path: 원본 파일 경로
        
        Returns:
            새 파일 경로
        """
        counter = 1
        stem = original_path.stem
        suffix = original_path.suffix
        parent = original_path.parent
        
        new_path = original_path
        while new_path.exists():
            new_name = f"{stem}({counter}){suffix}"
            new_path = parent / new_name
            counter += 1
        
        logger.info(f"파일명 변경 (번호): {original_path.name} -> {new_path.name}")
        return new_path
    
    def _rename_with_timestamp(self, original_path: Path) -> Path:
        """
        타임스탬프를 추가하여 파일명 변경
        예: filename.txt -> 2025-12-27_12-34-56_filename.txt
        
        Args:
            original_path: 원본 파일 경로
        
        Returns:
            새 파일 경로
        """
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        new_name = f"{timestamp}_{original_path.name}"
        new_path = original_path.parent / new_name
        
        logger.info(f"파일명 변경 (타임스탐프): {original_path.name} -> {new_path.name}")
        return new_path
    
    def _record_move_history(self, result: Dict) -> None:
        """
        파일 이동 작업을 로컬 히스토리에 기록
        
        Args:
            result: 이동 결과 딕셔너리
        """
        history_record = {
            "timestamp": datetime.now().isoformat(),
            "source_path": result["source_path"],
            "destination_path": result["destination_path"],
            "folder_name": result["folder_name"],
            "status": result["status"],
            "created_new_folder": result["created_new_folder"],
            "duplicate_handled": result["duplicate_handled"]
        }
        self.move_history.append(history_record)
        logger.debug(f"이동 히스토리 기록됨: {history_record}")
    
    def get_move_history(self) -> List[Dict]:
        """
        파일 이동 히스토리 반환
        
        Returns:
            이동 작업 히스토리 리스트
        """
        return self.move_history.copy()
    
    def get_move_history_summary(self) -> Dict:
        """
        파일 이동 히스토리 요약 정보
        
        Returns:
            히스토리 요약 정보
        """
        total = len(self.move_history)
        successful = sum(1 for h in self.move_history if h["status"] == "success")
        failed = sum(1 for h in self.move_history if h["status"] == "error")
        warning = sum(1 for h in self.move_history if h["status"] == "warning")
        
        return {
            "total_operations": total,
            "successful": successful,
            "failed": failed,
            "warnings": warning,
            "success_rate": f"{(successful/total*100):.1f}%" if total > 0 else "0%"
        }
    
    def clear_move_history(self) -> None:
        """
        파일 이동 히스토리 초기화
        """
        self.move_history.clear()
        logger.info("파일 이동 히스토리가 초기화되었습니다.")


if __name__ == "__main__":
    # 기본 사용 예시
    mover = FileMover()
    print(f"FileMover 초기화됨")
    print(f"기본 경로: {mover.base_path}")
    print(f"중복 처리 전략: {mover.duplicate_strategy}")

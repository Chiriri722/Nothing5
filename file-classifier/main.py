# -*- coding: utf-8 -*-
"""
LLM 기반 파일 자동 분류 프로그램 메인 진입점

파일 내용을 분석하고 LLM을 사용하여 자동으로 분류합니다.
모든 모듈을 통합하고 GUI 및 CLI 모드를 지원합니다.
"""

import sys
import logging
import signal
import argparse
import time
from pathlib import Path
from typing import Optional, Callable, Dict, Any
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.config import (
    PROJECT_ROOT,
    LOGS_DIR,
    UNDO_HISTORY_FILE,
    DEFAULT_CATEGORIES,
    LOG_LEVEL,
    LOG_FILE,
    validate_config
)
from modules.logger import AppLogger
from modules.extractor import FileExtractor
from modules.classifier import FileClassifier
from modules.mover import FileMover, DuplicateHandlingStrategy
from modules.undo_manager import UndoManager
from modules.watcher import FolderMonitor

# UI import는 옵셔널 (CLI 모드에서는 불필요)
try:
    from ui.ui import FileClassifierGUI
    HAS_GUI = True
except ImportError:
    HAS_GUI = False


class FileClassifierApp:
    """
    파일 분류 애플리케이션 메인 클래스
    
    모든 모듈을 통합하여 파일 분류 기능을 제공합니다.
    GUI 모드와 CLI 모드를 지원하며, 신호 처리 및 정상 종료를 구현합니다.
    """
    
    def __init__(self, gui_mode: bool = True):
        """
        FileClassifierApp 초기화
        
        Args:
            gui_mode (bool): GUI 모드 여부 (False면 CLI 모드)
        """
        # 로거 초기화
        AppLogger.initialize(
            name="FileClassifier",
            log_level=LOG_LEVEL,
            log_file=str(LOG_FILE)
        )
        self.logger = AppLogger.get_logger()
        
        self.logger.info("="*60)
        self.logger.info("LLM 기반 파일 자동 분류 프로그램")
        self.logger.info(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"프로젝트 루트: {PROJECT_ROOT}")
        self.logger.info("="*60)
        
        # 설정 유효성 검사
        try:
            validate_config()
            self.logger.info("설정 유효성 검사 완료")
        except ValueError as e:
            self.logger.error(f"설정 오류: {e}")
            raise
        
        # 모드 설정
        self.gui_mode = gui_mode and HAS_GUI
        self.is_running = True
        self.is_paused = False
        
        # 통계 정보
        self.stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'start_time': datetime.now(),
            'categories': {}
        }
        
        # 모듈 초기화
        self.logger.info("모듈 초기화 중...")
        self.extractor = FileExtractor()
        self.classifier: Optional[FileClassifier] = None
        self.mover = FileMover(
            duplicate_strategy=DuplicateHandlingStrategy.RENAME_WITH_NUMBER
        )
        self.undo_manager = UndoManager(
            history_file=str(UNDO_HISTORY_FILE)
        )
        self.monitor: Optional[FolderMonitor] = None
        self.gui: Optional[FileClassifierGUI] = None
        
        # Classifier 초기화 (API 키 필요)
        try:
            self.classifier = FileClassifier()
            self.logger.info("FileClassifier 초기화 완료")
        except ValueError as e:
            self.logger.warning(f"FileClassifier 초기화 실패: {e}")
            self.classifier = None
        
        # GUI 초기화 (GUI 모드인 경우)
        if self.gui_mode:
            self.logger.info("GUI 모드 초기화 중...")
            self.gui = FileClassifierGUI()
            self._setup_gui_callbacks()
            self.logger.info("GUI 초기화 완료")
        else:
            self.logger.info("CLI 모드로 실행")
        
        # 신호 처리 설정
        self._setup_signal_handlers()
        
        self.logger.info("애플리케이션 초기화 완료")
    
    def _setup_signal_handlers(self) -> None:
        """신호 핸들러 설정 (Ctrl+C, SIGTERM)"""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        self.logger.info("신호 핸들러 등록 완료")
    
    def _signal_handler(self, signum: int, frame) -> None:
        """신호 핸들러"""
        signal_name = signal.Signals(signum).name
        self.logger.info(f"신호 수신: {signal_name} ({signum})")
        self.logger.info("애플리케이션 종료 중...")
        self.stop_application()
    
    def _setup_gui_callbacks(self) -> None:
        """GUI 콜백 함수 설정"""
        if not self.gui:
            return
        
        self.gui.set_on_start_monitoring(self._on_start_monitoring)
        self.gui.set_on_stop_monitoring(self._on_stop_monitoring)
        self.gui.set_on_undo(self._on_undo)
        self.gui.set_on_redo(self._on_redo)
        self.gui.set_on_export_log(self._on_export_log)
        self.logger.info("GUI 콜백 설정 완료")
    
    def _on_start_monitoring(self, folder: str) -> None:
        """파일 감시 시작"""
        if not Path(folder).exists():
            error_msg = f"폴더가 존재하지 않습니다: {folder}"
            self.logger.error(error_msg)
            if self.gui:
                self.gui.show_error_dialog("오류", error_msg)
            return
        
        try:
            self.monitor = FolderMonitor(folder)
            self.monitor.start(on_file_created=self._on_file_created)
            self.is_running = True
            self.logger.info(f"파일 감시 시작: {folder}")
            if self.gui:
                self.gui.update_status(f"모니터링 중: {Path(folder).name}")
        except Exception as e:
            error_msg = f"감시 시작 오류: {e}"
            self.logger.error(error_msg, exc_info=True)
            if self.gui:
                self.gui.show_error_dialog("오류", error_msg)
    
    def _on_stop_monitoring(self) -> None:
        """파일 감시 중지"""
        if self.monitor and self.monitor.is_monitoring():
            self.monitor.stop()
            self.logger.info("파일 감시 중지")
            if self.gui:
                self.gui.update_status("모니터링 중지됨")
        else:
            self.logger.warning("감시 중이 아닙니다.")
    
    def _on_file_created(self, file_path: str) -> None:
        """새 파일 생성 시 콜백 (파일 처리 파이프라인)"""
        if not self.is_running or self.is_paused:
            self.logger.debug(f"파일 처리 스킵: {file_path}")
            return
        
        try:
            self.logger.info(f"파일 자동 분류 시작: {file_path}")
            file_path_obj = Path(file_path)
            
            if not file_path_obj.exists():
                self.logger.warning(f"파일이 존재하지 않습니다: {file_path}")
                return
            
            # 1. 파일 내용 추출
            extracted = self.extractor.extract(file_path)
            content = extracted.get('content', '') if extracted else ''
            
            # 2. 파일 분류
            if not self.classifier:
                self.logger.warning("Classifier가 초기화되지 않았습니다.")
                return
            
            file_type = file_path_obj.suffix.lstrip('.')
            classification_result = self.classifier.classify_file(
                filename=file_path_obj.name,
                file_type=file_type,
                content=content
            )
            
            if classification_result.get('status') != 'success':
                error_msg = classification_result.get('error', '분류 실패')
                self.logger.warning(f"분류 실패: {file_path} - {error_msg}")
                self.stats['failed'] += 1
                return
            
            # 3. 파일 이동
            folder_name = classification_result.get('folder_name', '기타')
            move_result = self.mover.move_file(file_path, folder_name)
            
            if move_result.get('status') == 'success':
                self.stats['successful'] += 1
                self.stats['categories'][folder_name] = self.stats['categories'].get(folder_name, 0) + 1
                self.logger.info(f"파일 분류 완료: {file_path_obj.name} → {folder_name}")
                
                if self.gui:
                    self.gui.safe_update_ui(
                        self.gui.on_file_processed_event,
                        (file_path_obj.name, folder_name, "✓")
                    )
            else:
                error_msg = move_result.get('error', '이동 실패')
                self.logger.error(f"파일 이동 실패: {file_path} - {error_msg}")
                self.stats['failed'] += 1
            
            self.stats['total_processed'] += 1
        
        except Exception as e:
            self.logger.error(f"파일 처리 중 오류: {file_path} - {e}", exc_info=True)
            self.stats['failed'] += 1
    
    def _on_undo(self) -> None:
        """작업 실행 취소"""
        if not self.undo_manager.can_undo():
            self.logger.warning("실행 취소할 작업이 없습니다.")
            if self.gui:
                self.gui.show_info_dialog("알림", "실행 취소할 작업이 없습니다.")
            return
        
        try:
            action = self.undo_manager.undo()
            self.logger.info(f"작업 실행 취소: {action}")
            if self.gui:
                self.gui.show_info_dialog("완료", "작업이 실행 취소되었습니다.")
        except Exception as e:
            error_msg = f"실행 취소 중 오류: {e}"
            self.logger.error(error_msg, exc_info=True)
            if self.gui:
                self.gui.show_error_dialog("오류", error_msg)
    
    def _on_redo(self) -> None:
        """작업 다시 실행"""
        if not self.undo_manager.can_redo():
            self.logger.warning("다시 실행할 작업이 없습니다.")
            if self.gui:
                self.gui.show_info_dialog("알림", "다시 실행할 작업이 없습니다.")
            return
        
        try:
            action = self.undo_manager.redo()
            self.logger.info(f"작업 다시 실행: {action}")
            if self.gui:
                self.gui.show_info_dialog("완료", "작업이 다시 실행되었습니다.")
        except Exception as e:
            error_msg = f"다시 실행 중 오류: {e}"
            self.logger.error(error_msg, exc_info=True)
            if self.gui:
                self.gui.show_error_dialog("오류", error_msg)
    
    def _on_export_log(self, file_path: str) -> None:
        """작업 로그 내보내기"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("파일 분류 프로그램 로그\n")
                f.write("="*60 + "\n")
                f.write(f"생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"실행 시간: {datetime.now() - self.stats['start_time']}\n")
                f.write("\n[통계]\n")
                f.write(f"총 처리 파일: {self.stats['total_processed']}개\n")
                f.write(f"성공: {self.stats['successful']}개\n")
                f.write(f"실패: {self.stats['failed']}개\n")
                f.write(f"성공률: {(self.stats['successful']/max(1, self.stats['total_processed'])*100):.1f}%\n")
                f.write("\n[카테고리별 분류]\n")
                for cat, count in sorted(self.stats['categories'].items()):
                    f.write(f"  {cat}: {count}개\n")
            
            self.logger.info(f"로그 내보내기 완료: {file_path}")
        except Exception as e:
            error_msg = f"로그 내보내기 실패: {e}"
            self.logger.error(error_msg, exc_info=True)
    
    def run_gui(self) -> None:
        """GUI 모드 실행"""
        if not self.gui:
            self.logger.error("GUI 모드를 사용할 수 없습니다.")
            return
        
        try:
            self.logger.info("GUI 모드 시작")
            self.gui.run()
        except Exception as e:
            self.logger.error(f"GUI 오류: {e}", exc_info=True)
            raise
        finally:
            self.cleanup()
    
    def run_cli(self) -> None:
        """CLI 모드 실행 (대화형 수동 분류)"""
        self.logger.info("CLI 모드 시작")
        print("\n" + "="*60)
        print("LLM 기반 파일 자동 분류 프로그램 (CLI 모드)")
        print("="*60 + "\n")
        
        while True:
            print("\n명령어: classify (분류), monitor (감시), stats (통계), quit (종료)")
            command = input("> ").strip().lower()
            
            if command == "quit":
                break
            elif command == "classify":
                self._cli_classify_file()
            elif command == "monitor":
                self._cli_monitor_folder()
            elif command == "stats":
                self._cli_show_statistics()
            else:
                print("알 수 없는 명령어입니다.")
        
        self.cleanup()
    
    def _cli_classify_file(self) -> None:
        """CLI: 파일 분류"""
        file_path = input("분류할 파일 경로: ").strip()
        if not file_path:
            return
        
        file_path = Path(file_path)
        if not file_path.exists():
            print("오류: 파일이 존재하지 않습니다.")
            return
        
        try:
            extracted = self.extractor.extract(str(file_path))
            content = extracted.get('content', '') if extracted else ''
            
            if not self.classifier:
                print("오류: Classifier가 초기화되지 않았습니다.")
                return
            
            result = self.classifier.classify_file(
                filename=file_path.name,
                file_type=file_path.suffix.lstrip('.'),
                content=content
            )
            
            if result.get('status') == 'success':
                folder_name = result.get('folder_name')
                confidence = result.get('confidence')
                reason = result.get('reason')
                
                print(f"\n분류 결과:")
                print(f"  파일: {file_path.name}")
                print(f"  폴더: {folder_name}")
                print(f"  신뢰도: {confidence:.2f}")
                print(f"  이유: {reason}")
                
                move = input("\n파일을 이동하시겠습니까? (y/n): ").strip().lower()
                if move == 'y':
                    move_result = self.mover.move_file(str(file_path), folder_name)
                    if move_result.get('status') == 'success':
                        print(f"파일이 이동되었습니다: {move_result.get('destination_path')}")
                        self.stats['successful'] += 1
                    else:
                        print(f"오류: {move_result.get('error')}")
                        self.stats['failed'] += 1
            else:
                print(f"분류 실패: {result.get('error')}")
                self.stats['failed'] += 1
            
            self.stats['total_processed'] += 1
        except Exception as e:
            print(f"오류: {e}")
            self.logger.error(f"CLI 분류 오류: {e}", exc_info=True)
    
    def _cli_monitor_folder(self) -> None:
        """CLI: 폴더 감시"""
        folder = input("감시할 폴더 경로: ").strip()
        if not folder:
            return
        
        folder_path = Path(folder)
        if not folder_path.exists():
            print("오류: 폴더가 존재하지 않습니다.")
            return
        
        try:
            duration = int(input("감시 시간 (초): "))
            self.monitor = FolderMonitor(folder)
            self.monitor.start(on_file_created=self._on_file_created)
            
            print(f"\n감시 중... ({duration}초)")
            time.sleep(duration)
            
            self.monitor.stop()
            print("감시 완료.")
        except ValueError:
            print("오류: 숫자를 입력하세요.")
        except Exception as e:
            print(f"오류: {e}")
            self.logger.error(f"CLI 감시 오류: {e}", exc_info=True)
    
    def _cli_show_statistics(self) -> None:
        """CLI: 통계 표시"""
        print(f"\n[통계]")
        print(f"총 처리 파일: {self.stats['total_processed']}개")
        print(f"성공: {self.stats['successful']}개")
        print(f"실패: {self.stats['failed']}개")
        print(f"성공률: {(self.stats['successful']/max(1, self.stats['total_processed'])*100):.1f}%")
        
        if self.stats['categories']:
            print(f"\n[카테고리별 분류]")
            for cat, count in sorted(self.stats['categories'].items()):
                print(f"  {cat}: {count}개")
    
    def stop_application(self) -> None:
        """애플리케이션 중지"""
        self.is_running = False
        self.logger.info("애플리케이션 중지됨")
        self.cleanup()
    
    def cleanup(self) -> None:
        """정리 작업 (리소스 해제, 스레드 종료 등)"""
        try:
            self.logger.info("정리 작업 시작")
            
            if self.monitor and self.monitor.is_monitoring():
                self.monitor.stop()
                self.logger.info("파일 감시 중지됨")
            
            elapsed_time = (datetime.now() - self.stats['start_time']).total_seconds()
            self.logger.info(f"최종 통계: 처리 파일 {self.stats['total_processed']}개, "
                           f"성공 {self.stats['successful']}개, 실패 {self.stats['failed']}개, "
                           f"소요 시간 {elapsed_time:.1f}초")
            
            self.logger.info("="*60)
            self.logger.info(f"프로그램 종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self.logger.info("="*60)
        except Exception as e:
            self.logger.error(f"정리 작업 중 오류: {e}", exc_info=True)


def main():
    """
    메인 함수
    
    명령행 인자를 파싱하고 애플리케이션을 실행합니다.
    """
    parser = argparse.ArgumentParser(
        description="LLM 기반 파일 자동 분류 프로그램",
        epilog="예: python main.py --gui  (GUI 모드), python main.py --cli (CLI 모드)"
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="GUI 모드로 실행 (기본값)"
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="CLI 모드로 실행"
    )
    parser.add_argument(
        "--folder",
        type=str,
        help="모니터링할 폴더 경로"
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="로그 레벨"
    )
    
    args = parser.parse_args()
    
    gui_mode = True
    if args.cli:
        gui_mode = False
    
    try:
        app = FileClassifierApp(gui_mode=gui_mode)
        
        if not gui_mode:
            if args.folder:
                app._on_start_monitoring(args.folder)
            else:
                app.run_cli()
        else:
            app.run_gui()
    
    except KeyboardInterrupt:
        print("\n사용자에 의해 프로그램이 중단되었습니다.")
    except ValueError as e:
        print(f"설정 오류: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"오류 발생: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

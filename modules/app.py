# -*- coding: utf-8 -*-
"""
File Classifier Application Module

Contains the main application logic for the File Classifier.
"""

import logging
import signal
import asyncio
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

import config.config as cfg
from config.config import (
    PROJECT_ROOT,
    LOG_LEVEL,
    LOG_FILE,
    UNDO_HISTORY_FILE,
    validate_config
)
from modules.logger import AppLogger
from modules.extractor import FileExtractor
from modules.classifier import FileClassifier
from modules.mover import FileMover, DuplicateHandlingStrategy
from modules.undo_manager import UndoManager
from modules.watcher import FolderMonitor
from modules.worker import FileProcessingWorker
from modules.cli import CLIHandler

# UI import (Optional)
try:
    from ui.ui import FileClassifierGUI
    HAS_GUI = True
except ImportError:
    HAS_GUI = False


class FileClassifierApp:
    """
    File Classifier Application Main Class

    Integrates all modules to provide file classification functionality.
    Supports both GUI and CLI modes.
    """

    def __init__(self, gui_mode: bool = True):
        """
        Initialize FileClassifierApp

        Args:
            gui_mode (bool): Whether to run in GUI mode (False for CLI)
        """
        # Initialize Logger
        AppLogger.initialize(
            name="FileClassifier",
            log_level=LOG_LEVEL,
            log_file=str(LOG_FILE)
        )
        self.logger = AppLogger.get_logger()

        self.logger.info("="*60)
        self.logger.info("LLM-based Automatic File Classifier")
        self.logger.info(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"Project Root: {PROJECT_ROOT}")
        self.logger.info("="*60)

        # Mode setting
        self.gui_mode = gui_mode and HAS_GUI

        # Load Credentials & Validate Config
        try:
            cfg.load_credentials()  # Load keys from all sources
            validate_config()
            self.logger.info("Configuration validation successful")
        except ValueError as e:
            self.logger.warning(f"Configuration initialization needed: {e}")
            if not self.gui_mode:
                # CLI mode requires valid config immediately
                raise

        self.is_running = True
        self.is_paused = False

        # Statistics
        self.stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'start_time': datetime.now(),
            'categories': {}
        }

        # Initialize Modules
        self.logger.info("Initializing modules...")

        # Async Initialization
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.queue = asyncio.Queue()
        self.worker_task = None

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

        # Initialize Classifier
        self._init_classifier()

        # Initialize Worker
        self.worker = FileProcessingWorker(
            queue=self.queue,
            extractor=self.extractor,
            classifier=self.classifier,
            mover=self.mover,
            stats=self.stats,
            gui_update_callback=self._update_gui_callback if self.gui_mode else None
        )

        # Initialize GUI if needed
        if self.gui_mode:
            self.logger.info("Initializing GUI mode...")
            self.gui = FileClassifierGUI()
            self._setup_gui_callbacks()
            # Update worker callback now that GUI exists
            self.worker.gui_update_callback = self._update_gui_callback
            self.logger.info("GUI initialization complete")
        else:
            self.logger.info("Running in CLI mode")

        # Signal Handlers
        self._setup_signal_handlers()

        self.logger.info("Application initialization complete")

    def _init_classifier(self):
        """Initialize or Re-initialize the Classifier"""
        try:
            # Reload config to get latest values
            import importlib
            importlib.reload(cfg)

            self.classifier = FileClassifier(
                api_key=cfg.OPENAI_API_KEY,
                base_url=cfg.OPENAI_BASE_URL,
                model=cfg.LLM_MODEL
            )

            # Update worker classifier reference if worker exists
            if hasattr(self, 'worker'):
                self.worker.classifier = self.classifier

            self.logger.info("FileClassifier initialized")
        except ValueError as e:
            self.logger.warning(f"FileClassifier initialization failed: {e}")
            self.classifier = None
            if hasattr(self, 'worker'):
                self.worker.classifier = None
        except ImportError as e:
            self.logger.error(f"Missing required package: {e}")
            self.classifier = None
            if hasattr(self, 'worker'):
                self.worker.classifier = None

    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers"""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum: int, frame) -> None:
        """Signal handler callback"""
        signal_name = signal.Signals(signum).name
        self.logger.info(f"Signal received: {signal_name} ({signum})")
        self.stop_application()

    def _setup_gui_callbacks(self) -> None:
        """Setup GUI callbacks"""
        if not self.gui:
            return

        self.gui.set_on_classify(self._on_classify_manual) # Bind manual classification
        self.gui.set_on_start_monitoring(self._on_start_monitoring)
        self.gui.set_on_stop_monitoring(self._on_stop_monitoring)
        self.gui.set_on_undo(self._on_undo)
        self.gui.set_on_redo(self._on_redo)
        self.gui.set_on_export_log(self._on_export_log)
        self.gui.set_on_settings_changed(self._on_settings_changed)

    def _update_gui_callback(self, filename: str, folder_name: str, status: str):
        """Callback to update GUI from worker"""
        if self.gui:
            self.gui.safe_update_ui(
                self.gui.on_file_processed_event,
                (filename, folder_name, status)
            )

    def _on_settings_changed(self) -> None:
        """Callback for settings change"""
        self.logger.info("Settings changed detected. Re-initializing classifier...")
        self._init_classifier()
        if self.classifier:
             if self.gui:
                 self.gui.show_info_dialog("Complete", "Settings applied.")
        else:
             if self.gui:
                 self.gui.show_warning_dialog("Warning", "Settings saved but Classifier failed to initialize.")

    def _on_classify_manual(self, folder: str, categories: List[str]) -> None:
        """
        Manually trigger classification for all files in a folder.
        This scans the folder and queues files for async processing.
        """
        self.logger.info(f"Manual classification requested for: {folder}")

        if not self.classifier:
            if self.gui:
                self.gui.show_error_dialog("Error", "Classifier is not initialized. Please check settings.")
            return

        folder_path = Path(folder)
        if not folder_path.exists():
             if self.gui:
                self.gui.show_error_dialog("Error", "Selected folder does not exist.")
             return

        # Start worker if not already running
        if not self.worker_task or self.worker_task.done():
             future = asyncio.run_coroutine_threadsafe(self.worker.run(), self.loop)
             self.worker_task = future

        # Scan files
        count = 0
        try:
            # Handle recursion based on config
            if cfg.RECURSIVE_SEARCH:
                files = [f for f in folder_path.rglob('*') if f.is_file()]
            else:
                files = [f for f in folder_path.glob('*') if f.is_file()]

            for file_path in files:
                # Skip hidden files or system files if needed
                if file_path.name.startswith('.'):
                    continue

                self._on_file_created(str(file_path))
                count += 1

            if self.gui:
                self.gui.update_status(f"Queued {count} files for classification.")
            self.logger.info(f"Queued {count} files from {folder}")

        except Exception as e:
            self.logger.error(f"Error scanning folder: {e}")
            if self.gui:
                self.gui.show_error_dialog("Error", f"Failed to scan folder: {e}")

    def _on_start_monitoring(self, folder: str) -> None:
        """Start file monitoring"""
        if not self.classifier:
            self.logger.error("Classifier not ready.")
            if self.gui:
                self.gui.show_error_dialog("Error", "Settings incomplete.")
                self.gui._show_settings()
            return

        if not Path(folder).exists():
            error_msg = f"Folder does not exist: {folder}"
            self.logger.error(error_msg)
            if self.gui:
                self.gui.show_error_dialog("Error", error_msg)
            return

        try:
            self.monitor = FolderMonitor(folder)
            self.monitor.start(on_file_created=self._on_file_created)
            self.is_running = True
            self.logger.info(f"Monitoring started: {folder}")

            # Start Async Worker
            if not self.worker_task or self.worker_task.done():
                future = asyncio.run_coroutine_threadsafe(self.worker.run(), self.loop)
                self.worker_task = future

            if self.gui:
                self.gui.update_status(f"Monitoring: {Path(folder).name}")
        except Exception as e:
            error_msg = f"Monitoring start error: {e}"
            self.logger.error(error_msg, exc_info=True)
            if self.gui:
                self.gui.show_error_dialog("Error", error_msg)

    def _on_stop_monitoring(self) -> None:
        """Stop file monitoring"""
        if self.monitor and self.monitor.is_monitoring():
            self.monitor.stop()
            self.logger.info("Monitoring stopped")
            if self.gui:
                self.gui.update_status("Monitoring stopped")
        else:
            self.logger.warning("Not monitoring.")

    def _on_file_created(self, file_path: str) -> None:
        """Callback for new file creation"""
        if not self.is_running or self.is_paused:
            self.logger.debug(f"File skipped: {file_path}")
            return

        self.loop.call_soon_threadsafe(self.queue.put_nowait, file_path)
        self.logger.info(f"File queued: {file_path}")

    def _on_undo(self) -> None:
        """Undo last action"""
        if not self.undo_manager.can_undo():
            self.logger.warning("Nothing to undo.")
            if self.gui:
                self.gui.show_info_dialog("Info", "Nothing to undo.")
            return

        try:
            action = self.undo_manager.undo()
            self.logger.info(f"Undo action: {action}")
            if self.gui:
                self.gui.show_info_dialog("Complete", "Undo successful.")
        except Exception as e:
            error_msg = f"Undo error: {e}"
            self.logger.error(error_msg, exc_info=True)
            if self.gui:
                self.gui.show_error_dialog("Error", error_msg)

    def _on_redo(self) -> None:
        """Redo last action"""
        if not self.undo_manager.can_redo():
            self.logger.warning("Nothing to redo.")
            if self.gui:
                self.gui.show_info_dialog("Info", "Nothing to redo.")
            return

        try:
            action = self.undo_manager.redo()
            self.logger.info(f"Redo action: {action}")
            if self.gui:
                self.gui.show_info_dialog("Complete", "Redo successful.")
        except Exception as e:
            error_msg = f"Redo error: {e}"
            self.logger.error(error_msg, exc_info=True)
            if self.gui:
                self.gui.show_error_dialog("Error", error_msg)

    def _on_export_log(self, file_path: str) -> None:
        """Export log"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("File Classifier Log\n")
                f.write("="*60 + "\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Runtime: {datetime.now() - self.stats['start_time']}\n")
                f.write("\n[Statistics]\n")
                f.write(f"Total: {self.stats['total_processed']}\n")
                f.write(f"Success: {self.stats['successful']}\n")
                f.write(f"Failed: {self.stats['failed']}\n")
                f.write(f"Success Rate: {(self.stats['successful']/max(1, self.stats['total_processed'])*100):.1f}%\n")
                f.write("\n[Categories]\n")
                for cat, count in sorted(self.stats['categories'].items()):
                    f.write(f"  {cat}: {count}\n")

            self.logger.info(f"Log exported: {file_path}")
        except Exception as e:
            error_msg = f"Log export failed: {e}"
            self.logger.error(error_msg, exc_info=True)

    def run_gui(self) -> None:
        """Run in GUI mode"""
        if not self.gui:
            self.logger.error("GUI not available.")
            return

        # Start background asyncio loop
        t = threading.Thread(target=self.loop.run_forever, daemon=True)
        t.start()

        try:
            self.logger.info("Starting GUI...")
            self.gui.run()
        except Exception as e:
            self.logger.error(f"GUI Error: {e}", exc_info=True)
            raise
        finally:
            self.loop.call_soon_threadsafe(self.loop.stop)
            t.join(timeout=1.0)
            self.cleanup()

    def run_cli(self) -> None:
        """Run in CLI mode using CLIHandler"""
        handler = CLIHandler(self)
        handler.run()

    def stop_application(self) -> None:
        """Stop application"""
        self.is_running = False
        self.logger.info("Application stopping...")
        if hasattr(self, 'worker'):
            asyncio.run_coroutine_threadsafe(self.worker.stop(), self.loop)
        self.cleanup()

    def cleanup(self) -> None:
        """Cleanup resources"""
        try:
            self.logger.info("Cleaning up...")

            if self.monitor and self.monitor.is_monitoring():
                self.monitor.stop()
                self.logger.info("Monitoring stopped")

            elapsed_time = (datetime.now() - self.stats['start_time']).total_seconds()
            self.logger.info(f"Final Stats: Processed {self.stats['total_processed']}, "
                           f"Success {self.stats['successful']}, Failed {self.stats['failed']}, "
                           f"Time {elapsed_time:.1f}s")
        except Exception as e:
            self.logger.error(f"Cleanup error: {e}", exc_info=True)

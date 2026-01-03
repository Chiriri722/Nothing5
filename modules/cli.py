# -*- coding: utf-8 -*-
"""
CLI Handler Module

Handles Command Line Interface interactions for the File Classifier.
"""

import time
import logging
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from modules.app import FileClassifierApp

class CLIHandler:
    """
    Handles CLI operations for the File Classifier Application.
    """

    def __init__(self, app: 'FileClassifierApp'):
        """
        Initialize CLI Handler

        Args:
            app (FileClassifierApp): The main application instance
        """
        self.app = app
        self.logger = logging.getLogger("FileClassifier.CLI")

    def run(self) -> None:
        """
        Run the CLI loop.
        """
        self.logger.info("Starting CLI mode...")
        print("\n" + "="*60)
        print("LLM-based File Classifier (CLI Mode)")
        print("="*60 + "\n")

        # Start the asyncio loop in a separate thread if not already running
        # (FileClassifierApp usually handles this, but we ensure it here if run_cli is the entry point)
        t = threading.Thread(target=self.app.loop.run_forever, daemon=True)
        t.start()

        try:
            while True:
                print("\nCommands: classify, monitor, stats, quit")
                command = input("> ").strip().lower()

                if command == "quit":
                    break
                elif command == "classify":
                    self._classify_file()
                elif command == "monitor":
                    self._monitor_folder()
                elif command == "stats":
                    self._show_statistics()
                else:
                    print("Unknown command.")
        except KeyboardInterrupt:
            print("\nInterrupted.")
        finally:
            self.app.loop.call_soon_threadsafe(self.app.loop.stop)
            t.join(timeout=1.0)
            self.app.cleanup()

    def _classify_file(self) -> None:
        """CLI: Classify a file manually."""
        file_path_input = input("File path: ").strip()
        if not file_path_input:
            return

        file_path = Path(file_path_input)
        if not file_path.exists():
            print("Error: File not found.")
            return

        try:
            # Synchronous extraction for CLI feedback (or use app's async methods wrapped)
            # Since CLI is blocking, we can call blocking methods or wait for async ones.
            # However, app.extractor.extract is blocking.
            extracted = self.app.extractor.extract(str(file_path))
            content = extracted.get('content', '') if extracted else ''

            if not self.app.classifier:
                print("Error: Classifier not initialized.")
                return

            # Use blocking classify_file for immediate response in CLI
            # Note: app.classifier.classify_file is synchronous (blocking API call)
            result = self.app.classifier.classify_file(
                filename=file_path.name,
                file_type=file_path.suffix.lstrip('.'),
                content=content
            )

            if result.get('status') == 'success':
                folder_name = result.get('folder_name')
                confidence = result.get('confidence')
                reason = result.get('reason')

                print(f"\nResult:")
                print(f"  File: {file_path.name}")
                print(f"  Folder: {folder_name}")
                print(f"  Confidence: {confidence:.2f}")
                print(f"  Reason: {reason}")

                move = input("\nMove file? (y/n): ").strip().lower()
                if move == 'y':
                    move_result = self.app.mover.move_file(str(file_path), folder_name)
                    if move_result.get('status') == 'success':
                        print(f"Moved to: {move_result.get('destination_path')}")
                        self.app.stats['successful'] += 1
                    else:
                        print(f"Error: {move_result.get('error')}")
                        self.app.stats['failed'] += 1
            else:
                print(f"Classification failed: {result.get('error')}")
                self.app.stats['failed'] += 1

            self.app.stats['total_processed'] += 1

        except Exception as e:
            print(f"Error: {e}")
            self.logger.error(f"CLI error: {e}", exc_info=True)

    def _monitor_folder(self) -> None:
        """CLI: Monitor folder for a duration."""
        folder = input("Folder to monitor: ").strip()
        if not folder:
            return

        folder_path = Path(folder)
        if not folder_path.exists():
            print("Error: Folder not found.")
            return

        try:
            duration_str = input("Duration (seconds): ")
            duration = int(duration_str)

            # Use app's monitor setup logic manually or calling a private method?
            # Better to instantiate a new monitor or use app's capabilities.
            # But app._on_start_monitoring is tied to GUI updates slightly.
            # Let's use the app's monitor object directly.

            from modules.watcher import FolderMonitor
            self.app.monitor = FolderMonitor(folder)
            self.app.monitor.start(on_file_created=self.app._on_file_created)
            self.app.is_running = True

            # Start worker if not running
            if not self.app.worker_task or self.app.worker_task.done():
                import asyncio
                future = asyncio.run_coroutine_threadsafe(self.app._process_queue_worker(), self.app.loop)
                self.app.worker_task = future

            print(f"\nMonitoring for {duration} seconds...")
            time.sleep(duration)

            self.app.monitor.stop()
            print("Monitoring finished.")

        except ValueError:
            print("Error: Invalid number.")
        except Exception as e:
            print(f"Error: {e}")
            self.logger.error(f"CLI monitoring error: {e}", exc_info=True)

    def _show_statistics(self) -> None:
        """CLI: Show statistics."""
        stats = self.app.stats
        print(f"\n[Statistics]")
        print(f"Total: {stats['total_processed']}")
        print(f"Success: {stats['successful']}")
        print(f"Failed: {stats['failed']}")

        total = max(1, stats['total_processed'])
        print(f"Success Rate: {(stats['successful']/total*100):.1f}%")

        if stats['categories']:
            print(f"\n[Categories]")
            for cat, count in sorted(stats['categories'].items()):
                print(f"  {cat}: {count}")

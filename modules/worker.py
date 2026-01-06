# -*- coding: utf-8 -*-
"""
File Processing Worker Module

Handles asynchronous file processing pipeline: Extraction -> Classification -> Moving.
"""

import asyncio
import logging
from typing import Optional, Dict, Set
from pathlib import Path
from datetime import datetime

from modules.extractor import FileExtractor
from modules.classifier import FileClassifier
from modules.mover import FileMover, DuplicateHandlingStrategy
import config.config as cfg

logger = logging.getLogger(__name__)

class FileProcessingWorker:
    """
    Worker class that processes files from a queue.
    """

    def __init__(
        self,
        queue: asyncio.Queue,
        extractor: FileExtractor,
        classifier: FileClassifier,
        mover: FileMover,
        stats: Dict,
        gui_update_callback: Optional[callable] = None
    ):
        """
        Initialize the worker.

        Args:
            queue: The asyncio Queue to consume files from.
            extractor: FileExtractor instance.
            classifier: FileClassifier instance.
            mover: FileMover instance.
            stats: Shared statistics dictionary.
            gui_update_callback: Optional callback to update GUI (async or sync wrapper needed).
        """
        self.queue = queue
        self.extractor = extractor
        self.classifier = classifier
        self.mover = mover
        self.stats = stats
        self.gui_update_callback = gui_update_callback

        self.is_running = False
        self.active_tasks: Set[asyncio.Task] = set()

        # Concurrency control
        self.concurrency_limit = getattr(cfg, 'MAX_CONCURRENT_FILE_PROCESSING', 20)
        self.semaphore = asyncio.Semaphore(self.concurrency_limit)

    async def run(self):
        """
        Start the worker loop.
        """
        self.is_running = True
        logger.info("FileProcessingWorker started.")

        while self.is_running:
            try:
                # Wait for a file from the queue
                try:
                    file_path = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue

                # Create a task for processing the file
                # Acquire semaphore inside the task to limit concurrency
                task = asyncio.create_task(self._process_file_bounded(file_path))

                # Keep track of active tasks
                self.active_tasks.add(task)
                task.add_done_callback(self.active_tasks.discard)

                self.queue.task_done()

            except Exception as e:
                logger.error(f"Worker loop error: {e}", exc_info=True)
                await asyncio.sleep(1)

        logger.info("FileProcessingWorker stopped.")

    async def stop(self):
        """
        Stop the worker.
        """
        self.is_running = False
        # Wait for active tasks? Or just let them finish?
        # Usually we might want to wait for them.
        if self.active_tasks:
            logger.info(f"Waiting for {len(self.active_tasks)} active tasks to finish...")
            await asyncio.gather(*self.active_tasks, return_exceptions=True)

    async def _process_file_bounded(self, file_path: str):
        """Wrapper to process file with semaphore limit"""
        async with self.semaphore:
            await self._process_file_async(file_path)

    async def _process_file_async(self, file_path: str):
        """Single file async processing pipeline"""
        try:
            file_path_obj = Path(file_path)

            if not file_path_obj.exists():
                logger.warning(f"File does not exist: {file_path}")
                return

            # 1. Extract content (Async)
            extracted = await self.extractor.extract_async(file_path)
            content = extracted.get('content', '') if extracted else ''

            # 2. Classify (Async)
            if not self.classifier:
                logger.warning("Classifier not initialized.")
                return

            file_type = file_path_obj.suffix.lstrip('.')

            if self.classifier._is_image_file(file_type):
                classification_result = await self.classifier.classify_image_async(file_path)
            else:
                classification_result = await self.classifier.classify_file_async(
                    filename=file_path_obj.name,
                    file_type=file_type,
                    content=content,
                    file_path=file_path
                )

            if classification_result.get('status') != 'success':
                error_msg = classification_result.get('error', 'Classification failed')
                logger.warning(f"Classification failed: {file_path} - {error_msg}")
                self.stats['failed'] += 1
                return

            # 3. Move file (Async)
            folder_name = classification_result.get('folder_name', 'Others')
            move_result = await self.mover.move_file_async(file_path, folder_name)

            if move_result.get('status') == 'success':
                self.stats['successful'] += 1
                self.stats['categories'][folder_name] = self.stats['categories'].get(folder_name, 0) + 1
                logger.info(f"File processed: {file_path_obj.name} -> {folder_name}")

                if self.gui_update_callback:
                    # Callback is responsible for thread safety if it touches GUI
                    self.gui_update_callback(file_path_obj.name, folder_name, "✓")
            else:
                error_msg = move_result.get('error', 'Move failed')
                logger.error(f"Move failed: {file_path} - {error_msg}")
                self.stats['failed'] += 1

            self.stats['total_processed'] += 1

        except Exception as e:
            logger.error(f"Processing error (Async): {file_path} - {e}", exc_info=True)
            self.stats['failed'] += 1

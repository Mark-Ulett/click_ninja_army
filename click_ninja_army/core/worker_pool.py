"""
Worker Pool for Click Ninja Army

This module provides a simple and efficient worker pool for processing tasks concurrently.
It manages a pool of worker threads that process tasks from a shared queue.

Key Features:
- Thread-based concurrency
- Task queue management
- Resource utilization control
- Error handling and logging
- Graceful shutdown

Example:
    >>> def process_task(task):
    ...     # Process the task
    ...     return result
    >>> pool = WorkerPool(process_task, max_workers=5)
    >>> pool.start()
    >>> pool.add_task({'id': 1, 'data': 'test'})
    >>> pool.stop()
"""

import logging
import threading
import queue
from typing import Callable, Any, Dict, Optional
from concurrent.futures import ThreadPoolExecutor
import time

logger = logging.getLogger(__name__)

class WorkerPool:
    """
    Simple worker pool for processing tasks concurrently.
    
    This class provides a high-level interface for:
    1. Managing worker threads
    2. Processing tasks from a queue
    3. Handling task results
    4. Error handling and logging
    5. Resource management
    
    Attributes:
        process_func (Callable): Function to process tasks
        max_workers (int): Maximum number of worker threads
        task_queue (queue.Queue): Queue for pending tasks
        workers (List[threading.Thread]): List of worker threads
        running (bool): Whether the pool is running
    
    Example:
        >>> def process_task(task):
        ...     # Process the task
        ...     return result
        >>> pool = WorkerPool(process_task, max_workers=5)
        >>> pool.start()
        >>> pool.add_task({'id': 1, 'data': 'test'})
        >>> pool.stop()
    """
    
    def __init__(self, process_func: Callable[[Dict[str, Any]], Any],
                 max_workers: int = 5):
        """
        Initialize the worker pool.
        
        Args:
            process_func (Callable): Function to process tasks
            max_workers (int): Maximum number of worker threads
        
        Example:
            >>> pool = WorkerPool(process_task, max_workers=5)
        """
        logger.info(f"Initializing WorkerPool with {max_workers} workers")
        self.process_func = process_func
        self.max_workers = max_workers
        self.task_queue = queue.Queue()
        self.workers = []
        self.running = False
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        logger.debug("WorkerPool initialized successfully")

    def start(self):
        """
        Start the worker pool.
        
        This method:
        1. Creates worker threads
        2. Starts processing tasks
        3. Enables task submission
        
        Example:
            >>> pool = WorkerPool(process_task)
            >>> pool.start()
        """
        if self.running:
            logger.warning("Worker pool is already running")
            return
        
        try:
            logger.info(f"Starting worker pool with {self.max_workers} workers")
            self.running = True
            
            for i in range(self.max_workers):
                worker = threading.Thread(target=self._worker_loop, name=f"worker-{i}")
                worker.daemon = True
                worker.start()
                self.workers.append(worker)
                logger.debug(f"Started worker thread {i}")
            
            logger.info("Worker pool started successfully")
        except Exception as e:
            logger.error(f"Failed to start worker pool: {str(e)}")
            self.running = False
            raise

    def stop(self):
        """
        Stop the worker pool.
        
        This method:
        1. Stops accepting new tasks
        2. Waits for current tasks to complete
        3. Shuts down worker threads
        
        Example:
            >>> pool = WorkerPool(process_task)
            >>> pool.start()
            >>> # ... process tasks ...
            >>> pool.stop()
        """
        if not self.running:
            logger.warning("Worker pool is not running")
            return
        
        try:
            logger.info("Stopping worker pool")
            self.running = False
            self._executor.shutdown(wait=True)
            
            for worker in self.workers:
                worker.join()
            
            self.workers.clear()
            logger.info("Worker pool stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping worker pool: {str(e)}")
            raise

    def add_task(self, task: Dict[str, Any]) -> bool:
        """
        Add a task to the queue.
        
        Args:
            task (Dict[str, Any]): Task data to process
        
        Returns:
            bool: True if task was added successfully
        
        Example:
            >>> pool = WorkerPool(process_task)
            >>> pool.start()
            >>> pool.add_task({'id': 1, 'data': 'test'})
        """
        if not self.running:
            logger.error("Cannot add task: worker pool is not running")
            return False
        
        try:
            logger.debug(f"Adding task to queue: {task.get('id', 'unknown')}")
            self.task_queue.put(task)
            logger.debug(f"Successfully added task to queue: {task.get('id', 'unknown')}")
            return True
        except Exception as e:
            logger.error(f"Error adding task to queue: {str(e)}")
            return False

    def _worker_loop(self):
        """
        Main worker loop for processing tasks.
        
        This method:
        1. Gets tasks from the queue
        2. Processes tasks using the process function
        3. Handles task results and errors
        4. Continues until stopped
        
        Example:
            >>> def process_task(task):
            ...     # Process the task
            ...     return result
            >>> pool = WorkerPool(process_task)
            >>> pool.start()  # Workers start processing tasks
        """
        thread_name = threading.current_thread().name
        logger.debug(f"Worker {thread_name} started")
        tasks_processed = 0
        errors_encountered = 0
        
        while self.running:
            try:
                task = self.task_queue.get(timeout=1)
                if task is None:
                    continue
                
                task_id = task.get('id', 'unknown')
                logger.info(f"Worker {thread_name} processing task: {task_id}")
                start_time = time.time()
                
                future = self._executor.submit(self.process_func, task)
                
                try:
                    result = future.result(timeout=30)
                    processing_time = time.time() - start_time
                    tasks_processed += 1
                    logger.info(f"Worker {thread_name} completed task {task_id} in {processing_time:.2f} seconds")
                    logger.debug(f"Task {task_id} result: {result}")
                except Exception as e:
                    errors_encountered += 1
                    logger.error(f"Worker {thread_name} failed to process task {task_id}: {str(e)}")
                    logger.debug(f"Task {task_id} data: {task}")
                
                self.task_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                errors_encountered += 1
                logger.error(f"Worker {thread_name} encountered error: {str(e)}")
        
        logger.info(f"Worker {thread_name} shutting down. Processed {tasks_processed} tasks with {errors_encountered} errors") 
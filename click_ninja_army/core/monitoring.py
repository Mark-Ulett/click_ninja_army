"""
Monitoring System - Comprehensive logging and metrics tracking

This module provides a centralized system for monitoring and logging all aspects
of the Click Ninja Army system, including campaign pool generation, request generation,
impressions, clicks, and performance metrics.

Key Features:
- Structured logging by category
- Real-time metrics tracking
- Performance monitoring
- Queue monitoring
- Worker utilization tracking
- Error rate monitoring

Example:
    >>> monitor = MonitoringSystem("click_ninja.db", log_dir="logs")
    >>> monitor.log_event("campaign_pool", "info", "Campaign pool generation completed")
"""

import logging
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field
from collections import defaultdict
import threading
import json
import os
from queue import Queue
import sqlite3

logger = logging.getLogger(__name__)

@dataclass
class QueueMetrics:
    """Metrics for a queue."""
    current_size: int = 0
    max_size: int = 0
    total_processed: int = 0
    avg_wait_time: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)

@dataclass
class WorkerMetrics:
    """Metrics for worker pools."""
    active_workers: int = 0
    total_tasks: int = 0
    avg_task_time: float = 0.0
    utilization: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)

class MonitoringSystem:
    """
    Centralized monitoring and logging system.
    
    This class manages:
    1. Structured logging by category
    2. Real-time metrics tracking
    3. Performance monitoring
    4. Queue monitoring
    5. Worker utilization tracking
    6. Error rate monitoring
    """

    def __init__(self, db_path: str, log_dir: str = "logs"):
        """
        Initialize the monitoring system.
        
        Args:
            db_path: Path to the SQLite database
            log_dir: Directory for log files
        """
        self.db_path = db_path
        self.log_dir = log_dir
        self._setup_logging()
        self._setup_metrics_tables()
        
        # Initialize metrics storage
        self.queue_metrics: Dict[str, QueueMetrics] = defaultdict(QueueMetrics)
        self.worker_metrics: Dict[str, WorkerMetrics] = defaultdict(WorkerMetrics)
        self.performance_metrics: Dict[str, Dict[str, Any]] = defaultdict(dict)
        
        # Thread-safe operations
        self.lock = threading.Lock()
        
        # Start metrics collection
        self.running = True
        self.collector_thread = threading.Thread(
            target=self._collect_metrics,
            daemon=True
        )
        self.collector_thread.start()

    def _setup_logging(self):
        """Set up logging configuration."""
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
        
        # Configure root logger
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(os.path.join(self.log_dir, 'click_ninja.log')),
                logging.StreamHandler()
            ]
        )
        
        # Create category-specific loggers
        self.loggers = {
            'campaign_pool': logging.getLogger('campaign_pool'),
            'request_generation': logging.getLogger('request_generation'),
            'impression_processing': logging.getLogger('impression_processing'),
            'click_processing': logging.getLogger('click_processing'),
            'performance': logging.getLogger('performance')
        }
        
        # Add file handlers for each category
        for category, logger in self.loggers.items():
            handler = logging.FileHandler(
                os.path.join(self.log_dir, f'{category}.log')
            )
            handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            ))
            logger.addHandler(handler)

    def _setup_metrics_tables(self):
        """Set up metrics tables in the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Performance metrics table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS monitoring_metrics (
                        id INTEGER PRIMARY KEY,
                        category TEXT NOT NULL,
                        metric_name TEXT NOT NULL,
                        metric_value REAL NOT NULL,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(category, metric_name, timestamp)
                    )
                """)
                
                # Queue metrics table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS queue_metrics (
                        id INTEGER PRIMARY KEY,
                        queue_name TEXT NOT NULL,
                        current_size INTEGER NOT NULL,
                        max_size INTEGER NOT NULL,
                        total_processed INTEGER NOT NULL,
                        avg_wait_time REAL NOT NULL,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Worker metrics table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS worker_metrics (
                        id INTEGER PRIMARY KEY,
                        pool_name TEXT NOT NULL,
                        active_workers INTEGER NOT NULL,
                        total_tasks INTEGER NOT NULL,
                        avg_task_time REAL NOT NULL,
                        utilization REAL NOT NULL,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create indexes
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_monitoring_metrics_category 
                    ON monitoring_metrics(category, timestamp)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_queue_metrics_name 
                    ON queue_metrics(queue_name, timestamp)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_worker_metrics_pool 
                    ON worker_metrics(pool_name, timestamp)
                """)
                
                conn.commit()
        except Exception as e:
            logger.error(f"Error setting up metrics tables: {str(e)}")
            raise

    def log_event(self, category: str, level: str, message: str, **kwargs):
        """
        Log an event with the specified category and level.
        
        Args:
            category: Event category (campaign_pool, request_generation, etc.)
            level: Log level (info, warning, error, etc.)
            message: Log message
            **kwargs: Additional context data
        """
        if category not in self.loggers:
            logger.warning(f"Unknown category: {category}")
            return
        
        log_func = getattr(self.loggers[category], level.lower())
        context = json.dumps(kwargs) if kwargs else ""
        log_func(f"{message} {context}")

    def update_queue_metrics(self, queue_name: str, queue: Queue, wait_time: float):
        """
        Update metrics for a queue.
        
        Args:
            queue_name: Name of the queue
            queue: Queue instance
            wait_time: Time spent waiting in queue
        """
        with self.lock:
            metrics = self.queue_metrics[queue_name]
            metrics.current_size = queue.qsize()
            metrics.max_size = max(metrics.max_size, queue.qsize())
            metrics.total_processed += 1
            metrics.avg_wait_time = (
                (metrics.avg_wait_time * (metrics.total_processed - 1) + wait_time) /
                metrics.total_processed
            )
            metrics.last_updated = datetime.now()
            
            # Store in database
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO queue_metrics (
                            queue_name, current_size, max_size,
                            total_processed, avg_wait_time
                        ) VALUES (?, ?, ?, ?, ?)
                    """, (
                        queue_name, metrics.current_size, metrics.max_size,
                        metrics.total_processed, metrics.avg_wait_time
                    ))
                    conn.commit()
            except Exception as e:
                logger.error(f"Error updating queue metrics: {str(e)}")

    def update_worker_metrics(self, pool_name: str, active_workers: int,
                            task_time: float, total_tasks: int):
        """
        Update metrics for a worker pool.
        
        Args:
            pool_name: Name of the worker pool
            active_workers: Number of active workers
            task_time: Time taken for the last task
            total_tasks: Total number of tasks processed
        """
        with self.lock:
            metrics = self.worker_metrics[pool_name]
            metrics.active_workers = active_workers
            metrics.total_tasks = total_tasks
            metrics.avg_task_time = (
                (metrics.avg_task_time * (total_tasks - 1) + task_time) /
                total_tasks
            )
            metrics.utilization = active_workers / total_tasks if total_tasks > 0 else 0
            metrics.last_updated = datetime.now()
            
            # Store in database
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO worker_metrics (
                            pool_name, active_workers, total_tasks,
                            avg_task_time, utilization
                        ) VALUES (?, ?, ?, ?, ?)
                    """, (
                        pool_name, active_workers, total_tasks,
                        metrics.avg_task_time, metrics.utilization
                    ))
                    conn.commit()
            except Exception as e:
                logger.error(f"Error updating worker metrics: {str(e)}")

    def update_performance_metrics(self, category: str, metrics: Dict[str, float]):
        """
        Update performance metrics for a category.
        
        Args:
            category: Metric category
            metrics: Dictionary of metric names and values
        """
        with self.lock:
            self.performance_metrics[category].update(metrics)
            
            # Store in database
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    for name, value in metrics.items():
                        cursor.execute("""
                            INSERT INTO monitoring_metrics (
                                category, metric_name, metric_value
                            ) VALUES (?, ?, ?)
                        """, (category, name, value))
                    conn.commit()
            except Exception as e:
                logger.error(f"Error updating performance metrics: {str(e)}")

    def _collect_metrics(self):
        """Background thread for collecting metrics."""
        while self.running:
            try:
                # Collect queue metrics
                for name, metrics in self.queue_metrics.items():
                    self.update_queue_metrics(name, Queue(), 0.0)
                
                # Collect worker metrics
                for name, metrics in self.worker_metrics.items():
                    self.update_worker_metrics(
                        name,
                        metrics.active_workers,
                        metrics.avg_task_time,
                        metrics.total_tasks
                    )
                
                # Collect performance metrics
                for category, metrics in self.performance_metrics.items():
                    self.update_performance_metrics(category, metrics)
                
                time.sleep(60)  # Collect metrics every minute
            except Exception as e:
                logger.error(f"Error collecting metrics: {str(e)}")
                time.sleep(300)  # Wait longer on error

    def get_queue_metrics(self, queue_name: str) -> Dict[str, Any]:
        """Get metrics for a specific queue."""
        with self.lock:
            metrics = self.queue_metrics[queue_name]
            return {
                'current_size': metrics.current_size,
                'max_size': metrics.max_size,
                'total_processed': metrics.total_processed,
                'avg_wait_time': metrics.avg_wait_time,
                'last_updated': metrics.last_updated.isoformat()
            }

    def get_worker_metrics(self, pool_name: str) -> Dict[str, Any]:
        """Get metrics for a specific worker pool."""
        with self.lock:
            metrics = self.worker_metrics[pool_name]
            return {
                'active_workers': metrics.active_workers,
                'total_tasks': metrics.total_tasks,
                'avg_task_time': metrics.avg_task_time,
                'utilization': metrics.utilization,
                'last_updated': metrics.last_updated.isoformat()
            }

    def get_performance_metrics(self, category: str) -> Dict[str, float]:
        """Get performance metrics for a category."""
        with self.lock:
            return self.performance_metrics[category].copy()

    def stop(self):
        """Stop the metrics collection thread."""
        self.running = False
        if self.collector_thread.is_alive():
            self.collector_thread.join(timeout=60) 
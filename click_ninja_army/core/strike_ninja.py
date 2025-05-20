"""
Strike Ninja - Parallel impression and click processing

This module provides a robust system for processing impressions and clicks in parallel,
with separate worker pools, rate limiting, and comprehensive performance tracking.

Key Features:
- Separate worker pools for impressions and clicks
- Rate limiting per operation type
- Operation queuing
- Success/failure tracking
- Performance metrics per ad item

Example:
    >>> config = OperationConfig(impression_url='https://api.example.com/impression', click_url='https://api.example.com/click', api_token='your_token', impression_rate_limit=10, click_rate_limit=5, impression_burst=5, click_burst=3)
    >>> strike = StrikeNinja(config, db, metrics_manager)
    >>> strike.start()
    >>> strike.queue_impression(entry, priority=1)
"""

import logging
import time
import threading
from typing import Dict, List, Any, Optional
from queue import PriorityQueue
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
import requests
from datetime import datetime
from collections import defaultdict
from click_ninja_army.core.metrics import MetricsManager
from click_ninja_army.core.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

@dataclass
class WorkerPoolConfig:
    """Configuration for worker pools."""
    min_workers: int = 1
    max_workers: int = 10
    queue_size: int = 1000
    idle_timeout: float = 60.0  # seconds
    max_tasks_per_worker: int = 1000
    shutdown_timeout: float = 30.0  # seconds

@dataclass
class OperationConfig:
    """Configuration for impression and click operations."""
    impression_url: str
    click_url: str
    api_token: str
    impression_rate_limit: float  # impressions per second
    click_rate_limit: float      # clicks per second
    impression_burst: int        # maximum impression burst
    click_burst: int            # maximum click burst
    max_retries: int = 3
    retry_delay: float = 1.0
    timeout: int = 10
    
    # Worker pool configurations
    impression_workers: WorkerPoolConfig = field(default_factory=lambda: WorkerPoolConfig(
        min_workers=2,
        max_workers=10,
        queue_size=1000,
        idle_timeout=60.0,
        max_tasks_per_worker=1000,
        shutdown_timeout=30.0
    ))
    
    click_workers: WorkerPoolConfig = field(default_factory=lambda: WorkerPoolConfig(
        min_workers=1,
        max_workers=5,
        queue_size=500,
        idle_timeout=60.0,
        max_tasks_per_worker=1000,
        shutdown_timeout=30.0
    ))

@dataclass
class PerformanceMetrics:
    """Performance metrics tracking per ad item."""
    response_times: Dict[str, List[float]] = field(default_factory=lambda: defaultdict(list))
    success_count: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    failure_count: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    retry_count: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    lock: threading.Lock = field(default_factory=threading.Lock)

    def add_response_time(self, ad_item_id: str, response_time: float):
        """Add a response time measurement for an ad item."""
        with self.lock:
            self.response_times[ad_item_id].append(response_time)

    def record_success(self, ad_item_id: str):
        """Record a successful operation for an ad item."""
        with self.lock:
            self.success_count[ad_item_id] += 1

    def record_failure(self, ad_item_id: str):
        """Record a failed operation for an ad item."""
        with self.lock:
            self.failure_count[ad_item_id] += 1

    def record_retry(self, ad_item_id: str):
        """Record a retry for an ad item."""
        with self.lock:
            self.retry_count[ad_item_id] += 1

    def get_metrics(self, ad_item_id: str) -> Dict[str, Any]:
        """Get performance metrics for an ad item."""
        with self.lock:
            response_times = self.response_times[ad_item_id]
            total_ops = self.success_count[ad_item_id] + self.failure_count[ad_item_id]
            
            if not response_times:
                return {
                    'success_rate': 0.0,
                    'avg_response_time': 0.0,
                    'total_operations': 0,
                    'success_count': 0,
                    'failure_count': 0,
                    'retry_count': 0
                }

            return {
                'success_rate': (self.success_count[ad_item_id] / total_ops) * 100 if total_ops > 0 else 0.0,
                'avg_response_time': sum(response_times) / len(response_times),
                'total_operations': total_ops,
                'success_count': self.success_count[ad_item_id],
                'failure_count': self.failure_count[ad_item_id],
                'retry_count': self.retry_count[ad_item_id]
            }

class StrikeNinja:
    """
    Handles parallel impression and click processing.
    
    This class manages:
    1. Separate worker pools for impressions and clicks
    2. Rate limiting per operation type
    3. Operation queuing
    4. Success/failure tracking
    5. Performance metrics per ad item
    """

    def __init__(self, config: OperationConfig, db, metrics_manager: MetricsManager):
        """
        Initialize Strike Ninja.
        
        Args:
            config: Operation configuration
            db: Database instance
            metrics_manager: Metrics manager instance
        """
        self.config = config
        self.db = db
        self.metrics_manager = metrics_manager
        
        # Initialize rate limiters
        self.impression_limiter = RateLimiter(config.impression_rate_limit, config.impression_burst)
        self.click_limiter = RateLimiter(config.click_rate_limit, config.click_burst)
        
        # Initialize queues with configured sizes
        self.impression_queue = PriorityQueue(maxsize=config.impression_workers.queue_size)
        self.click_queue = PriorityQueue(maxsize=config.click_workers.queue_size)
        
        # Initialize worker pools with configured settings
        self.impression_workers = min(
            config.impression_workers.max_workers,
            config.impression_burst
        )
        self.click_workers = min(
            config.click_workers.max_workers,
            config.click_burst
        )
        
        # Create thread pools with configured settings
        self.impression_executor = ThreadPoolExecutor(
            max_workers=self.impression_workers,
            thread_name_prefix="impression_worker"
        )
        self.click_executor = ThreadPoolExecutor(
            max_workers=self.click_workers,
            thread_name_prefix="click_worker"
        )
        
        # Control flags
        self.running = False
        
        # Worker statistics
        self.impression_stats = {
            'active_workers': 0,
            'tasks_completed': 0,
            'last_activity': time.time()
        }
        self.click_stats = {
            'active_workers': 0,
            'tasks_completed': 0,
            'last_activity': time.time()
        }
        self.stats_lock = threading.Lock()

        # Add to __init__
        self.failure_counter = 0
        self.failure_threshold = 20
        self.circuit_breaker_tripped = False
        self.circuit_breaker_cooldown = 60  # seconds

    def _update_worker_stats(self, pool_type: str, task_completed: bool = False):
        """Update worker pool statistics."""
        with self.stats_lock:
            stats = self.impression_stats if pool_type == 'impression' else self.click_stats
            if task_completed:
                stats['tasks_completed'] += 1
            stats['last_activity'] = time.time()

    def _check_worker_health(self):
        """Monitor worker pool health and adjust if needed."""
        while self.running:
            try:
                current_time = time.time()
                
                # Check impression workers
                with self.stats_lock:
                    if (current_time - self.impression_stats['last_activity'] > 
                        self.config.impression_workers.idle_timeout):
                        logger.warning("Impression workers idle timeout reached")
                        self._adjust_worker_pool('impression')
                    
                    if (self.impression_stats['tasks_completed'] >= 
                        self.config.impression_workers.max_tasks_per_worker):
                        logger.info("Rotating impression workers due to max tasks reached")
                        self._rotate_worker_pool('impression')
                
                # Check click workers
                with self.stats_lock:
                    if (current_time - self.click_stats['last_activity'] > 
                        self.config.click_workers.idle_timeout):
                        logger.warning("Click workers idle timeout reached")
                        self._adjust_worker_pool('click')
                    
                    if (self.click_stats['tasks_completed'] >= 
                        self.config.click_workers.max_tasks_per_worker):
                        logger.info("Rotating click workers due to max tasks reached")
                        self._rotate_worker_pool('click')
                
                time.sleep(10)  # Check every 10 seconds
            except Exception as e:
                logger.error(f"Error in worker health check: {str(e)}")
                time.sleep(30)  # Wait longer on error

    def _adjust_worker_pool(self, pool_type: str):
        """Adjust worker pool size based on load."""
        config = (self.config.impression_workers if pool_type == 'impression' 
                 else self.config.click_workers)
        stats = self.impression_stats if pool_type == 'impression' else self.click_stats
        
        with self.stats_lock:
            if stats['active_workers'] > config.min_workers:
                # Reduce workers if idle
                logger.info(f"Reducing {pool_type} workers due to low activity")
                self._rotate_worker_pool(pool_type)
            elif stats['active_workers'] < config.max_workers:
                # Add workers if needed
                logger.info(f"Adding {pool_type} workers due to high activity")
                self._add_workers(pool_type)

    def _rotate_worker_pool(self, pool_type: str):
        """Rotate worker pool to prevent resource exhaustion."""
        executor = (self.impression_executor if pool_type == 'impression' 
                   else self.click_executor)
        config = (self.config.impression_workers if pool_type == 'impression' 
                 else self.config.click_workers)
        
        # Shutdown current executor
        executor.shutdown(wait=False)
        
        # Create new executor
        new_executor = ThreadPoolExecutor(
            max_workers=config.max_workers,
            thread_name_prefix=f"{pool_type}_worker"
        )
        
        # Update reference
        if pool_type == 'impression':
            self.impression_executor = new_executor
        else:
            self.click_executor = new_executor
        
        # Reset statistics
        with self.stats_lock:
            if pool_type == 'impression':
                self.impression_stats['tasks_completed'] = 0
            else:
                self.click_stats['tasks_completed'] = 0

    def _add_workers(self, pool_type: str):
        """Add workers to the pool."""
        executor = (self.impression_executor if pool_type == 'impression' 
                   else self.click_executor)
        worker_count = (self.impression_workers if pool_type == 'impression' 
                       else self.click_workers)
        
        for _ in range(worker_count):
            if pool_type == 'impression':
                executor.submit(self._impression_worker)
            else:
                executor.submit(self._click_worker)
        
        with self.stats_lock:
            if pool_type == 'impression':
                self.impression_stats['active_workers'] += worker_count
            else:
                self.click_stats['active_workers'] += worker_count

    def _create_impression_payload(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Create REST API impression request payload."""
        return {
            'adTag': entry.get('ad_tag', ''),
            'adItemId': entry.get('ad_item_id', ''),
            'adRequestId': entry.get('ad_request_id', ''),
            'creativeId': entry.get('creative_id', None),
            'cache': entry.get('cache', False),
            'customerId': entry.get('customer_id', ''),
            'displayedAt': entry.get('displayed_at', datetime.now().isoformat()),
            'payload': entry.get('payload', {
                'sessionId': entry.get('session_id', ''),
                'sessionExpiry': entry.get('session_expiry', '')
            })
        }

    def _create_click_payload(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Create REST API click request payload."""
        return {
            'adItemId': entry.get('ad_item_id', ''),
            'adTag': entry.get('ad_tag', ''),
            'adRequestId': entry.get('ad_request_id', ''),
            'creativeId': entry.get('creative_id', None),
            'customerId': entry.get('customer_id', ''),
            'displayedAt': entry.get('displayed_at', datetime.now().isoformat()),
            'clickedAt': entry.get('clicked_at', datetime.now().isoformat()),
            'payload': entry.get('payload', {
                'sessionId': entry.get('session_id', ''),
                'sessionExpiry': entry.get('session_expiry', '')
            })
        }

    def _trip_circuit_breaker(self):
        self.circuit_breaker_tripped = True
        logger.critical(f"StrikeNinja Circuit breaker tripped: {self.failure_counter} consecutive failures. Pausing all workers for {self.circuit_breaker_cooldown} seconds.")
        time.sleep(self.circuit_breaker_cooldown)
        logger.info("StrikeNinja circuit breaker cooldown complete. Resuming workers.")
        self.failure_counter = 0
        self.circuit_breaker_tripped = False

    def _make_impression(self, entry: Dict[str, Any], retry_count: int = 0) -> bool:
        if self.circuit_breaker_tripped:
            logger.warning("StrikeNinja circuit breaker is active. Skipping impression.")
            return False
        if not self.impression_limiter.acquire():
            time.sleep(0.1)
            return self._make_impression(entry, retry_count)
        start_time = time.time()
        try:
            payload = self._create_impression_payload(entry)
            response = requests.post(
                self.config.impression_url,
                json=payload,
                headers={'Authorization': f'Bearer {self.config.api_token}'},
                timeout=self.config.timeout
            )
            response.raise_for_status()
            response_time = time.time() - start_time
            self.metrics_manager.update_performance_metrics(
                entry['ad_item_id'],
                'impression',
                True,
                response_time,
                False
            )
            self.failure_counter = 0
            return True
        except Exception as e:
            self.failure_counter += 1
            if self.failure_counter >= self.failure_threshold:
                self._trip_circuit_breaker()
            if retry_count < self.config.max_retries:
                logger.warning(f"Impression failed (attempt {retry_count + 1}): {str(e)}")
                time.sleep(self.config.retry_delay * (retry_count + 1))
                self.metrics_manager.update_performance_metrics(
                    entry['ad_item_id'],
                    'impression',
                    False,
                    time.time() - start_time,
                    True
                )
                return self._make_impression(entry, retry_count + 1)
            else:
                logger.error(f"Impression failed after {self.config.max_retries} attempts: {str(e)}")
                self.metrics_manager.update_performance_metrics(
                    entry['ad_item_id'],
                    'impression',
                    False,
                    time.time() - start_time,
                    False
                )
                return False

    def _make_click(self, entry: Dict[str, Any], retry_count: int = 0) -> bool:
        if self.circuit_breaker_tripped:
            logger.warning("StrikeNinja circuit breaker is active. Skipping click.")
            return False
        if not self.click_limiter.acquire():
            time.sleep(0.1)
            return self._make_click(entry, retry_count)
        start_time = time.time()
        try:
            payload = self._create_click_payload(entry)
            response = requests.post(
                self.config.click_url,
                json=payload,
                headers={'Authorization': f'Bearer {self.config.api_token}'},
                timeout=self.config.timeout
            )
            response.raise_for_status()
            response_time = time.time() - start_time
            self.metrics_manager.update_performance_metrics(
                entry['ad_item_id'],
                'click',
                True,
                response_time,
                False
            )
            self.failure_counter = 0
            return True
        except Exception as e:
            self.failure_counter += 1
            if self.failure_counter >= self.failure_threshold:
                self._trip_circuit_breaker()
            if retry_count < self.config.max_retries:
                logger.warning(f"Click failed (attempt {retry_count + 1}): {str(e)}")
                time.sleep(self.config.retry_delay * (retry_count + 1))
                self.metrics_manager.update_performance_metrics(
                    entry['ad_item_id'],
                    'click',
                    False,
                    time.time() - start_time,
                    True
                )
                return self._make_click(entry, retry_count + 1)
            else:
                logger.error(f"Click failed after {self.config.max_retries} attempts: {str(e)}")
                self.metrics_manager.update_performance_metrics(
                    entry['ad_item_id'],
                    'click',
                    False,
                    time.time() - start_time,
                    False
                )
                return False

    def _impression_worker(self):
        """Worker thread for processing impressions."""
        while self.running:
            try:
                priority, timestamp, entry = self.impression_queue.get(timeout=1)
                success = self._make_impression(entry)
                if success:
                    self.db.update_request_status(entry['ad_request_id'], 'impression_sent')
                self.impression_queue.task_done()
                self._update_worker_stats('impression', task_completed=success)
            except Exception as e:
                logger.error(f"Impression worker error: {str(e)}")
                continue

    def _click_worker(self):
        """Worker thread for processing clicks."""
        while self.running:
            try:
                priority, entry = self.click_queue.get(timeout=1)
                success = self._make_click(entry)
                if success:
                    self.db.update_request_status(entry['ad_request_id'], 'click_sent')
                self.click_queue.task_done()
                self._update_worker_stats('click', task_completed=success)
            except Exception as e:
                logger.error(f"Click worker error: {str(e)}", exc_info=True)
                continue

    def start(self):
        """Start the impression and click processing."""
        self.running = True
        
        # Start worker health monitoring
        self.health_monitor = threading.Thread(
            target=self._check_worker_health,
            daemon=True
        )
        self.health_monitor.start()
        
        # Start initial worker pools
        self._add_workers('impression')
        self._add_workers('click')
        
        logger.info(f"Started {self.impression_workers} impression workers and "
                   f"{self.click_workers} click workers")

    def stop(self):
        """Stop the impression and click processing."""
        self.running = False
        
        # Shutdown executors
        self.impression_executor.shutdown(wait=True)
        self.click_executor.shutdown(wait=True)
        
        logger.info("Stopped all worker threads")

    def queue_impression(self, entry: Dict[str, Any], priority: int = 0):
        """Queue an impression operation."""
        self.impression_queue.put((priority, time.time(), entry))
        logger.info(f"Queued impression for requestId: {entry['request_id']}")

    def queue_click(self, entry: Dict[str, Any], priority: int = 0):
        """Queue a click operation."""
        self.click_queue.put((priority, entry))
        logger.info(f"Queued click for adRequestId: {entry['ad_request_id']}")

    def get_metrics(self, ad_item_id: str) -> Dict[str, Any]:
        """Get performance metrics for an ad item."""
        return self.metrics_manager.get_performance_metrics(ad_item_id) 
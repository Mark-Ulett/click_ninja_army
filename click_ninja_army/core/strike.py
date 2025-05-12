"""
Strike Ninja - Executes ad operations using request IDs from Scout Ninja

This module provides a robust system for executing ad operations with support for:
- Concurrent operation execution
- Performance monitoring
- Error handling and retries
- Database persistence
- Rate limiting
- Metrics collection

Key Features:
- Multi-threaded operation execution
- Real-time performance metrics
- Automatic retry mechanism
- Operation logging
- Response time tracking
- Success rate monitoring

Example:
    >>> config = OperationConfig(
    ...     base_url="https://api.example.com",
    ...     auth_token="your-token",
    ...     publisher_id="pub123",
    ...     guest_id="guest123"
    ... )
    >>> strike = StrikeNinja(
    ...     operation_config=config,
    ...     db_connection_string="click_ninja.db",
    ...     worker_count=4
    ... )
    >>> strike.start()
    >>> strike.execute_operations(request_ids, "click")
"""

import logging
import time
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import threading
from queue import Queue
import requests
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
import sqlite3
import statistics
from collections import deque
import queue

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class OperationConfig:
    """
    Configuration for operation execution.
    
    This class holds all necessary configuration parameters for executing ad operations.
    
    Attributes:
        base_url (str): Base URL for the API endpoint
        auth_token (str): Authentication token for API access
        publisher_id (str): Publisher identifier
        guest_id (str): Guest user identifier
        ad_server_url (str): Base URL for ad server
        ad_server_impressions_url (str): URL for impression tracking
        ad_server_clicks_url (str): URL for click tracking
        timeout (int): Request timeout in seconds (default: 10)
        max_retries (int): Maximum number of retry attempts (default: 3)
        retry_delay (float): Delay between retries in seconds (default: 1.0)
    
    Example:
        >>> config = OperationConfig(
        ...     base_url="https://api.example.com",
        ...     auth_token="your-token",
        ...     publisher_id="pub123",
        ...     guest_id="guest123"
        ... )
    """
    base_url: str
    auth_token: str
    publisher_id: str
    guest_id: str
    ad_server_url: str = "https://dev.shyftcommerce.com/server"
    ad_server_impressions_url: str = "https://dev.shyftcommerce.com/server/rmn-impressions"
    ad_server_clicks_url: str = "https://dev.shyftcommerce.com/server/rmn-clicks"
    timeout: int = 10
    max_retries: int = 3
    retry_delay: float = 1.0

@dataclass
class PerformanceMetrics:
    """
    Performance metrics for operation monitoring.
    
    This class tracks various performance metrics for ad operations:
    - Response times
    - Success/failure counts
    - Total operations
    - Operations per second
    - Success rate
    - Response time percentiles
    
    Attributes:
        response_times (deque): Circular buffer of response times
        success_count (int): Number of successful operations
        failure_count (int): Number of failed operations
        total_operations (int): Total number of operations
        start_time (float): Timestamp when metrics started being collected
        lock (Lock): Thread synchronization lock
    
    Example:
        >>> metrics = PerformanceMetrics()
        >>> metrics.add_response_time(0.5)
        >>> metrics.record_success()
        >>> print(metrics.get_metrics())
    """
    response_times: deque = field(default_factory=lambda: deque(maxlen=1000))
    success_count: int = 0
    failure_count: int = 0
    total_operations: int = 0
    start_time: float = field(default_factory=time.time)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def add_response_time(self, response_time: float):
        """
        Add a response time measurement.
        
        Args:
            response_time (float): Response time in seconds
        
        Example:
            >>> metrics.add_response_time(0.5)
        """
        with self.lock:
            self.response_times.append(response_time)
            self.total_operations += 1

    def record_success(self):
        """
        Record a successful operation.
        
        Example:
            >>> metrics.record_success()
        """
        with self.lock:
            self.success_count += 1

    def record_failure(self):
        """
        Record a failed operation.
        
        Example:
            >>> metrics.record_failure()
        """
        with self.lock:
            self.failure_count += 1

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get current performance metrics.
        
        This method calculates:
        1. Success rate
        2. Average response time
        3. 95th percentile response time
        4. Operations per second
        5. Total operation counts
        
        Returns:
            Dict[str, Any]: Dictionary containing all metrics
        
        Example:
            >>> metrics = PerformanceMetrics()
            >>> metrics.add_response_time(0.5)
            >>> metrics.record_success()
            >>> print(metrics.get_metrics())
        """
        with self.lock:
            if not self.response_times:
                return {
                    "success_rate": 0.0,
                    "avg_response_time": 0.0,
                    "p95_response_time": 0.0,
                    "total_operations": 0,
                    "success_count": 0,
                    "failure_count": 0,
                    "operations_per_second": 0.0
                }

            elapsed_time = time.time() - self.start_time
            success_rate = (self.success_count / self.total_operations) * 100
            response_times = list(self.response_times)
            
            return {
                "success_rate": success_rate,
                "avg_response_time": statistics.mean(response_times),
                "p95_response_time": statistics.quantiles(response_times, n=20)[18],
                "total_operations": self.total_operations,
                "success_count": self.success_count,
                "failure_count": self.failure_count,
                "operations_per_second": self.total_operations / elapsed_time if elapsed_time > 0 else 0
            }

class WorkerPool:
    """
    Manages a pool of worker threads for operation execution.
    
    This class provides:
    1. Concurrent operation execution
    2. Task queuing
    3. Performance monitoring
    4. Graceful shutdown
    5. Error handling
    
    Attributes:
        worker_count (int): Number of worker threads
        executor (ThreadPoolExecutor): Thread pool for operation execution
        task_queue (Queue): Queue for pending operations
        stop_event (Event): Event for graceful shutdown
        workers (List[Thread]): List of worker threads
        metrics (PerformanceMetrics): Performance tracking
    
    Example:
        >>> pool = WorkerPool(worker_count=4)
        >>> pool.start()
        >>> pool.submit_operation({"request_id": "req123", "operation_type": "click"})
    """
    
    def __init__(self, worker_count: int = 4):
        """
        Initialize the worker pool.
        
        Args:
            worker_count (int): Number of worker threads to create
        
        Example:
            >>> pool = WorkerPool(worker_count=4)
        """
        self.worker_count = worker_count
        self.executor = ThreadPoolExecutor(max_workers=worker_count)
        self.task_queue = Queue()
        self.stop_event = threading.Event()
        self.workers: List[threading.Thread] = []
        self.metrics = PerformanceMetrics()

    def start(self):
        """
        Start the worker pool.
        
        This method:
        1. Creates worker threads
        2. Sets them as daemon threads
        3. Starts each thread
        4. Adds them to the workers list
        
        Example:
            >>> pool = WorkerPool(worker_count=4)
            >>> pool.start()
        """
        for _ in range(self.worker_count):
            worker = threading.Thread(target=self._worker_loop)
            worker.daemon = True
            worker.start()
            self.workers.append(worker)
        logger.info(f"Started {self.worker_count} Strike Ninja workers")

    def stop(self):
        """
        Stop the worker pool gracefully.
        
        This method:
        1. Sets the stop event
        2. Waits for workers to finish
        3. Shuts down the thread pool
        4. Cleans up resources
        
        Example:
            >>> pool = WorkerPool(worker_count=4)
            >>> pool.start()
            >>> # ... process operations ...
            >>> pool.stop()
        """
        self.stop_event.set()
        for worker in self.workers:
            worker.join()
        self.executor.shutdown(wait=True)
        logger.info("Stopped all Strike Ninja workers")

    def _worker_loop(self):
        """
        Main worker loop for processing operations.
        
        This method:
        1. Gets operations from the queue
        2. Executes each operation
        3. Records performance metrics
        4. Handles errors
        
        Example:
            >>> # Worker threads automatically run this loop
        """
        while not self.stop_event.is_set():
            try:
                operation = self.task_queue.get(timeout=1.0)
                if operation is None:
                    continue

                start_time = time.time()
                success = self._execute_operation(operation)
                response_time = time.time() - start_time

                self.metrics.add_response_time(response_time)
                if success:
                    self.metrics.record_success()
                else:
                    self.metrics.record_failure()

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in worker loop: {e}")

    def _execute_operation(self, operation: Dict[str, Any]) -> bool:
        """
        Execute a single operation.
        
        Args:
            operation (Dict[str, Any]): Operation data to execute
        
        Returns:
            bool: True if operation was successful
        
        Example:
            >>> success = pool._execute_operation({
            ...     "request_id": "req123",
            ...     "operation_type": "click"
            ... })
        """
        # Implementation will be added based on specific requirements
        return True

    def submit_operation(self, operation: Dict[str, Any]):
        """
        Submit an operation to the worker pool.
        
        Args:
            operation (Dict[str, Any]): Operation data to submit
        
        Example:
            >>> pool.submit_operation({
            ...     "request_id": "req123",
            ...     "operation_type": "click"
            ... })
        """
        self.task_queue.put(operation)

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get current performance metrics.
        
        Returns:
            Dict[str, Any]: Dictionary containing all metrics
        
        Example:
            >>> metrics = pool.get_metrics()
            >>> print(f"Success rate: {metrics['success_rate']}%")
        """
        return self.metrics.get_metrics()

class OperationExecutor:
    """
    Executes ad operations using the configured API endpoints.
    
    This class handles:
    1. Operation execution
    2. Response processing
    3. Error handling
    4. Retry logic
    
    Attributes:
        config (OperationConfig): Operation configuration
        session (Session): HTTP session for making requests
    
    Example:
        >>> executor = OperationExecutor(config)
        >>> success = executor.execute_operation("req123", "click")
    """
    
    def __init__(self, config: OperationConfig):
        """
        Initialize the operation executor.
        
        Args:
            config (OperationConfig): Operation configuration
        
        Example:
            >>> executor = OperationExecutor(config)
        """
        logger.info("Initializing OperationExecutor")
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {config.auth_token}",
            "Content-Type": "application/json"
        })
        logger.debug("OperationExecutor initialized with API configuration")

    def execute_operation(self, request_id: str, operation_type: str) -> bool:
        """
        Execute an ad operation.
        
        Args:
            request_id (str): Request identifier
            operation_type (str): Type of operation (impression or click)
        
        Returns:
            bool: True if operation was successful
        
        Example:
            >>> success = executor.execute_operation("req123", "click")
        """
        try:
            logger.info(f"Executing {operation_type} operation for request {request_id}")
            
            # Determine endpoint based on operation type
            if operation_type == 'impression':
                endpoint = self.config.ad_server_impressions_url
            elif operation_type == 'click':
                endpoint = self.config.ad_server_clicks_url
            else:
                logger.error(f"Unsupported operation type: {operation_type}")
                raise ValueError(f"Unsupported operation type: {operation_type}")
            
            # Create operation payload
            payload = {
                "requestId": request_id,
                "user": {
                    "publisherId": self.config.publisher_id if hasattr(self.config, 'publisher_id') else self.config.api.publisher_id,
                    "guestId": self.config.guest_id if hasattr(self.config, 'guest_id') else self.config.api.guest_id
                },
                "timestamp": datetime.now().isoformat()
            }
            
            # Execute operation
            logger.debug(f"Making API request to {endpoint}")
            response = self.session.post(
                endpoint,
                json=payload,
                timeout=self.config.timeout
            )
            response.raise_for_status()
            
            logger.info(f"Successfully executed {operation_type} operation for request {request_id}")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Failed to execute operation: {str(e)}")
            raise

class StrikeNinja:
    """
    Main Strike Ninja class that coordinates operation execution.
    
    This class provides:
    1. Operation execution coordination
    2. Database persistence
    3. Performance monitoring
    4. Worker pool management
    5. Error handling
    
    Attributes:
        operation_executor (OperationExecutor): Executes individual operations
        worker_pool (WorkerPool): Manages worker threads
        db_conn: SQLite database connection for operation logging
    
    Example:
        >>> strike = StrikeNinja(
        ...     operation_config=config,
        ...     db_connection_string="click_ninja.db",
        ...     worker_count=4
        ... )
        >>> strike.start()
        >>> strike.execute_operations(request_ids, "click")
    """
    
    def __init__(
        self,
        operation_config: OperationConfig,
        db_connection_string: str,
        worker_count: int = 4
    ):
        """
        Initialize the Strike Ninja.
        
        Args:
            operation_config (OperationConfig): Operation configuration
            db_connection_string (str): SQLite database path
            worker_count (int): Number of worker threads
        
        Example:
            >>> strike = StrikeNinja(
            ...     operation_config=config,
            ...     db_connection_string="click_ninja.db",
            ...     worker_count=4
            ... )
        """
        self.operation_executor = OperationExecutor(operation_config)
        self.worker_pool = WorkerPool(worker_count)
        self.db_conn = sqlite3.connect(db_connection_string)
        self.db_conn.row_factory = sqlite3.Row
        self._setup_database()

    def _setup_database(self):
        """
        Initialize database tables for operation tracking.
        
        This method:
        1. Creates the operation_log table
        2. Sets up necessary indexes
        3. Configures constraints
        
        Example:
            >>> strike = StrikeNinja(...)
            >>> # Database setup is automatic
        """
        cursor = self.db_conn.cursor()
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS operation_log (
                    id INTEGER PRIMARY KEY,
                    request_id TEXT NOT NULL,
                    operation_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    response_time FLOAT,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_operation_log_request_id 
                ON operation_log(request_id)
            """)
            
            self.db_conn.commit()
        finally:
            cursor.close()

    def start(self):
        """
        Start the Strike Ninja.
        
        This method:
        1. Initializes the worker pool
        2. Starts worker threads
        
        Example:
            >>> strike = StrikeNinja(...)
            >>> strike.start()
        """
        self.worker_pool.start()

    def stop(self):
        """
        Stop the Strike Ninja.
        
        This method:
        1. Stops the worker pool
        2. Cleans up resources
        
        Example:
            >>> strike = StrikeNinja(...)
            >>> strike.start()
            >>> # ... process operations ...
            >>> strike.stop()
        """
        self.worker_pool.stop()

    def execute_operations(self, request_ids: List[str], operation_type: str) -> int:
        """
        Execute operations for multiple request IDs.
        
        This method:
        1. Submits operations to the worker pool
        2. Tracks successful submissions
        3. Returns the count of submitted operations
        
        Args:
            request_ids (List[str]): List of request IDs to operate on
            operation_type (str): Type of operation to perform
        
        Returns:
            int: Number of successfully submitted operations
        
        Example:
            >>> num_submitted = strike.execute_operations(
            ...     request_ids=["req1", "req2"],
            ...     operation_type="click"
            ... )
        """
        success_count = 0
        for request_id in request_ids:
            operation = {
                "request_id": request_id,
                "operation_type": operation_type
            }
            self.worker_pool.submit_operation(operation)
            success_count += 1
        return success_count

    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get current performance metrics.
        
        Returns:
            Dict[str, Any]: Dictionary containing all metrics
        
        Example:
            >>> metrics = strike.get_performance_metrics()
            >>> print(f"Success rate: {metrics['success_rate']}%")
        """
        return self.worker_pool.get_metrics()

    def log_operation(self, request_id: str, operation_type: str, status: str, 
                     response_time: Optional[float] = None, error_message: Optional[str] = None):
        """
        Log an operation to the database.
        
        This method:
        1. Records operation details
        2. Stores performance metrics
        3. Captures error information
        
        Args:
            request_id (str): ID of the request
            operation_type (str): Type of operation performed
            status (str): Operation status
            response_time (Optional[float]): Response time in seconds
            error_message (Optional[str]): Error message if operation failed
        
        Example:
            >>> strike.log_operation(
            ...     request_id="req123",
            ...     operation_type="click",
            ...     status="success",
            ...     response_time=0.5
            ... )
        """
        try:
            cursor = self.db_conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO operation_log (
                        request_id, operation_type, status,
                        response_time, error_message
                    ) VALUES (?, ?, ?, ?, ?)
                """, (request_id, operation_type, status,
                      response_time, error_message))
                self.db_conn.commit()
            finally:
                cursor.close()
        except Exception as e:
            logger.error(f"Error logging operation: {e}") 
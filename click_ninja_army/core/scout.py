"""
Scout Ninja - Generates and manages ad request IDs for high-performance testing

This module provides a robust system for generating and managing ad request IDs
with support for rate limiting, priority queuing, and database persistence.

Key Features:
- Request generation with rate limiting
- Priority-based request queuing
- Database persistence for request tracking
- Concurrent request processing
- Retry mechanism for failed requests
- Comprehensive error handling

Example:
    >>> config = RequestConfig(
    ...     base_url="https://api.example.com",
    ...     auth_token="your-token",
    ...     publisher_id="pub123",
    ...     guest_id="guest123"
    ... )
    >>> scout = ScoutNinja(
    ...     request_config=config,
    ...     db_connection_string="click_ninja.db",
    ...     rate_limit=10.0,
    ...     burst_limit=20
    ... )
    >>> scout.start()
    >>> scout.generate_requests(campaigns, count=100)
"""

import logging
import time
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import threading
from queue import Queue, PriorityQueue
import requests
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
import sqlite3
from sqlite3 import Row

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class RequestConfig:
    """
    Configuration for request generation.
    
    This class holds all necessary configuration parameters for making ad requests.
    
    Attributes:
        base_url (str): Base URL for the API endpoint
        auth_token (str): Authentication token for API access
        publisher_id (str): Publisher identifier
        guest_id (str): Guest user identifier
        ad_size (str): Size of the ad (default: "adSize2")
        ad_count (int): Number of ads per request (default: 20)
        timeout (int): Request timeout in seconds (default: 10)
        ad_server_url (str): Base URL for ad server
        ad_server_impressions_url (str): URL for impression tracking
        ad_server_clicks_url (str): URL for click tracking
    """
    base_url: str
    auth_token: str
    publisher_id: str
    guest_id: str
    ad_size: str = "adSize2"
    ad_count: int = 20
    timeout: int = 10
    ad_server_url: str = "https://dev.shyftcommerce.com/server"
    ad_server_impressions_url: str = "https://dev.shyftcommerce.com/server/rmn-impressions"
    ad_server_clicks_url: str = "https://dev.shyftcommerce.com/server/rmn-clicks"

@dataclass
class RateLimiter:
    """
    Token bucket rate limiter implementation.
    
    This class implements a token bucket algorithm for rate limiting requests.
    It allows for burst traffic while maintaining a long-term average rate.
    
    Attributes:
        rate (float): Requests per second
        burst (int): Maximum burst size
        tokens (float): Current number of available tokens
        last_update (float): Timestamp of last token update
        lock (Lock): Thread synchronization lock
    
    Example:
        >>> limiter = RateLimiter(rate=10.0, burst=20)
        >>> if limiter.acquire():
        ...     make_request()
    """
    rate: float  # requests per second
    burst: int   # maximum burst size
    tokens: float = field(default=0.0)
    last_update: float = field(default_factory=time.time)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def acquire(self) -> bool:
        """
        Acquire a token from the bucket.
        
        This method implements the token bucket algorithm:
        1. Calculate time passed since last update
        2. Add new tokens based on time passed
        3. Cap tokens at burst limit
        4. Consume a token if available
        
        Returns:
            bool: True if a token was acquired, False otherwise
        
        Example:
            >>> limiter = RateLimiter(rate=10.0, burst=20)
            >>> if limiter.acquire():
            ...     make_request()
        """
        with self.lock:
            now = time.time()
            time_passed = now - self.last_update
            self.tokens = min(self.burst, self.tokens + time_passed * self.rate)
            self.last_update = now

            if self.tokens >= 1.0:
                self.tokens -= 1.0
                logger.debug(f"Token acquired. Remaining tokens: {self.tokens:.2f}")
                return True
            logger.debug(f"Rate limit exceeded. Available tokens: {self.tokens:.2f}")
            return False

class RequestGenerator:
    """
    Generates ad requests based on campaign data.
    
    This class handles the creation and submission of ad requests to the API.
    It supports multiple ad types and handles field name normalization.
    
    Attributes:
        config (RequestConfig): Configuration for request generation
        session (Session): HTTP session for making requests
    
    Example:
        >>> config = RequestConfig(...)
        >>> generator = RequestGenerator(config)
        >>> request_id = generator.generate_request(campaign_data)
    """
    
    def __init__(self, config: RequestConfig):
        """
        Initialize the request generator.
        
        Args:
            config (RequestConfig): Configuration for request generation
        
        Example:
            >>> config = RequestConfig(...)
            >>> generator = RequestGenerator(config)
        """
        logger.info("Initializing RequestGenerator")
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {config.auth_token}",
            "Content-Type": "application/json"
        })
        logger.debug("RequestGenerator initialized with API configuration")

    def _normalize_field_name(self, field_name: str) -> str:
        """
        Convert between camelCase and snake_case.
        
        Args:
            field_name (str): Field name to normalize
        
        Returns:
            str: Normalized field name
        
        Example:
            >>> generator._normalize_field_name("ad_type")  # Returns "adType"
            >>> generator._normalize_field_name("adType")   # Returns "ad_type"
        """
        if '_' in field_name:  # snake_case to camelCase
            parts = field_name.split('_')
            return parts[0] + ''.join(x.title() for x in parts[1:])
        else:  # camelCase to snake_case
            return ''.join(['_' + c.lower() if c.isupper() else c for c in field_name]).lstrip('_')

    def create_request_payload(self, campaign: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create request payload from campaign data.
        
        This method:
        1. Extracts ad type and tag from campaign data
        2. Handles both camelCase and snake_case field names
        3. Validates required fields
        4. Constructs the API payload
        
        Args:
            campaign (Dict[str, Any]): Campaign data containing ad configuration
        
        Returns:
            Dict[str, Any]: API request payload
        
        Raises:
            ValueError: If required fields are missing
        
        Example:
            >>> campaign = {
            ...     "adType": "banner",
            ...     "adTag": "tag123",
            ...     "keywords": ["keyword1"],
            ...     "pageCategoryIds": [1, 2]
            ... }
            >>> payload = generator.create_request_payload(campaign)
        """
        try:
            logger.debug(f"Creating payload for campaign: {campaign.get('campaign_id', 'unknown')}")
            
            # Handle both camelCase and snake_case field names
            ad_type = campaign.get("adType") or campaign.get("ad_type")
            
            # Check for adTag in root level or in slots array
            ad_tag = None
            if "adTag" in campaign or "ad_tag" in campaign:
                ad_tag = campaign.get("adTag") or campaign.get("ad_tag")
            elif "slots" in campaign and isinstance(campaign["slots"], list) and len(campaign["slots"]) > 0:
                ad_tag = campaign["slots"][0].get("adTag") or campaign["slots"][0].get("ad_tag")
            
            keywords = campaign.get("keywords", [])
            categories = campaign.get("pageCategoryIds") or campaign.get("page_category_ids", [])

            if not ad_type:
                logger.error("Missing ad type in campaign data")
                raise ValueError("Request data must contain 'adType' or 'ad_type' field")
            if not ad_tag:
                logger.error("Missing ad tag in campaign data")
                raise ValueError("Request data must contain 'adTag' or 'ad_tag' field in root or slots array")

            payload = {
                "adType": ad_type,
                "slots": [
                    {
                        "adTag": ad_tag,
                        "adSize": self.config.ad_size,
                        "adCount": self.config.ad_count
                    }
                ],
                "user": {
                    "publisherId": self.config.publisher_id if hasattr(self.config, 'publisher_id') else self.config.api.publisher_id,
                    "guestId": self.config.guest_id if hasattr(self.config, 'guest_id') else self.config.api.guest_id
                },
                "keywords": keywords,
                "pageCategoryIds": categories,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.debug(f"Created payload: {json.dumps(payload)}")
            return payload
            
        except Exception as e:
            logger.error(f"Failed to create request payload: {str(e)}")
            raise

    def generate_request(self, campaign: Dict[str, Any]) -> Optional[str]:
        """
        Generate a single ad request.
        
        Args:
            campaign (Dict[str, Any]): Campaign data containing:
                - adType (str): Type of ad
                - adTag (str): Ad tag
                - operation_type (str): Type of operation (impression or click)
                - Additional campaign-specific fields
        
        Returns:
            Optional[str]: Generated request ID if successful, None otherwise
        """
        try:
            logger.info("Generating request")
            
            # Validate required fields
            if 'adTag' not in campaign and not any('adTag' in slot for slot in campaign.get('slots', [])):
                logger.error("Missing required field: adTag")
                raise ValueError("Request data must contain 'adTag' field")
            
            # Create payload
            payload = self.create_request_payload(campaign)
            
            # Determine endpoint based on operation type
            operation_type = campaign.get('operation_type', 'impression')
            if operation_type == 'impression':
                endpoint = self.config.ad_server_impressions_url
            elif operation_type == 'click':
                endpoint = self.config.ad_server_clicks_url
            else:
                logger.error(f"Unsupported operation type: {operation_type}")
                raise ValueError(f"Unsupported operation type: {operation_type}")
            
            # Make API request
            logger.info(f"Making API request to {endpoint}")
            response = self.session.post(
                endpoint,
                json=payload,
                timeout=self.config.timeout
            )
            response.raise_for_status()
            
            # Process response
            response_data = response.json()
            request_id = response_data.get('requestId')
            
            if not request_id:
                logger.error("No request ID in response")
                return None
                
            logger.info(f"Successfully generated request with ID: {request_id}")
            return request_id
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Failed to generate request: {str(e)}")
            raise

class RequestPool:
    """
    Manages a pool of request IDs with priority and retry support.
    
    This class provides:
    1. Database persistence for requests
    2. Priority-based request queuing
    3. Request status tracking
    4. Retry mechanism
    5. Concurrent access support
    
    Attributes:
        db_conn: SQLite database connection
        priority_queue: Queue for managing request priorities
        lock: Thread synchronization lock
    
    Example:
        >>> pool = RequestPool("click_ninja.db")
        >>> pool.add_request("req123", target_matrix_id=1, priority=1)
    """
    
    def __init__(self, db_connection_string: str):
        """
        Initialize the request pool.
        
        Args:
            db_connection_string (str): SQLite database path
        
        Example:
            >>> pool = RequestPool("click_ninja.db")
        """
        self.db_conn = sqlite3.connect(db_connection_string)
        self.db_conn.row_factory = sqlite3.Row
        self._setup_database()
        self.priority_queue = PriorityQueue()
        self.lock = threading.Lock()

    def _setup_database(self):
        """
        Initialize database tables and indexes.
        
        This method:
        1. Creates the request_pool table if it doesn't exist
        2. Sets up necessary indexes
        3. Configures constraints
        
        Example:
            >>> pool = RequestPool("click_ninja.db")
            >>> # Database setup is automatic
        """
        cursor = self.db_conn.cursor()
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS request_pool (
                    id INTEGER PRIMARY KEY,
                    request_id TEXT UNIQUE NOT NULL,
                    target_matrix_id INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    priority INTEGER DEFAULT 0,
                    retries INTEGER DEFAULT 0,
                    last_attempt TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT valid_status CHECK (status IN ('pending', 'in_progress', 'completed', 'failed'))
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_request_pool_status 
                ON request_pool(status, priority)
            """)
            
            self.db_conn.commit()
        finally:
            cursor.close()

    def add_request(self, request_id: str, target_matrix_id: int, priority: int = 0) -> bool:
        """
        Add a new request to the pool.
        
        Args:
            request_id (str): Unique identifier for the request
            target_matrix_id (int): ID of the target matrix
            priority (int): Request priority (default: 0)
        
        Returns:
            bool: True if request was added successfully
        
        Example:
            >>> pool.add_request("req123", target_matrix_id=1, priority=1)
        """
        try:
            cursor = self.db_conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO request_pool (request_id, target_matrix_id, priority)
                    VALUES (?, ?, ?)
                    ON CONFLICT (request_id) DO NOTHING
                    RETURNING id
                """, (request_id, target_matrix_id, priority))
                self.db_conn.commit()
                return cursor.fetchone() is not None
            finally:
                cursor.close()
        except Exception as e:
            logger.error(f"Error adding request to pool: {e}")
            return False

    def get_next_request(self) -> Optional[Dict[str, Any]]:
        """
        Get the next request to process based on priority.
        
        This method:
        1. Selects the highest priority pending request
        2. Updates its status to in_progress
        3. Records the attempt timestamp
        
        Returns:
            Optional[Dict[str, Any]]: Request data if available
        
        Example:
            >>> request = pool.get_next_request()
            >>> if request:
            ...     process_request(request)
        """
        try:
            cursor = self.db_conn.cursor()
            try:
                cursor.execute("""
                    UPDATE request_pool
                    SET status = 'in_progress',
                        last_attempt = CURRENT_TIMESTAMP
                    WHERE id = (
                        SELECT id
                        FROM request_pool
                        WHERE status = 'pending'
                        ORDER BY priority DESC, created_at ASC
                        LIMIT 1
                    )
                    RETURNING id, request_id, target_matrix_id, retries
                """)
                result = cursor.fetchone()
                if result:
                    self.db_conn.commit()
                    return {
                        "id": result[0],
                        "request_id": result[1],
                        "target_matrix_id": result[2],
                        "retries": result[3]
                    }
                return None
            finally:
                cursor.close()
        except Exception as e:
            logger.error(f"Error getting next request: {e}")
            return None

    def mark_request_completed(self, request_id: int) -> bool:
        """
        Mark a request as completed.
        
        Args:
            request_id (int): ID of the request to mark as completed
        
        Returns:
            bool: True if request was marked as completed
        
        Example:
            >>> pool.mark_request_completed(1)
        """
        try:
            cursor = self.db_conn.cursor()
            try:
                cursor.execute("""
                    UPDATE request_pool
                    SET status = 'completed'
                    WHERE id = ?
                """, (request_id,))
                self.db_conn.commit()
                return cursor.rowcount > 0
            finally:
                cursor.close()
        except Exception as e:
            logger.error(f"Error marking request completed: {e}")
            return False

    def mark_request_failed(self, request_id: int, max_retries: int = 3) -> bool:
        """
        Mark a request as failed and handle retries.
        
        This method:
        1. Increments the retry counter
        2. Either resets the request to pending or marks it as failed
        3. Updates the last attempt timestamp
        
        Args:
            request_id (int): ID of the request to mark as failed
            max_retries (int): Maximum number of retry attempts
        
        Returns:
            bool: True if request was handled successfully
        
        Example:
            >>> pool.mark_request_failed(1, max_retries=3)
        """
        try:
            cursor = self.db_conn.cursor()
            try:
                cursor.execute("""
                    UPDATE request_pool
                    SET status = CASE
                            WHEN retries < ? THEN 'pending'
                            ELSE 'failed'
                        END,
                        retries = retries + 1
                    WHERE id = ?
                    RETURNING status
                """, (max_retries, request_id))
                result = cursor.fetchone()
                self.db_conn.commit()
                return result and result[0] == 'pending'
            finally:
                cursor.close()
        except Exception as e:
            logger.error(f"Error marking request failed: {e}")
            return False

class ScoutNinja:
    """
    Main class for managing the request generation and processing pipeline.
    
    This class coordinates:
    1. Request generation
    2. Rate limiting
    3. Worker pool management
    4. Database persistence
    5. Error handling
    
    Attributes:
        request_config (RequestConfig): Configuration for request generation
        db_connection_string (str): Database connection string
        rate_limit (float): Requests per second limit
        burst_limit (int): Maximum burst size
        worker_count (int): Number of worker threads
    
    Example:
        >>> scout = ScoutNinja(
        ...     request_config=config,
        ...     db_connection_string="click_ninja.db",
        ...     rate_limit=10.0,
        ...     burst_limit=20
        ... )
        >>> scout.start()
    """
    
    def __init__(
        self,
        request_config: RequestConfig,
        db_connection_string: str,
        rate_limit: float = 10.0,
        burst_limit: int = 20,
        worker_count: int = 1
    ):
        """
        Initialize the Scout Ninja.
        
        Args:
            request_config (RequestConfig): Configuration for request generation
            db_connection_string (str): Database connection string
            rate_limit (float): Requests per second limit
            burst_limit (int): Maximum burst size
            worker_count (int): Number of worker threads
        
        Example:
            >>> scout = ScoutNinja(
            ...     request_config=config,
            ...     db_connection_string="click_ninja.db",
            ...     rate_limit=10.0,
            ...     burst_limit=20
            ... )
        """
        logger.info("Initializing ScoutNinja")
        self.request_config = request_config
        self.db_connection_string = db_connection_string
        self.rate_limiter = RateLimiter(rate=rate_limit, burst=burst_limit)
        self.worker_count = worker_count
        self.running = False
        self.workers = []
        self.request_generator = RequestGenerator(request_config)
        self.request_pool = RequestPool(db_connection_string)
        logger.debug("ScoutNinja initialized successfully")

    def start(self):
        """
        Start the Scout Ninja processing pipeline.
        
        This method:
        1. Initializes the request pool
        2. Creates worker threads
        3. Starts the worker loop
        
        Example:
            >>> scout.start()
        """
        try:
            logger.info("Starting ScoutNinja")
            self.running = True
            
            # Start worker threads
            for i in range(self.worker_count):
                worker = threading.Thread(target=self._worker_loop, name=f"scout-worker-{i}")
                worker.daemon = True
                worker.start()
                self.workers.append(worker)
                logger.debug(f"Started worker thread {i}")
            
            logger.info(f"ScoutNinja started with {self.worker_count} workers")
        except Exception as e:
            logger.error(f"Failed to start ScoutNinja: {str(e)}")
            raise

    def stop(self):
        """
        Stop the Scout Ninja processing pipeline.
        
        This method:
        1. Signals workers to stop
        2. Waits for workers to finish
        3. Cleans up resources
        
        Example:
            >>> scout.stop()
        """
        try:
            logger.info("Stopping ScoutNinja")
            self.running = False
            
            for worker in self.workers:
                worker.join()
            
            self.workers.clear()
            logger.info("ScoutNinja stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping ScoutNinja: {str(e)}")
            raise

    def _worker_loop(self):
        """
        Main worker loop for processing requests.
        
        This method:
        1. Gets the next request from the pool
        2. Processes the request
        3. Updates request status
        4. Handles errors
        
        Example:
            >>> # Worker threads automatically run this loop
        """
        thread_name = threading.current_thread().name
        logger.debug(f"Worker {thread_name} started")
        
        while self.running:
            try:
                # Check rate limit
                if not self.rate_limiter.acquire():
                    time.sleep(0.1)
                    continue
                
                # Process requests
                logger.debug(f"Worker {thread_name} checking for requests")
                request = self.request_pool.get_next_request()
                if not request:
                    time.sleep(0.1)
                    continue

                try:
                    # Process the request
                    success = self._process_request(request)
                    if success:
                        self.request_pool.mark_request_completed(request["id"])
                    else:
                        self.request_pool.mark_request_failed(request["id"])
                except Exception as e:
                    logger.error(f"Error processing request {request['id']}: {e}")
                    self.request_pool.mark_request_failed(request["id"])
            except Exception as e:
                logger.error(f"Worker {thread_name} encountered error: {str(e)}")

    def _process_request(self, request: Dict[str, Any]) -> bool:
        """
        Process a single request.
        
        Args:
            request (Dict[str, Any]): Request data to process
        
        Returns:
            bool: True if request was processed successfully
        
        Example:
            >>> success = scout._process_request(request)
        """
        # Implementation depends on specific requirements
        # This is a placeholder for the actual request processing logic
        return True

    def generate_requests(self, campaigns: List[Dict[str, Any]], count: int) -> int:
        """
        Generate multiple requests for the given campaigns.
        
        This method:
        1. Validates campaign data
        2. Generates requests up to the specified count
        3. Adds requests to the pool
        4. Returns the number of successful generations
        
        Args:
            campaigns (List[Dict[str, Any]]): List of campaign data
            count (int): Number of requests to generate
        
        Returns:
            int: Number of successfully generated requests
        
        Example:
            >>> num_generated = scout.generate_requests(campaigns, count=100)
        """
        try:
            logger.info(f"Generating {count} requests for {len(campaigns)} campaigns")
            success_count = 0
            
            for campaign in campaigns:
                campaign_id = campaign.get('campaign_id', 'unknown')
                logger.debug(f"Processing campaign {campaign_id}")
                
                for _ in range(count):
                    if self.rate_limiter.acquire():
                        request_id = self.request_generator.generate_request(campaign)
                        if request_id:
                            success_count += 1
                            logger.debug(f"Generated request {request_id} for campaign {campaign_id}")
                    else:
                        logger.debug("Rate limit reached, waiting...")
                        time.sleep(0.1)
            
            logger.info(f"Successfully generated {success_count} requests")
            return success_count
            
        except Exception as e:
            logger.error(f"Error generating requests: {str(e)}")
            return 0 
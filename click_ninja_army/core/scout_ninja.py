"""
Scout Ninja - Parallel request generation with rate limiting and retry mechanisms

This module provides a robust system for generating ad requests in parallel,
with support for rate limiting, priority queuing, and automatic retries.

Key Features:
- Parallel request generation
- Rate limiting per API endpoint
- Priority-based request queuing
- Automatic retry mechanism
- Progress tracking
- Comprehensive error handling

Example:
    >>> config = RequestConfig(api_url='https://api.example.com', api_token='your_token', rate_limit=10, burst_limit=5)
    >>> scout = ScoutNinja(config, db, metrics_manager)
    >>> scout.start()
    >>> scout.generate_requests(entries, priority=1)
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
import traceback

logger = logging.getLogger(__name__)

@dataclass
class RequestConfig:
    """Configuration for request generation."""
    api_url: str
    api_token: str
    rate_limit: float  # requests per second
    burst_limit: int   # maximum burst size
    max_retries: int = 3
    retry_delay: float = 1.0
    timeout: int = 10
    publisher_id: str = 'PET67'
    guest_id: str = 'G-PET34567'

@dataclass
class RateLimiter:
    """Token bucket rate limiter implementation."""
    rate: float  # requests per second
    burst: int   # maximum burst size
    tokens: float = field(default=0.0)
    last_update: float = field(default_factory=time.time)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def acquire(self) -> bool:
        """Acquire a token from the bucket."""
        with self.lock:
            now = time.time()
            time_passed = now - self.last_update
            self.tokens = min(self.burst, self.tokens + time_passed * self.rate)
            self.last_update = now

            if self.tokens >= 1.0:
                self.tokens -= 1.0
                return True
            return False

class ScoutNinja:
    """
    Handles parallel request generation with rate limiting and retries.
    
    This class manages:
    1. Parallel request generation
    2. Rate limiting
    3. Request queuing
    4. Retry mechanism
    5. Progress tracking
    """

    def __init__(self, config: RequestConfig, db, metrics_manager: MetricsManager):
        """
        Initialize Scout Ninja.
        
        Args:
            config: Request configuration
            db: Database instance
            metrics_manager: Metrics manager instance
        """
        self.config = config
        self.db = db
        self.metrics_manager = metrics_manager
        self.rate_limiter = RateLimiter(config.rate_limit, config.burst_limit)
        self.request_queue = PriorityQueue()
        self.worker_count = min(10, config.burst_limit)  # Limit worker count
        self.executor = ThreadPoolExecutor(max_workers=self.worker_count)
        self.running = False
        self.stats = {
            'requests_generated': 0,
            'requests_failed': 0,
            'retries': 0
        }
        self.stats_lock = threading.Lock()
        self.failure_counter = 0
        self.failure_threshold = 20
        self.circuit_breaker_tripped = False
        self.circuit_breaker_cooldown = 60  # seconds

    def _create_request_payload(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Create REST API request payload from campaign pool entry for supported ad types."""
        if entry['ad_type'] == 'Product':
            return {
                'adType': 'Product',
                'slots': [
                    {
                        'adTag': entry['ad_tag'],
                        'adSize': entry.get('ad_size', 'adSize4'),
                        'adCount': entry.get('ad_count', 40)
                    }
                ],
                'user': {
                    'publisherId': self.config.publisher_id if hasattr(self.config, 'publisher_id') else 'PET67',
                    'customerId': entry.get('customer_id'),
                    'guestId': self.config.guest_id if hasattr(self.config, 'guest_id') else 'G-PET34567',
                    'networkIp': entry.get('network_ip', ''),
                    'searchKeyword': entry.get('search_keyword', ''),
                    'pageType': entry.get('page_type', ''),
                    'pageCategoryIds': entry.get('page_category_ids', []),
                    'additionalProductFilters': entry.get('additional_product_filters', None)
                },
                'page': {
                    'currentUrl': entry.get('current_url', ''),
                    'sourceUrl': entry.get('source_url', '')
                },
                'device': {
                    'deviceId': entry.get('device_id', ''),
                    'userAgent': entry.get('user_agent', ''),
                    'language': entry.get('language', ''),
                    'platform': entry.get('platform', ''),
                    'screenSize': entry.get('screen_size', '')
                },
                'keyValues': entry.get('key_values', None),
                'memoryToken': entry.get('memory_token', None)
            }
        elif entry['ad_type'] == 'Display':
            return {
                'adType': 'Display',
                'slots': [
                    {
                        'adTag': entry['ad_tag'],
                        'adSize': entry.get('ad_size', 'adSize2'),
                        'adCount': entry.get('ad_count', 10)
                    }
                ],
                'user': {
                    'publisherId': self.config.publisher_id if hasattr(self.config, 'publisher_id') else 'PET67',
                    'customerId': entry.get('customer_id'),
                    'guestId': self.config.guest_id if hasattr(self.config, 'guest_id') else 'G-PET34567',
                    'networkIp': entry.get('network_ip', ''),
                    'searchKeyword': entry.get('search_keyword', None),
                    'pageType': entry.get('page_type', ''),
                    'pageCategoryIds': entry.get('page_category_ids', None),
                    'additionalProductFilters': entry.get('additional_product_filters', None)
                },
                'page': {
                    'currentUrl': entry.get('current_url', ''),
                    'sourceUrl': entry.get('source_url', '')
                },
                'device': {
                    'deviceId': entry.get('device_id', ''),
                    'userAgent': entry.get('user_agent', ''),
                    'language': entry.get('language', ''),
                    'platform': entry.get('platform', ''),
                    'screenSize': entry.get('screen_size', '')
                },
                'keyValues': entry.get('key_values', None)
            }
        elif entry['ad_type'] == 'Video':
            return {
                'adType': 'Video',
                'slots': entry.get('slots', [
                    {
                        'adTag': entry.get('ad_tag', ''),
                        'adSize': entry.get('ad_size', 'adSize1'),
                        'adCount': entry.get('ad_count', 1)
                    }
                ]),
                'user': {
                    'publisherId': self.config.publisher_id if hasattr(self.config, 'publisher_id') else 'PET67',
                    'customerId': entry.get('customer_id'),
                    'guestId': self.config.guest_id if hasattr(self.config, 'guest_id') else 'G-PET34567',
                    'networkIp': entry.get('network_ip', ''),
                    'searchKeyword': entry.get('search_keyword', None),
                    'pageType': entry.get('page_type', ''),
                    'pageCategoryIds': entry.get('page_category_ids', None),
                    'additionalProductFilters': entry.get('additional_product_filters', None)
                },
                'page': {
                    'currentUrl': entry.get('current_url', ''),
                    'sourceUrl': entry.get('source_url', '')
                },
                'device': {
                    'deviceId': entry.get('device_id', ''),
                    'userAgent': entry.get('user_agent', ''),
                    'language': entry.get('language', ''),
                    'platform': entry.get('platform', ''),
                    'screenSize': entry.get('screen_size', '')
                },
                'keyValues': entry.get('key_values', None)
            }
        elif entry['ad_type'] == 'NativeFixed':
            return {
                'adType': 'NativeFixed',
                'slots': entry.get('slots', [
                    {
                        'adTag': entry.get('ad_tag', ''),
                        'adSize': entry.get('ad_size', 'adSize1'),
                        'adCount': entry.get('ad_count', 1)
                    }
                ]),
                'user': {
                    'publisherId': self.config.publisher_id if hasattr(self.config, 'publisher_id') else 'PET67',
                    'customerId': entry.get('customer_id'),
                    'guestId': self.config.guest_id if hasattr(self.config, 'guest_id') else 'G-PET34567',
                    'networkIp': entry.get('network_ip', ''),
                    'searchKeyword': entry.get('search_keyword', None),
                    'pageType': entry.get('page_type', ''),
                    'pageCategoryIds': entry.get('page_category_ids', None),
                    'additionalProductFilters': entry.get('additional_product_filters', None)
                },
                'page': {
                    'currentUrl': entry.get('current_url', ''),
                    'sourceUrl': entry.get('source_url', '')
                },
                'device': {
                    'deviceId': entry.get('device_id', ''),
                    'userAgent': entry.get('user_agent', ''),
                    'language': entry.get('language', ''),
                    'platform': entry.get('platform', ''),
                    'screenSize': entry.get('screen_size', '')
                },
                'keyValues': entry.get('key_values', None)
            }
        elif entry['ad_type'] == 'NativeDynamic':
            return {
                'adType': 'Display',
                'slots': entry.get('slots', [
                    {
                        'adTag': entry.get('ad_tag', ''),
                        'adSize': entry.get('ad_size', 'adSize2'),
                        'adCount': entry.get('ad_count', 10)
                    }
                ]),
                'user': {
                    'publisherId': self.config.publisher_id if hasattr(self.config, 'publisher_id') else 'PET67',
                    'customerId': entry.get('customer_id'),
                    'guestId': self.config.guest_id if hasattr(self.config, 'guest_id') else 'G-PET34567',
                    'networkIp': entry.get('network_ip', ''),
                    'searchKeyword': entry.get('search_keyword', None),
                    'pageType': entry.get('page_type', ''),
                    'pageCategoryIds': entry.get('page_category_ids', None),
                    'additionalProductFilters': entry.get('additional_product_filters', None)
                },
                'page': {
                    'currentUrl': entry.get('current_url', ''),
                    'sourceUrl': entry.get('source_url', '')
                },
                'device': {
                    'deviceId': entry.get('device_id', ''),
                    'userAgent': entry.get('user_agent', ''),
                    'language': entry.get('language', ''),
                    'platform': entry.get('platform', ''),
                    'screenSize': entry.get('screen_size', '')
                },
                'keyValues': entry.get('key_values', None)
            }
        # Fallback for other ad types (to be implemented)
        return {}

    def _trip_circuit_breaker(self):
        self.circuit_breaker_tripped = True
        logger.critical(f"Circuit breaker tripped: {self.failure_counter} consecutive failures. Pausing all workers for {self.circuit_breaker_cooldown} seconds.")
        time.sleep(self.circuit_breaker_cooldown)
        logger.info("Circuit breaker cooldown complete. Resuming workers.")
        self.failure_counter = 0
        self.circuit_breaker_tripped = False

    def _generate_request(self, entry: Dict[str, Any], retry_count: int = 0) -> Optional[str]:
        if self.circuit_breaker_tripped:
            logger.warning("Circuit breaker is active. Skipping request.")
            return None
        if not self.rate_limiter.acquire():
            time.sleep(0.1)
            return self._generate_request(entry, retry_count)
        start_time = time.time()
        try:
            payload = self._create_request_payload(entry)
            response = requests.post(
                self.config.api_url,
                json=payload,
                headers={'Authorization': f'Bearer {self.config.api_token}'},
                timeout=self.config.timeout
            )
            response.raise_for_status()
            ad_request_id = response.json().get('adRequestId')
            if not ad_request_id:
                raise ValueError("No adRequestId in response")
            response_time = time.time() - start_time
            self.metrics_manager.update_performance_metrics(
                entry['ad_item_id'],
                'request_generation',
                True,
                response_time,
                False
            )
            self.db.update_ad_request_id(entry['request_id'], ad_request_id)
            # Reset failure counter on success
            self.failure_counter = 0
            return ad_request_id
        except Exception as e:
            self.failure_counter += 1
            if self.failure_counter >= self.failure_threshold:
                self._trip_circuit_breaker()
            if retry_count < self.config.max_retries:
                logger.warning(f"Request generation failed (attempt {retry_count + 1}): {str(e)}")
                time.sleep(self.config.retry_delay * (retry_count + 1))
                self.metrics_manager.update_performance_metrics(
                    entry['ad_item_id'],
                    'request_generation',
                    False,
                    time.time() - start_time,
                    True
                )
                return self._generate_request(entry, retry_count + 1)
            else:
                logger.error(f"Request generation failed after {self.config.max_retries} attempts: {str(e)}")
                self.metrics_manager.update_performance_metrics(
                    entry['ad_item_id'],
                    'request_generation',
                    False,
                    time.time() - start_time,
                    False
                )
                return None

    def _worker(self):
        """Worker thread for processing requests."""
        while self.running:
            try:
                priority, tiebreaker, entry = self.request_queue.get(timeout=1)
                ad_request_id = self._generate_request(entry)
                
                if ad_request_id:
                    # Store in request pool
                    self.db.insert_request_pool_entry(entry['id'], ad_request_id)
                    with self.stats_lock:
                        self.stats['requests_generated'] += 1
                
                self.request_queue.task_done()
            except Exception as e:
                import queue
                if isinstance(e, queue.Empty):
                    # If the queue is empty and all tasks are done, exit the worker
                    if self.request_queue.empty():
                        break
                    else:
                        continue
                logger.error(f"Worker error: {str(e)}\n{traceback.format_exc()}")
                continue

    def start(self):
        """Start the request generation process."""
        self.running = True
        for _ in range(self.worker_count):
            self.executor.submit(self._worker)
        logger.info(f"Started {self.worker_count} worker threads")

    def stop(self):
        """Stop the request generation process."""
        self.running = False
        self.executor.shutdown(wait=True)
        logger.info("Stopped all worker threads")

    def generate_requests(self, entries: List[Dict[str, Any]], priority: int = 0):
        """
        Queue campaign pool entries for request generation.
        
        Args:
            entries: List of campaign pool entries
            priority: Request priority (lower number = higher priority)
        """
        for idx, entry in enumerate(entries):
            self.request_queue.put((priority, idx, entry))  # FIFO: priority=0, tiebreaker=idx
        logger.info(f"Queued {len(entries)} entries for request generation")

    def get_stats(self) -> Dict[str, int]:
        """Get current statistics."""
        with self.stats_lock:
            return self.stats.copy()

    def get_metrics(self, ad_item_id: str) -> Dict[str, Any]:
        """Get performance metrics for an ad item."""
        return self.metrics_manager.get_performance_metrics(ad_item_id) 
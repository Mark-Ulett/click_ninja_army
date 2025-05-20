"""
Rate Limiter - Controls the rate of operations (e.g., impressions, clicks)

This module provides a simple token bucket rate limiter to ensure operations
do not exceed a specified rate and burst limit.
"""

import time
import threading

class RateLimiter:
    def __init__(self, rate_limit: float, burst_limit: int):
        self.rate_limit = rate_limit  # tokens per second
        self.burst_limit = burst_limit  # maximum tokens
        self.tokens = burst_limit
        self.last_update = time.time()
        self.lock = threading.Lock()

    def acquire(self) -> bool:
        with self.lock:
            now = time.time()
            time_passed = now - self.last_update
            self.tokens = min(self.burst_limit, self.tokens + time_passed * self.rate_limit)
            self.last_update = now
            if self.tokens >= 1:
                self.tokens -= 1
                return True
            return False 
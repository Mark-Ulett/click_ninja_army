"""
Metrics Manager - Comprehensive metrics tracking and reporting

This module provides a centralized system for tracking and reporting metrics
across the Click Ninja Army system, including campaign pool generation,
request generation, impressions, and clicks.

Key Features:
- Campaign pool metrics tracking
- Request pool metrics tracking
- Performance metrics per ad item
- Success/failure rate monitoring
- Response time tracking
- Error rate logging

Example:
    >>> metrics = MetricsManager("click_ninja.db")
    >>> metrics.log_campaign_pool_metrics(100, 150, 5.2)
"""

import logging
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field
from collections import defaultdict
import threading
import sqlite3

logger = logging.getLogger(__name__)

@dataclass
class AdItemMetrics:
    """Metrics for a single ad item."""
    impressions: int = 0
    clicks: int = 0
    success_count: int = 0
    failure_count: int = 0
    retry_count: int = 0
    response_times: List[float] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)

class MetricsManager:
    """
    Centralized metrics management system.
    
    This class handles:
    1. Campaign pool metrics
    2. Request pool metrics
    3. Performance metrics per ad item
    4. Success/failure tracking
    5. Response time tracking
    6. Error rate monitoring
    """

    def __init__(self, db_path: str):
        """
        Initialize the metrics manager.
        
        Args:
            db_path: Path to the SQLite database
        """
        self.db_path = db_path
        self._setup_tables()
        self.ad_item_metrics: Dict[str, AdItemMetrics] = defaultdict(AdItemMetrics)
        self.lock = threading.Lock()

    def _setup_tables(self):
        """Set up metrics tables in the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Campaign pool metrics table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS campaign_pool_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        csv_rows_processed INTEGER NOT NULL,
                        campaign_pool_rows_generated INTEGER NOT NULL,
                        generation_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        duration_seconds REAL,
                        status TEXT DEFAULT 'completed'
                    )
                """)
                
                # Request pool metrics table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS request_pool_metrics (
                        id INTEGER PRIMARY KEY,
                        requests_generated INTEGER NOT NULL,
                        generation_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        duration_seconds REAL,
                        status TEXT DEFAULT 'completed'
                    )
                """)
                
                # Performance metrics table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS performance_metrics (
                        id INTEGER PRIMARY KEY,
                        ad_item_id TEXT NOT NULL,
                        operation_type TEXT NOT NULL,
                        success_count INTEGER DEFAULT 0,
                        failure_count INTEGER DEFAULT 0,
                        retry_count INTEGER DEFAULT 0,
                        avg_response_time REAL,
                        total_operations INTEGER DEFAULT 0,
                        last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(ad_item_id, operation_type)
                    )
                """)
                
                # Create indexes
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_performance_metrics_ad_item 
                    ON performance_metrics(ad_item_id)
                """)
                
                conn.commit()
                logger.info("Metrics tables setup completed")
        except Exception as e:
            logger.error(f"Error setting up metrics tables: {str(e)}")
            raise

    def log_campaign_pool_metrics(self, rows_processed: int, rows_generated: int, 
                                duration_seconds: float, status: str = 'completed'):
        """Log campaign pool generation metrics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO campaign_pool_metrics (
                        csv_rows_processed, campaign_pool_rows_generated, duration_seconds, status
                    ) VALUES (?, ?, ?, ?)
                """, (rows_processed, rows_generated, duration_seconds, status))
                conn.commit()
                logger.info(f"Logged campaign pool metrics: {rows_processed} processed, "
                          f"{rows_generated} generated")
        except Exception as e:
            logger.error(f"Error logging campaign pool metrics: {str(e)}")
            raise

    def log_request_pool_metrics(self, requests_generated: int, duration_seconds: float,
                               status: str = 'completed'):
        """Log request pool generation metrics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO request_pool_metrics (
                        requests_generated, duration_seconds, status
                    ) VALUES (?, ?, ?)
                """, (requests_generated, duration_seconds, status))
                conn.commit()
                logger.info(f"Logged request pool metrics: {requests_generated} generated")
        except Exception as e:
            logger.error(f"Error logging request pool metrics: {str(e)}")
            raise

    def update_performance_metrics(self, ad_item_id: str, operation_type: str,
                                 success: bool, response_time: float, retry: bool = False):
        """Update performance metrics for an ad item."""
        with self.lock:
            metrics = self.ad_item_metrics[ad_item_id]
            
            if success:
                metrics.success_count += 1
                metrics.response_times.append(response_time)
                if operation_type == 'impression':
                    metrics.impressions += 1
                elif operation_type == 'click':
                    metrics.clicks += 1
            else:
                metrics.failure_count += 1
            
            if retry:
                metrics.retry_count += 1
            
            metrics.last_updated = datetime.now()
            
            # Update database
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO performance_metrics (
                            ad_item_id, operation_type, success_count, failure_count,
                            retry_count, avg_response_time, total_operations, last_updated
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(ad_item_id, operation_type) DO UPDATE SET
                            success_count = success_count + ?,
                            failure_count = failure_count + ?,
                            retry_count = retry_count + ?,
                            avg_response_time = (avg_response_time * total_operations + ?) / (total_operations + 1),
                            total_operations = total_operations + 1,
                            last_updated = ?
                    """, (
                        ad_item_id, operation_type,
                        int(success), int(not success), int(retry),
                        response_time, 1, datetime.now(),
                        int(success), int(not success), int(retry),
                        response_time, datetime.now()
                    ))
                    conn.commit()
            except Exception as e:
                logger.error(f"Error updating performance metrics: {str(e)}")
                raise

    def get_ad_item_metrics(self, ad_item_id: str) -> Dict[str, Any]:
        """Get metrics for a specific ad item."""
        with self.lock:
            metrics = self.ad_item_metrics[ad_item_id]
            response_times = metrics.response_times
            
            return {
                'impressions': metrics.impressions,
                'clicks': metrics.clicks,
                'success_rate': (metrics.success_count / (metrics.success_count + metrics.failure_count) * 100
                               if (metrics.success_count + metrics.failure_count) > 0 else 0),
                'avg_response_time': (sum(response_times) / len(response_times)
                                    if response_times else 0),
                'retry_rate': (metrics.retry_count / (metrics.success_count + metrics.failure_count) * 100
                              if (metrics.success_count + metrics.failure_count) > 0 else 0),
                'last_updated': metrics.last_updated.isoformat()
            }

    def get_campaign_pool_metrics(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent campaign pool metrics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM campaign_pool_metrics
                    ORDER BY generation_timestamp DESC
                    LIMIT ?
                """, (limit,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting campaign pool metrics: {str(e)}")
            return []

    def get_request_pool_metrics(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent request pool metrics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM request_pool_metrics
                    ORDER BY generation_timestamp DESC
                    LIMIT ?
                """, (limit,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting request pool metrics: {str(e)}")
            return []

    def get_performance_metrics(self, ad_item_id: str) -> Dict[str, Any]:
        """Get performance metrics for an ad item from the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM performance_metrics
                    WHERE ad_item_id = ?
                """, (ad_item_id,))
                rows = cursor.fetchall()
                
                if not rows:
                    return {}
                
                return {
                    'impression_metrics': dict(rows[0]) if rows[0]['operation_type'] == 'impression' else {},
                    'click_metrics': dict(rows[1]) if len(rows) > 1 and rows[1]['operation_type'] == 'click' else {}
                }
        except Exception as e:
            logger.error(f"Error getting performance metrics: {str(e)}")
            return {} 
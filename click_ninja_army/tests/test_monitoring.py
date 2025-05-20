"""
Test cases for the monitoring system.

This module contains tests to verify:
1. Logging functionality
2. Metrics collection
3. Database operations
4. Thread safety
5. Error handling
"""

import unittest
import os
import time
import json
import logging
from datetime import datetime
from queue import Queue
from ..core.monitoring import MonitoringSystem

class TestMonitoringSystem(unittest.TestCase):
    """Test cases for the monitoring system."""

    def setUp(self):
        """Set up test environment."""
        self.test_db_path = "test_monitoring.db"
        self.test_log_dir = "test_logs"
        self.monitoring = MonitoringSystem(self.test_db_path, self.test_log_dir)

    def tearDown(self):
        """Clean up test environment."""
        self.monitoring.stop()
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
        if os.path.exists(self.test_log_dir):
            for file in os.listdir(self.test_log_dir):
                os.remove(os.path.join(self.test_log_dir, file))
            os.rmdir(self.test_log_dir)

    def test_logging_setup(self):
        """Test logging configuration."""
        # Check if log directory exists
        self.assertTrue(os.path.exists(self.test_log_dir))
        
        # Check if category loggers exist
        for category in ['campaign_pool', 'request_generation', 
                        'impression_processing', 'click_processing', 'performance']:
            self.assertIn(category, self.monitoring.loggers)
            self.assertTrue(os.path.exists(
                os.path.join(self.test_log_dir, f'{category}.log')
            ))

    def test_log_event(self):
        """Test event logging."""
        # Log test events
        self.monitoring.log_event(
            'campaign_pool',
            'info',
            'Test campaign pool event',
            campaign_id='test123'
        )
        
        # Verify log file content
        log_file = os.path.join(self.test_log_dir, 'campaign_pool.log')
        with open(log_file, 'r') as f:
            content = f.read()
            self.assertIn('Test campaign pool event', content)
            self.assertIn('test123', content)

    def test_queue_metrics(self):
        """Test queue metrics tracking."""
        # Create test queue
        queue = Queue()
        queue.put('test_item')
        
        # Update metrics
        self.monitoring.update_queue_metrics('test_queue', queue, 0.5)
        
        # Get metrics
        metrics = self.monitoring.get_queue_metrics('test_queue')
        self.assertEqual(metrics['current_size'], 1)
        self.assertEqual(metrics['max_size'], 1)
        self.assertEqual(metrics['total_processed'], 1)
        self.assertGreater(metrics['avg_wait_time'], 0)

    def test_worker_metrics(self):
        """Test worker metrics tracking."""
        # Update metrics
        self.monitoring.update_worker_metrics(
            'test_pool',
            active_workers=5,
            task_time=0.1,
            total_tasks=10
        )
        
        # Get metrics
        metrics = self.monitoring.get_worker_metrics('test_pool')
        self.assertEqual(metrics['active_workers'], 5)
        self.assertEqual(metrics['total_tasks'], 10)
        self.assertGreater(metrics['avg_task_time'], 0)
        self.assertGreater(metrics['utilization'], 0)

    def test_performance_metrics(self):
        """Test performance metrics tracking."""
        # Update metrics
        self.monitoring.update_performance_metrics('test_category', {
            'response_time': 0.5,
            'success_rate': 0.95
        })
        
        # Get metrics
        metrics = self.monitoring.get_performance_metrics('test_category')
        self.assertEqual(metrics['response_time'], 0.5)
        self.assertEqual(metrics['success_rate'], 0.95)

    def test_database_operations(self):
        """Test database operations."""
        # Update various metrics
        self.monitoring.update_queue_metrics('test_queue', Queue(), 0.5)
        self.monitoring.update_worker_metrics('test_pool', 5, 0.1, 10)
        self.monitoring.update_performance_metrics('test_category', {
            'response_time': 0.5
        })
        
        # Verify database content
        with self.monitoring._get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check queue metrics
            cursor.execute("SELECT COUNT(*) FROM queue_metrics")
            self.assertGreater(cursor.fetchone()[0], 0)
            
            # Check worker metrics
            cursor.execute("SELECT COUNT(*) FROM worker_metrics")
            self.assertGreater(cursor.fetchone()[0], 0)
            
            # Check performance metrics
            cursor.execute("SELECT COUNT(*) FROM performance_metrics")
            self.assertGreater(cursor.fetchone()[0], 0)

    def test_thread_safety(self):
        """Test thread safety of metrics operations."""
        import threading
        
        def update_metrics():
            for _ in range(100):
                self.monitoring.update_queue_metrics('test_queue', Queue(), 0.5)
                self.monitoring.update_worker_metrics('test_pool', 5, 0.1, 10)
                self.monitoring.update_performance_metrics('test_category', {
                    'response_time': 0.5
                })
        
        # Create multiple threads
        threads = [
            threading.Thread(target=update_metrics)
            for _ in range(5)
        ]
        
        # Start threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify metrics
        queue_metrics = self.monitoring.get_queue_metrics('test_queue')
        self.assertEqual(queue_metrics['total_processed'], 500)  # 5 threads * 100 updates

    def test_error_handling(self):
        """Test error handling."""
        # Test invalid category
        self.monitoring.log_event(
            'invalid_category',
            'info',
            'Test message'
        )
        
        # Test invalid log level
        self.monitoring.log_event(
            'campaign_pool',
            'invalid_level',
            'Test message'
        )
        
        # Test database error
        os.remove(self.test_db_path)
        self.monitoring.update_queue_metrics('test_queue', Queue(), 0.5)
        
        # Verify system continues to function
        self.assertTrue(self.monitoring.running)

if __name__ == '__main__':
    unittest.main() 
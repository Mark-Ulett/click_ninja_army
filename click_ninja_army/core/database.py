"""
Database Interface for Click Ninja Army

This module provides a SQLite-based database interface for managing ad requests and operations.
It handles all database operations including CRUD operations, status updates, and operation logging.

Key Features:
- SQLite database management
- Request lifecycle tracking
- Operation logging
- Status management
- Error handling and logging

Example:
    >>> db = Database("click_ninja.db")
    >>> db.connect()
    >>> request_data = {
    ...     'request_id': 'req_123',
    ...     'campaign_id': 'camp_456',
    ...     'ad_item_id': 'item_789',
    ...     'ad_tag': 'tag_1',
    ...     'ad_type': 'Display',
    ...     'page_category_ids': [1019, 1007]
    ... }
    >>> db.save_ad_request(request_data)
"""

import logging
import sqlite3
from typing import Optional, List, Dict, Any
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class Database:
    """
    SQLite database interface for managing ad requests and operations.
    
    This class provides a high-level interface for:
    1. Managing database connections
    2. Handling ad request lifecycle
    3. Tracking operation history
    4. Managing request status
    5. Error handling and logging
    
    Attributes:
        db_path (str): Path to the SQLite database file
        _conn (sqlite3.Connection): Database connection object
    
    Example:
        >>> db = Database("click_ninja.db")
        >>> db.connect()
        >>> requests = db.get_pending_requests(limit=10)
    """
    
    def __init__(self, db_path: str = "click_ninja.db"):
        """
        Initialize the database interface.
        
        Args:
            db_path (str): Path to the SQLite database file. Defaults to "click_ninja.db".
        """
        logger.info(f"Initializing Database with path: {db_path}")
        self.db_path = db_path
        self._conn = None

    def connect(self):
        """
        Establish a connection to the SQLite database.
        
        This method:
        1. Creates a new connection if none exists
        2. Configures row factory for named column access
        3. Enables foreign key support
        4. Sets up required tables
        
        Example:
            >>> db = Database()
            >>> db.connect()
        """
        try:
            if not self._conn:
                logger.info(f"Connecting to database at {self.db_path}")
                self._conn = sqlite3.connect(self.db_path)
                self._conn.row_factory = sqlite3.Row
                self._setup_tables()
                logger.info("Database connection established successfully")
        except sqlite3.Error as e:
            logger.error(f"Failed to connect to database: {str(e)}")
            raise

    def _setup_tables(self):
        """
        Initialize all required database tables.
        
        This method creates:
        1. Request pool table for managing requests
        2. Operation log table for tracking operations
        3. Required indexes and constraints
        """
        try:
            logger.info("Setting up database tables")
            with self._conn.cursor() as cursor:
                # Request pool table
                logger.debug("Creating request_pool table")
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS request_pool (
                        id INTEGER PRIMARY KEY,
                        request_id TEXT UNIQUE NOT NULL,
                        campaign_id TEXT NOT NULL,
                        ad_item_id TEXT,
                        ad_tag TEXT NOT NULL,
                        ad_type TEXT NOT NULL,
                        page_category_ids TEXT,
                        status TEXT NOT NULL DEFAULT 'pending',
                        priority INTEGER DEFAULT 0,
                        retries INTEGER DEFAULT 0,
                        last_attempt TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        CONSTRAINT valid_status CHECK (status IN ('pending', 'in_progress', 'completed', 'failed'))
                    )
                """)
                logger.debug("Request pool table created/verified")
                
                # Operation log table
                logger.debug("Creating operation_log table")
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS operation_log (
                        id INTEGER PRIMARY KEY,
                        request_id TEXT NOT NULL,
                        operation_type TEXT NOT NULL,
                        status TEXT NOT NULL,
                        response_time FLOAT,
                        error_message TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (request_id) REFERENCES request_pool(request_id)
                    )
                """)
                logger.debug("Operation log table created/verified")
                
                # Create indexes
                logger.debug("Creating database indexes")
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_request_pool_status 
                    ON request_pool(status, priority)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_operation_log_request_id 
                    ON operation_log(request_id)
                """)
                
                self._conn.commit()
                logger.info("Database tables and indexes setup completed")
        except sqlite3.Error as e:
            logger.error(f"Failed to setup database tables: {str(e)}")
            raise

    def close(self):
        """
        Close the database connection.
        
        This method:
        1. Closes the active connection
        2. Clears the connection object
        3. Ensures proper resource cleanup
        
        Example:
            >>> db = Database()
            >>> db.connect()
            >>> # ... perform operations ...
            >>> db.close()
        """
        if self._conn:
            logger.info("Closing database connection")
            self._conn.close()
            self._conn = None
            logger.info("Database connection closed")

    def save_ad_request(self, request_data: Dict[str, Any]) -> bool:
        """
        Save a new ad request to the database.
        
        Args:
            request_data (Dict[str, Any]): Request data containing:
                - request_id (str): Unique request identifier
                - campaign_id (str): Campaign identifier
                - ad_item_id (str): Ad item identifier
                - ad_tag (str): Ad tag
                - ad_type (str): Type of ad
                - page_category_ids (List[int]): Category IDs
        
        Returns:
            bool: True if request was saved successfully
        
        Example:
            >>> request_data = {
            ...     'request_id': 'req_123',
            ...     'campaign_id': 'camp_456',
            ...     'ad_item_id': 'item_789',
            ...     'ad_tag': 'tag_1',
            ...     'ad_type': 'Display',
            ...     'page_category_ids': [1019, 1007]
            ... }
            >>> db.save_ad_request(request_data)
        """
        try:
            logger.info(f"Saving ad request: {request_data['request_id']}")
            with self._conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO request_pool (
                        request_id, campaign_id, ad_item_id, ad_tag,
                        ad_type, page_category_ids
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    request_data['request_id'],
                    request_data['campaign_id'],
                    request_data.get('ad_item_id'),
                    request_data['ad_tag'],
                    request_data['ad_type'],
                    json.dumps(request_data.get('page_category_ids', []))
                ))
                self._conn.commit()
                logger.info(f"Successfully saved ad request: {request_data['request_id']}")
                return True
        except Exception as e:
            logger.error(f"Error saving ad request {request_data.get('request_id', 'unknown')}: {str(e)}")
            return False

    def get_pending_requests(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get a list of pending requests.
        
        Args:
            limit (int): Maximum number of requests to return
        
        Returns:
            List[Dict[str, Any]]: List of pending requests
        
        Example:
            >>> requests = db.get_pending_requests(limit=10)
        """
        try:
            logger.info(f"Fetching up to {limit} pending requests")
            with self._conn.cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM request_pool
                    WHERE status = 'pending'
                    ORDER BY priority DESC, created_at ASC
                    LIMIT ?
                """, (limit,))
                results = [dict(row) for row in cursor.fetchall()]
                logger.info(f"Found {len(results)} pending requests")
                if len(results) > 0:
                    logger.debug(f"First request ID: {results[0].get('request_id')}")
                return results
        except Exception as e:
            logger.error(f"Error getting pending requests: {str(e)}")
            return []

    def update_request_status(self, request_id: str, status: str) -> bool:
        """
        Update the status of a request.
        
        Args:
            request_id (str): ID of the request to update
            status (str): New status ('pending', 'in_progress', 'completed', 'failed')
        
        Returns:
            bool: True if status was updated successfully
        
        Example:
            >>> db.update_request_status('req_123', 'completed')
        """
        try:
            logger.info(f"Updating request {request_id} status to {status}")
            with self._conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE request_pool
                    SET status = ?, last_attempt = CURRENT_TIMESTAMP
                    WHERE request_id = ?
                """, (status, request_id))
                rows_affected = cursor.rowcount
                self._conn.commit()
                if rows_affected > 0:
                    logger.info(f"Successfully updated request {request_id} status to {status}")
                else:
                    logger.warning(f"No request found with ID {request_id}")
                return rows_affected > 0
        except Exception as e:
            logger.error(f"Error updating request {request_id} status: {str(e)}")
            return False

    def log_operation(self, request_id: str, operation_type: str, status: str,
                     response_time: Optional[float] = None,
                     error_message: Optional[str] = None) -> bool:
        """
        Log an operation to the database.
        
        Args:
            request_id (str): ID of the request
            operation_type (str): Type of operation performed
            status (str): Operation status
            response_time (Optional[float]): Response time in seconds
            error_message (Optional[str]): Error message if operation failed
        
        Returns:
            bool: True if operation was logged successfully
        
        Example:
            >>> db.log_operation(
            ...     request_id='req_123',
            ...     operation_type='click',
            ...     status='success',
            ...     response_time=0.5
            ... )
        """
        try:
            logger.info(f"Logging {operation_type} operation for request {request_id}")
            with self._conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO operation_log (
                        request_id, operation_type, status,
                        response_time, error_message
                    ) VALUES (?, ?, ?, ?, ?)
                """, (request_id, operation_type, status, response_time, error_message))
                self._conn.commit()
                logger.info(f"Successfully logged operation for request {request_id}")
                return True
        except Exception as e:
            logger.error(f"Error logging operation for request {request_id}: {str(e)}")
            return False 
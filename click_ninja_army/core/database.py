"""
Database Interface for Click Ninja Army

This module provides a SQLite-based database interface for managing ad requests, campaign pool entries, and operations.
It handles all database operations including CRUD operations, status updates, operation logging, and metrics tracking.

Key Features:
- SQLite database management
- Campaign pool and request pool lifecycle tracking
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
    
    def __init__(self, db_path: str):
        """
        Initialize the database interface.
        
        Args:
            db_path (str): Path to the SQLite database file
        """
        self.db_path = db_path
        self._conn = None
        self.connect()
        self._setup_tables()
        logger.debug(f"Database initialized with path: {db_path}")

    def _validate_ad_request_id(self, ad_request_id: str) -> bool:
        """
        Validate that the adRequestId contains the required suffix format.
        
        Args:
            ad_request_id (str): The adRequestId to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        if not ad_request_id or '/' not in ad_request_id:
            logger.error(f"Invalid adRequestId format: {ad_request_id}. Must contain '/' and suffix.")
            return False
        return True

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
            cursor = self._conn.cursor()
            logger.info("Setting up database tables")
            # Request pool table
            logger.debug("Creating request_pool table")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS request_pool (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ad_request_id TEXT UNIQUE,
                    ad_tag TEXT,
                    ad_item_id TEXT,
                    creative_id INTEGER,
                    campaign_id TEXT,
                    ad_type TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
                ON request_pool(status)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_campaign_pool_ad_item
                ON campaign_pool(ad_item_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_campaign_pool_campaign
                ON campaign_pool(campaign_id)
            """)
            
            # Campaign Pool table
            logger.debug("Creating campaign_pool table")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS campaign_pool (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ad_tag TEXT,
                    ad_item_id TEXT,
                    creative_id INTEGER,
                    campaign_id TEXT,
                    ad_type TEXT,
                    keyword TEXT,
                    category TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Request Pool table
            logger.debug("Creating request_pool table")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS request_pool (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    campaign_pool_id INTEGER NOT NULL,
                    ad_request_id TEXT NOT NULL,
                    request_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'pending',
                    FOREIGN KEY (campaign_pool_id) REFERENCES campaign_pool(id),
                    UNIQUE(ad_request_id)
                )
            ''')
            
            # Metrics table for campaign pool generation
            logger.debug("Creating campaign_pool_metrics table")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS campaign_pool_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    csv_rows_processed INTEGER NOT NULL,
                    campaign_pool_rows_generated INTEGER NOT NULL,
                    generation_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    duration_seconds REAL,
                    status TEXT DEFAULT 'completed'
                )
            ''')
            
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
                - campaign_id (str): Campaign identifier
                - ad_item_id (str): Ad item identifier
                - ad_tag (str): Ad tag
                - ad_type (str): Type of ad
                - creative_id (int): Creative identifier
                - page_category_ids (List[int]): Category IDs
        Returns:
            bool: True if request was saved successfully
        """
        try:
            # Ensure all required fields are present
            required_fields = ['campaign_id', 'ad_item_id', 'ad_tag', 'ad_type', 'creative_id']
            for field in required_fields:
                if field not in request_data:
                    logger.error(f"Missing required field: {field}")
                    return False
            
            # Convert page_category_ids to JSON string
            page_category_ids = json.dumps(request_data.get('page_category_ids', []))
            
            cursor = self._conn.cursor()
            cursor.execute("""
                INSERT INTO request_pool (
                    campaign_id,
                    ad_item_id,
                    ad_tag,
                    ad_type,
                    creative_id,
                    page_category_ids,
                    status,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'pending', CURRENT_TIMESTAMP)
            """, (
                request_data['campaign_id'],
                request_data['ad_item_id'],
                request_data['ad_tag'],
                request_data['ad_type'],
                request_data['creative_id'],
                page_category_ids
            ))
            
            self._conn.commit()
            logger.info(f"Saved ad request for campaign {request_data['campaign_id']}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving ad request: {str(e)}")
            return False

    def get_pending_requests(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get a list of pending requests.
        Args:
            limit (int): Maximum number of requests to return
        Returns:
            List[Dict[str, Any]]: List of pending requests, each including creative_id
        """
        try:
            logger.info(f"Fetching up to {limit} pending requests")
            cursor = self._conn.cursor()
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
            # Ensure creative_id is int or None
            for r in results:
                if 'creative_id' in r and r['creative_id'] is not None:
                    r['creative_id'] = int(r['creative_id'])
            return results
        except Exception as e:
            logger.error(f"Error getting pending requests: {str(e)}")
            return []

    def update_request_status(self, request_id: str, status: str) -> bool:
        """
        Update the status of a request in the database.
        
        Args:
            request_id (str): Request identifier (must include suffix)
            status (str): New status
        
        Returns:
            bool: True if status was updated successfully
        """
        try:
            # Validate request_id
            if not request_id or not self._validate_ad_request_id(request_id):
                logger.error(f"Invalid request_id format: {request_id}")
                return False

            logger.info(f"Updating status for request {request_id} to {status}")
            cursor = self._conn.cursor()
            cursor.execute("""
                UPDATE request_pool
                SET status = ?, updated_at = ?
                WHERE request_id = ?
            """, (
                status,
                datetime.now().isoformat(),
                request_id
            ))
            self._conn.commit()
            logger.info(f"Successfully updated status for request {request_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating status for request {request_id}: {str(e)}")
            return False

    def log_operation(self, request_id: str, operation_type: str, status: str,
                     response_time: Optional[float] = None,
                     error_message: Optional[str] = None) -> bool:
        """
        Log an operation to the database.
        
        Args:
            request_id (str): Request identifier (must include suffix)
            operation_type (str): Type of operation
            status (str): Operation status
            response_time (float): Response time in seconds
            error_message (str): Error message if operation failed
        
        Returns:
            bool: True if operation was logged successfully
        """
        try:
            # Validate request_id
            if not request_id or not self._validate_ad_request_id(request_id):
                logger.error(f"Invalid request_id format: {request_id}")
                return False

            logger.info(f"Logging {operation_type} operation for request {request_id}")
            cursor = self._conn.cursor()
            cursor.execute("""
                INSERT INTO operation_log (
                    request_id, operation_type, status,
                    response_time, error_message, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                request_id,
                operation_type,
                status,
                response_time,
                error_message,
                datetime.now().isoformat()
            ))
            self._conn.commit()
            logger.info(f"Successfully logged {operation_type} operation for request {request_id}")
            return True
        except Exception as e:
            logger.error(f"Error logging operation for request {request_id}: {str(e)}")
            return False

    def update_ad_request_id(self, request_id: str, ad_request_id: str) -> bool:
        """
        Update the ad_request_id (adRequestId) for a given request in the database.
        Args:
            request_id (str): The local UUID for the request row
            ad_request_id (str): The backend-generated adRequestId (with suffix)
        Returns:
            bool: True if updated successfully, False otherwise
        """
        try:
            logger.info(f"Updating ad_request_id for request {request_id} to {ad_request_id}")
            cursor = self._conn.cursor()
            cursor.execute("""
                UPDATE request_pool
                SET ad_request_id = ?
                WHERE request_id = ?
            """, (ad_request_id, request_id))
            self._conn.commit()
            logger.info(f"Successfully updated ad_request_id for request {request_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating ad_request_id for request {request_id}: {str(e)}")
            return False

    def insert_campaign_pool_entry(self, entry: Dict[str, Any]) -> int:
        """
        Insert a single campaign pool entry.
        
        Args:
            entry: Dictionary containing campaign pool entry data
                  Required fields: ad_tag, ad_item_id, creative_id, campaign_id, ad_type
                  Optional fields: keyword, category
        
        Returns:
            int: ID of the inserted row
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO campaign_pool (
                        ad_tag, ad_item_id, creative_id, campaign_id, 
                        ad_type, keyword, category
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    entry['ad_tag'],
                    entry['ad_item_id'],
                    entry['creative_id'],
                    entry['campaign_id'],
                    entry['ad_type'],
                    entry.get('keyword'),
                    entry.get('category')
                ))
                conn.commit()
                return cursor.lastrowid
        except sqlite3.IntegrityError as e:
            logger.warning(f"Duplicate entry skipped: {entry}")
            return -1
        except Exception as e:
            logger.error(f"Error inserting campaign pool entry: {e}")
            raise

    def log_campaign_pool_metrics(self, rows_processed: int, rows_generated: int):
        """
        Log metrics about campaign pool generation.
        
        Args:
            rows_processed: Number of CSV rows processed
            rows_generated: Number of campaign pool entries generated
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO campaign_pool_metrics (
                        csv_rows_processed, campaign_pool_rows_generated
                    ) VALUES (?, ?)
                """, (rows_processed, rows_generated))
                conn.commit()
        except Exception as e:
            logger.error(f"Error logging campaign pool metrics: {e}")
            raise

    def log_request_pool_metrics(self, requests_generated: int):
        """
        Log metrics about request pool generation.
        
        Args:
            requests_generated: Number of requests generated
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO request_pool_metrics (
                        requests_generated
                    ) VALUES (?)
                """, (requests_generated,))
                conn.commit()
        except Exception as e:
            logger.error(f"Error logging request pool metrics: {e}")
            raise

    def get_campaign_pool_entries(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Retrieve campaign pool entries for processing.
        
        Args:
            limit: Maximum number of entries to retrieve
        
        Returns:
            List of campaign pool entries
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM campaign_pool 
                    ORDER BY created_at ASC 
                    LIMIT ?
                """, (limit,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error retrieving campaign pool entries: {e}")
            raise

    def insert_request_pool_entry(self, campaign_pool_id: int, ad_request_id: str) -> bool:
        """
        Insert a request pool entry with the API-generated adRequestId.
        
        Args:
            campaign_pool_id: ID from campaign_pool table
            ad_request_id: API-generated adRequestId (must include suffix)
        
        Returns:
            bool: True if insertion was successful
        """
        try:
            # Validate adRequestId format
            if not self._validate_ad_request_id(ad_request_id):
                logger.error(f"Invalid adRequestId format: {ad_request_id}")
                return False

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO request_pool (
                        campaign_pool_id, ad_request_id, status
                    ) VALUES (?, ?, 'pending')
                """, (campaign_pool_id, ad_request_id))
                conn.commit()
                
                # Log metrics
                self.log_request_pool_metrics(1)
                
                logger.info(f"Inserted request pool entry for adRequestId: {ad_request_id}")
                return True
        except sqlite3.IntegrityError as e:
            logger.warning(f"Duplicate adRequestId skipped: {ad_request_id}")
            return False
        except Exception as e:
            logger.error(f"Error inserting request pool entry: {e}")
            return False 
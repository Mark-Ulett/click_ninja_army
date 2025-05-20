"""
Database Migration - Schema updates and data migration

This module handles database schema updates and data migration for the Click Ninja Army system.
It ensures smooth transitions between database versions while preserving existing data.

Key Features:
- Schema version tracking
- Safe table creation
- Data migration
- Foreign key constraint management
- Index optimization

Example:
    >>> migration = DatabaseMigration("click_ninja.db")
    >>> migration.migrate()
"""

import logging
import sqlite3
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class DatabaseMigration:
    """
    Handles database schema updates and data migration.
    
    This class manages:
    1. Schema version tracking
    2. Safe table creation
    3. Data migration
    4. Foreign key constraint management
    5. Index optimization
    """

    def __init__(self, db_path: str):
        """
        Initialize the database migration manager.
        
        Args:
            db_path: Path to the SQLite database
        """
        self.db_path = db_path
        self._setup_version_table()

    def _setup_version_table(self):
        """Set up schema version tracking table."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS schema_version (
                        version INTEGER PRIMARY KEY,
                        applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        description TEXT
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.error(f"Error setting up version table: {str(e)}")
            raise

    def get_current_version(self) -> int:
        """Get current schema version."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT MAX(version) FROM schema_version")
                result = cursor.fetchone()
                return result[0] if result[0] is not None else 0
        except Exception as e:
            logger.error(f"Error getting current version: {str(e)}")
            return 0

    def _create_campaign_pool_table(self, cursor: sqlite3.Cursor):
        """Create campaign pool table with new schema."""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS campaign_pool (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ad_tag TEXT NOT NULL,
                ad_item_id TEXT NOT NULL,
                creative_id INTEGER NOT NULL,
                campaign_id TEXT NOT NULL,
                ad_type TEXT NOT NULL,
                keyword TEXT,
                category TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(ad_tag, ad_item_id, creative_id, campaign_id, ad_type, keyword, category)
            )
        """)
        
        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_campaign_pool_ad_item 
            ON campaign_pool(ad_item_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_campaign_pool_campaign 
            ON campaign_pool(campaign_id)
        """)

    def _create_request_pool_table(self, cursor: sqlite3.Cursor):
        """Create request pool table with new schema."""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS request_pool (
                id INTEGER PRIMARY KEY,
                campaign_pool_id INTEGER NOT NULL,
                ad_request_id TEXT NOT NULL UNIQUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'pending',
                FOREIGN KEY (campaign_pool_id) REFERENCES campaign_pool(id)
            )
        """)
        
        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_request_pool_ad_request 
            ON request_pool(ad_request_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_request_pool_campaign 
            ON request_pool(campaign_pool_id)
        """)

    def _migrate_existing_data(self, cursor: sqlite3.Cursor):
        """Migrate existing data to new schema."""
        try:
            # Check if old tables exist
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='campaign_pool_old'
            """)
            if cursor.fetchone():
                # Migrate campaign pool data with type conversion
                cursor.execute("""
                    INSERT INTO campaign_pool (
                        ad_tag, ad_item_id, creative_id, campaign_id, ad_type,
                        keyword, category, created_at
                    )
                    SELECT 
                        ad_tag,
                        CAST(ad_item_id AS INTEGER),
                        CAST(creative_id AS INTEGER),
                        CAST(campaign_id AS INTEGER),
                        ad_type,
                        keyword,
                        CAST(category AS INTEGER),
                        created_at
                    FROM campaign_pool_old
                    WHERE ad_item_id IS NOT NULL 
                    AND creative_id IS NOT NULL 
                    AND campaign_id IS NOT NULL
                """)
                
                # Migrate request pool data
                cursor.execute("""
                    INSERT INTO request_pool (
                        campaign_pool_id, ad_request_id, created_at, status
                    )
                    SELECT 
                        cp.id, rp.ad_request_id, rp.created_at, 'pending'
                    FROM request_pool_old rp
                    JOIN campaign_pool_old cpo ON rp.campaign_pool_id = cpo.id
                    JOIN campaign_pool cp ON 
                        cp.ad_tag = cpo.ad_tag AND
                        cp.ad_item_id = CAST(cpo.ad_item_id AS INTEGER) AND
                        cp.creative_id = CAST(cpo.creative_id AS INTEGER) AND
                        cp.campaign_id = CAST(cpo.campaign_id AS INTEGER) AND
                        cp.ad_type = cpo.ad_type
                """)
                
                logger.info("Successfully migrated existing data")
        except Exception as e:
            logger.error(f"Error migrating data: {str(e)}")
            raise

    def _backup_existing_tables(self, cursor: sqlite3.Cursor):
        """Backup existing tables before migration."""
        try:
            # Check if tables exist before backing up
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name IN ('campaign_pool', 'request_pool')
            """)
            existing_tables = [row[0] for row in cursor.fetchall()]
            
            for table in existing_tables:
                cursor.execute(f"""
                    ALTER TABLE {table}
                    RENAME TO {table}_old
                """)
                logger.info(f"Backed up {table} to {table}_old")
        except Exception as e:
            logger.error(f"Error backing up tables: {str(e)}")
            raise

    def _update_version(self, cursor: sqlite3.Cursor, version: int, description: str):
        """Update schema version."""
        cursor.execute("""
            INSERT INTO schema_version (version, description)
            VALUES (?, ?)
        """, (version, description))

    def migrate(self):
        """Perform database migration."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Start transaction
                cursor.execute("BEGIN TRANSACTION")
                
                try:
                    # Backup existing tables
                    self._backup_existing_tables(cursor)
                    
                    # Create new tables
                    self._create_campaign_pool_table(cursor)
                    self._create_request_pool_table(cursor)
                    
                    # Migrate data
                    self._migrate_existing_data(cursor)
                    
                    # Update version
                    self._update_version(cursor, 1, "Initial migration with new schema")
                    
                    # Commit transaction
                    conn.commit()
                    logger.info("Database migration completed successfully")
                    
                except Exception as e:
                    # Rollback on error
                    conn.rollback()
                    logger.error(f"Migration failed: {str(e)}")
                    raise
                
        except Exception as e:
            logger.error(f"Error during migration: {str(e)}")
            raise

    def verify_migration(self) -> bool:
        """Verify migration success."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if new tables exist
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name IN ('campaign_pool', 'request_pool')
                """)
                tables = cursor.fetchall()
                if len(tables) != 2:
                    return False
                
                # Check if data was migrated
                cursor.execute("SELECT COUNT(*) FROM campaign_pool")
                campaign_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM request_pool")
                request_count = cursor.fetchone()[0]
                
                return campaign_count > 0 and request_count > 0
                
        except Exception as e:
            logger.error(f"Error verifying migration: {str(e)}")
            return False

if __name__ == "__main__":
    migration = DatabaseMigration("click_ninja.db")
    migration.migrate() 
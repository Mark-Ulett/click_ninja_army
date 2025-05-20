"""
Test cases for database migration functionality.

This module contains tests to verify:
1. Schema version tracking
2. Table creation
3. Data migration
4. Foreign key constraints
5. Index creation
"""

import unittest
import os
import sqlite3
from datetime import datetime
from ..core.database_migration import DatabaseMigration

class TestDatabaseMigration(unittest.TestCase):
    """Test cases for database migration."""

    def setUp(self):
        """Set up test environment."""
        self.test_db_path = "test_migration.db"
        self.migration = DatabaseMigration(self.test_db_path)

    def tearDown(self):
        """Clean up test environment."""
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

    def test_initial_version(self):
        """Test initial schema version."""
        version = self.migration.get_current_version()
        self.assertEqual(version, 0)

    def test_version_table_creation(self):
        """Test schema version table creation."""
        with sqlite3.connect(self.test_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'")
            result = cursor.fetchone()
            self.assertIsNotNone(result)

    def test_table_creation(self):
        """Test creation of new tables."""
        self.migration.migrate()
        
        with sqlite3.connect(self.test_db_path) as conn:
            cursor = conn.cursor()
            
            # Check campaign_pool table
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='campaign_pool'
            """)
            self.assertIsNotNone(cursor.fetchone())
            
            # Check request_pool table
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='request_pool'
            """)
            self.assertIsNotNone(cursor.fetchone())

    def test_index_creation(self):
        """Test creation of indexes."""
        self.migration.migrate()
        
        with sqlite3.connect(self.test_db_path) as conn:
            cursor = conn.cursor()
            
            # Check campaign_pool indexes
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='index' AND name='idx_campaign_pool_ad_item'
            """)
            self.assertIsNotNone(cursor.fetchone())
            
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='index' AND name='idx_campaign_pool_campaign'
            """)
            self.assertIsNotNone(cursor.fetchone())
            
            # Check request_pool indexes
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='index' AND name='idx_request_pool_ad_request'
            """)
            self.assertIsNotNone(cursor.fetchone())
            
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='index' AND name='idx_request_pool_campaign'
            """)
            self.assertIsNotNone(cursor.fetchone())

    def test_data_migration(self):
        """Test migration of existing data."""
        # Create old tables with test data
        with sqlite3.connect(self.test_db_path) as conn:
            cursor = conn.cursor()
            
            # Create old campaign_pool table
            cursor.execute("""
                CREATE TABLE campaign_pool (
                    id INTEGER PRIMARY KEY,
                    ad_tag TEXT NOT NULL,
                    ad_item_id TEXT NOT NULL,
                    creative_id TEXT NOT NULL,
                    campaign_id TEXT NOT NULL,
                    ad_type TEXT NOT NULL,
                    keyword_or_category TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create old request_pool table
            cursor.execute("""
                CREATE TABLE request_pool (
                    id INTEGER PRIMARY KEY,
                    campaign_pool_id INTEGER NOT NULL,
                    ad_request_id TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Insert test data
            cursor.execute("""
                INSERT INTO campaign_pool (
                    ad_tag, ad_item_id, creative_id, campaign_id, ad_type,
                    keyword_or_category, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                'test_tag', 'test_item', 'test_creative', 'test_campaign',
                'test_type', 'test_keyword', datetime.now().isoformat()
            ))
            
            campaign_id = cursor.lastrowid
            
            cursor.execute("""
                INSERT INTO request_pool (
                    campaign_pool_id, ad_request_id, created_at
                ) VALUES (?, ?, ?)
            """, (
                campaign_id, 'test_request', datetime.now().isoformat()
            ))
            
            conn.commit()
        
        # Perform migration
        self.migration.migrate()
        
        # Verify migrated data
        with sqlite3.connect(self.test_db_path) as conn:
            cursor = conn.cursor()
            
            # Check campaign_pool data
            cursor.execute("SELECT COUNT(*) FROM campaign_pool")
            self.assertEqual(cursor.fetchone()[0], 1)
            
            cursor.execute("""
                SELECT ad_tag, ad_item_id, creative_id, campaign_id, ad_type,
                       keyword, category
                FROM campaign_pool
            """)
            row = cursor.fetchone()
            self.assertEqual(row[0], 'test_tag')
            self.assertEqual(row[1], 'test_item')
            self.assertEqual(row[2], 'test_creative')
            self.assertEqual(row[3], 'test_campaign')
            self.assertEqual(row[4], 'test_type')
            self.assertEqual(row[5], 'test_keyword')
            self.assertIsNone(row[6])
            
            # Check request_pool data
            cursor.execute("SELECT COUNT(*) FROM request_pool")
            self.assertEqual(cursor.fetchone()[0], 1)
            
            cursor.execute("""
                SELECT ad_request_id, status
                FROM request_pool
            """)
            row = cursor.fetchone()
            self.assertEqual(row[0], 'test_request')
            self.assertEqual(row[1], 'pending')

    def test_foreign_key_constraints(self):
        """Test foreign key constraints."""
        self.migration.migrate()
        
        with sqlite3.connect(self.test_db_path) as conn:
            cursor = conn.cursor()
            
            # Try to insert request with non-existent campaign_pool_id
            with self.assertRaises(sqlite3.IntegrityError):
                cursor.execute("""
                    INSERT INTO request_pool (
                        campaign_pool_id, ad_request_id
                    ) VALUES (?, ?)
                """, (999, 'test_request'))
                
                conn.commit()

    def test_unique_constraints(self):
        """Test unique constraints."""
        self.migration.migrate()
        
        with sqlite3.connect(self.test_db_path) as conn:
            cursor = conn.cursor()
            
            # Insert first campaign
            cursor.execute("""
                INSERT INTO campaign_pool (
                    ad_tag, ad_item_id, creative_id, campaign_id, ad_type,
                    keyword, category
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                'test_tag', 'test_item', 'test_creative', 'test_campaign',
                'test_type', 'test_keyword', None
            ))
            
            # Try to insert duplicate campaign
            with self.assertRaises(sqlite3.IntegrityError):
                cursor.execute("""
                    INSERT INTO campaign_pool (
                        ad_tag, ad_item_id, creative_id, campaign_id, ad_type,
                        keyword, category
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    'test_tag', 'test_item', 'test_creative', 'test_campaign',
                    'test_type', 'test_keyword', None
                ))
                
                conn.commit()

    def test_migration_verification(self):
        """Test migration verification."""
        # Perform migration
        self.migration.migrate()
        
        # Verify migration
        self.assertTrue(self.migration.verify_migration())

if __name__ == '__main__':
    unittest.main() 
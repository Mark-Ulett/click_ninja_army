import sqlite3
from click_ninja_army.core.database_migration import DatabaseMigration
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_test_data():
    """Create test data in the old schema format."""
    with sqlite3.connect('test_click_ninja.db') as conn:
        cursor = conn.cursor()
        
        # Create old campaign_pool table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS campaign_pool (
                id INTEGER PRIMARY KEY,
                ad_tag TEXT NOT NULL,
                ad_item_id TEXT NOT NULL,
                creative_id TEXT NOT NULL,
                campaign_id TEXT NOT NULL,
                ad_type TEXT NOT NULL,
                keyword TEXT,
                category TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create old request_pool table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS request_pool (
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
                keyword, category
            ) VALUES 
            ('test_tag_1', '123', '456', '789', 'Display', 'keyword1', '101'),
            ('test_tag_2', '234', '567', '890', 'Video', 'keyword2', '102')
        """)
        
        campaign_ids = cursor.lastrowid - 1, cursor.lastrowid
        
        cursor.execute("""
            INSERT INTO request_pool (
                campaign_pool_id, ad_request_id
            ) VALUES 
            (?, 'req_123/abc'),
            (?, 'req_456/def')
        """, campaign_ids)
        
        conn.commit()
        logger.info("Test data created successfully")

def verify_migration():
    """Verify the migration results."""
    with sqlite3.connect('test_click_ninja.db') as conn:
        cursor = conn.cursor()
        
        # Check campaign_pool table structure
        cursor.execute("PRAGMA table_info(campaign_pool)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        
        # Verify column types
        assert columns['ad_item_id'] == 'INTEGER', "ad_item_id should be INTEGER"
        assert columns['creative_id'] == 'INTEGER', "creative_id should be INTEGER"
        assert columns['campaign_id'] == 'INTEGER', "campaign_id should be INTEGER"
        assert columns['category'] == 'INTEGER', "category should be INTEGER"
        
        # Check data conversion
        cursor.execute("SELECT * FROM campaign_pool")
        rows = cursor.fetchall()
        assert len(rows) == 2, "Should have 2 rows in campaign_pool"
        
        for row in rows:
            assert isinstance(row[2], int), "ad_item_id should be integer"
            assert isinstance(row[3], int), "creative_id should be integer"
            assert isinstance(row[4], int), "campaign_id should be integer"
            if row[7]:  # category
                assert isinstance(row[7], int), "category should be integer"
        
        # Check request_pool data
        cursor.execute("SELECT COUNT(*) FROM request_pool")
        assert cursor.fetchone()[0] == 2, "Should have 2 rows in request_pool"
        
        logger.info("Migration verification successful!")

def main():
    try:
        # Setup test data
        setup_test_data()
        
        # Run migration
        migration = DatabaseMigration('test_click_ninja.db')
        migration.migrate()
        
        # Verify results
        verify_migration()
        
        logger.info("Test migration completed successfully!")
        
    except Exception as e:
        logger.error(f"Test migration failed: {str(e)}")
        raise

if __name__ == "__main__":
    main() 
"""
Run Strike Ninja with proper configuration and database setup.
"""

import logging
import sqlite3
from click_ninja_army.config.config import config
from click_ninja_army.core.strike_ninja import StrikeNinja, OperationConfig, WorkerPoolConfig
from click_ninja_army.core.metrics import MetricsManager
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    # Initialize database connection
    db = sqlite3.connect(config.db_path)
    
    # Initialize metrics manager with database path
    metrics_manager = MetricsManager(config.db_path)
    
    # Configure Strike Ninja
    operation_config = OperationConfig(
        impression_url=config.api.ad_server_impressions_url,
        click_url=config.api.ad_server_clicks_url,
        api_token=config.api.auth_token,
        impression_rate_limit=config.rate_limit,
        click_rate_limit=config.rate_limit,
        impression_burst=config.burst_limit,
        click_burst=config.burst_limit,
        max_retries=3,
        retry_delay=1.0,
        timeout=config.request_timeout
    )
    
    # Initialize Strike Ninja
    strike_ninja = StrikeNinja(operation_config, db, metrics_manager)
    
    try:
        # Start processing
        logger.info("Starting Strike Ninja...")
        strike_ninja.start()
        
        # Get pending requests from request_pool
        cursor = db.cursor()
        cursor.execute("""
            SELECT id, request_id, campaign_id, ad_item_id, ad_tag, ad_type, page_category_ids
            FROM request_pool 
            WHERE status = 'pending' AND request_id IS NOT NULL AND request_id != ''
            ORDER BY priority DESC, created_at ASC
            LIMIT 1000
        """)
        pending_requests = cursor.fetchall()
        
        if not pending_requests:
            logger.info("No pending requests found")
            return
        
        logger.info(f"Processing {len(pending_requests)} pending requests")
        
        # Queue requests for processing
        for request in pending_requests:
            entry = {
                'id': request[0],
                'request_id': request[1],
                'campaign_id': request[2],
                'ad_item_id': request[3],
                'ad_tag': request[4],
                'ad_type': request[5],
                'page_category_ids': request[6]
            }
            strike_ninja.queue_impression(entry)
        
        # Wait for processing to complete
        while True:
            cursor.execute("SELECT COUNT(*) FROM request_pool WHERE status = 'pending'")
            pending_count = cursor.fetchone()[0]
            if pending_count == 0:
                break
            logger.info(f"Still processing... {pending_count} requests remaining")
            time.sleep(5)
            
    except KeyboardInterrupt:
        logger.info("Stopping Strike Ninja...")
    finally:
        strike_ninja.stop()
        db.close()

if __name__ == "__main__":
    main() 
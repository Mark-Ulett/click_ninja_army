#!/usr/bin/env python3
"""
ScoutNinja Runner Script

This script provides a command-line interface to test and run the ScoutNinja module.
It allows for testing individual components and the full workflow of the ScoutNinja system.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

from click_ninja_army.core.scout_ninja import ScoutNinja, RequestConfig
from click_ninja_army.core.database import Database
from click_ninja_army.core.metrics import MetricsManager
from click_ninja_army.config.config import config as global_config
# Attempt to import config and logger from the most likely locations
try:
    from click_ninja_army.config.scout_ninja_config import ScoutNinjaConfig
except ImportError:
    ScoutNinjaConfig = None  # Placeholder if not found
try:
    from click_ninja_army.core.logger import setup_logger
except ImportError:
    def setup_logger(level):
        import logging
        logging.basicConfig(level=getattr(logging, level))

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='ScoutNinja Runner')
    
    # Input file argument
    parser.add_argument(
        '--input-file',
        type=str,
        help='Path to the input CSV file containing request data'
    )
    
    # Component testing arguments
    parser.add_argument(
        '--test-parser',
        action='store_true',
        help='Test the CSV parser component'
    )
    
    parser.add_argument(
        '--test-validator',
        action='store_true',
        help='Test the request validator component'
    )
    
    parser.add_argument(
        '--test-processor',
        action='store_true',
        help='Test the request processor component'
    )
    
    # Configuration arguments
    parser.add_argument(
        '--config-file',
        type=str,
        help='Path to the configuration file (default: config/scout_ninja_config.yaml)'
    )
    
    parser.add_argument(
        '--log-level',
        type=str,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default='INFO',
        help='Set the logging level'
    )
    
    return parser.parse_args()

def run_component_test(scout_ninja: ScoutNinja, component: str, input_file: Optional[str] = None):
    """Run a specific component test."""
    if not input_file:
        print(f"Error: Input file required for testing {component}")
        return
    
    try:
        if component == 'parser':
            print("\nTesting CSV Parser...")
            requests = scout_ninja.parse_csv(input_file)
            print(f"Successfully parsed {len(requests)} requests")
            
        elif component == 'validator':
            print("\nTesting Request Validator...")
            requests = scout_ninja.parse_csv(input_file)
            valid_requests = scout_ninja.validate_requests(requests)
            print(f"Validated {len(valid_requests)} requests")
            
        elif component == 'processor':
            print("\nTesting Request Processor...")
            requests = scout_ninja.parse_csv(input_file)
            valid_requests = scout_ninja.validate_requests(requests)
            processed_requests = scout_ninja.process_requests(valid_requests)
            print(f"Processed {len(processed_requests)} requests")
            
    except Exception as e:
        print(f"Error testing {component}: {str(e)}")
        raise

def main():
    """Main entry point for the ScoutNinja runner."""
    args = parse_args()
    
    # Setup logging
    setup_logger(level=args.log_level)
    logger = logging.getLogger(__name__)
    
    try:
        # Build RequestConfig from global_config
        request_config = RequestConfig(
            api_url=global_config.api.ad_server_url,
            api_token=global_config.api.auth_token,
            rate_limit=global_config.rate_limit,
            burst_limit=global_config.burst_limit,
            timeout=global_config.api.request_timeout
        )
        db = Database(global_config.db_path)
        metrics_manager = MetricsManager(global_config.db_path)
        scout_ninja = ScoutNinja(request_config, db, metrics_manager)

        # Run full workflow (no component tests implemented in this version)
        print("\nRunning full ScoutNinja workflow...")
        entries = db.get_campaign_pool_entries(limit=1000)
        if not entries:
            print("No campaign pool entries found. Please ingest a campaign CSV first.")
            sys.exit(1)
        scout_ninja.start()
        scout_ninja.generate_requests(entries)
        # Wait for all requests to be processed
        import time
        while True:
            stats = scout_ninja.get_stats()
            print(f"Requests generated: {stats['requests_generated']}")
            if stats['requests_generated'] >= len(entries):
                break
            time.sleep(2)
        scout_ninja.stop()
        print("ScoutNinja workflow complete.")
        
    except Exception as e:
        logger.error(f"Error running ScoutNinja: {str(e)}")
        raise

if __name__ == '__main__':
    main() 
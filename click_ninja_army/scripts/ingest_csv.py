"""
CSV Ingestion Script

This script processes CSV files and generates campaign pool entries.
"""

import os
import sys
import logging
from pathlib import Path

# Add the project root to the Python path
project_root = str(Path(__file__).parent.parent.parent)
sys.path.append(project_root)

from click_ninja_army.core.data_transformer import DataTransformer
from click_ninja_army.core.database import Database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main function to process CSV files."""
    if len(sys.argv) != 2:
        print("Usage: python -m click_ninja_army.scripts.ingest_csv <csv_file_path>")
        sys.exit(1)

    csv_path = sys.argv[1]
    if not os.path.exists(csv_path):
        print(f"Error: File {csv_path} does not exist")
        sys.exit(1)

    try:
        # Initialize database and data transformer
        db = Database("click_ninja.db")
        transformer = DataTransformer(db)

        # Process the CSV file
        logger.info(f"Processing CSV file: {csv_path}")
        success = transformer.process_csv(csv_path)

        if success:
            logger.info("CSV processing completed successfully")
        else:
            logger.error("CSV processing failed")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Error processing CSV: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 
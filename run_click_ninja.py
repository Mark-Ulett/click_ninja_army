import pandas as pd
from click_ninja_army.core.data_transformer import DataTransformer
from click_ninja_army.core.database import Database
from click_ninja_army.core.request_generator import RequestGenerator
from click_ninja_army.core.coordinator import create_coordinator
from click_ninja_army.config.config import config
import uuid
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    try:
        # Step 1: Load campaign CSV
        CSV_PATH = 'campaign_12476_DEV.csv'
        df = pd.read_csv(CSV_PATH)
        logger.info(f"Loaded {len(df)} rows from {CSV_PATH}")

        # Step 2: Transform data
        transformer = DataTransformer()
        transformed_df = transformer.transform_dataframe(df)
        transformed_data = transformed_df.to_dict(orient='records')
        logger.info(f"Transformed data: {len(transformed_data)} valid rows")

        # Print a sample of the transformed data for review
        logger.info("Sample transformed rows:")
        for row in transformed_data[:3]:
            logger.info(row)

        # Step 3: Save requests to database
        db = Database(config.db_path)
        db.connect()
        saved_count = 0
        for row in transformed_data:
            if not isinstance(row, dict):
                logger.warning(f"Skipping non-dict row: {row}")
                continue
            # Generate a unique request_id for each row
            row['request_id'] = str(uuid.uuid4())
            # Ensure required fields exist
            if 'ad_tag' not in row or not row['ad_tag']:
                row['ad_tag'] = 'default_tag'
            if 'ad_type' not in row or not row['ad_type']:
                row['ad_type'] = 'Display'
            if db.save_ad_request(row):
                saved_count += 1
        logger.info(f"Saved {saved_count} requests to database.")

        # Step 4: Generate and execute ad requests, then impressions and clicks
        request_generator = RequestGenerator(config)
        coordinator = create_coordinator()

        for row in transformed_data:
            if not isinstance(row, dict):
                logger.warning(f"Skipping non-dict row for request generation: {row}")
                continue
            try:
                # 1. Make ad request (simulate by using the row as the ad request payload)
                ad_request_row = row.copy()
                ad_request_row['operation_type'] = 'ad_request'  # Custom type for ad request
                # For this example, we'll just use the row as the ad data (since no real ad request endpoint is shown)
                ad_data = ad_request_row  # In a real system, this would be the response from the ad request API
                # 2. If ad_data is valid, generate both impression and click
                for op_type in ['impression', 'click']:
                    op_row = ad_data.copy()
                    op_row['operation_type'] = op_type
                    try:
                        request_generator.generate_request(op_row)
                        logger.info(f"{op_type.capitalize()} generated for adTag: {op_row.get('adTag', op_row.get('ad_tag'))}")
                    except Exception as op_e:
                        logger.error(f"Error generating {op_type}: {str(op_e)}")
            except Exception as e:
                logger.error(f"Error processing ad/click/impression: {str(e)}")

        logger.info("Click Ninja Army run complete!")
    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}")
        raise

if __name__ == "__main__":
    main() 
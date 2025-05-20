"""
Data Transformer for Click Ninja Army

This module handles the transformation of CSV data into campaign pool entries.
It provides validation, type checking, data cleaning, and campaign pool generation functionality.

Key Features:
- CSV data validation and type conversion
- Category ID parsing
- Campaign pool entry generation with keyword/category expansion
- Error logging and metrics tracking

Example:
    >>> transformer = DataTransformer(db)
    >>> success = transformer.process_csv('input.csv')
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import json
import time
from datetime import datetime
import csv

logger = logging.getLogger(__name__)

class DataTransformer:
    """
    Handles transformation of CSV data into API-ready format.
    
    This class is responsible for:
    1. Validating input data
    2. Converting data types
    3. Parsing category IDs
    4. Transforming data into API format
    
    Attributes:
        required_fields (Dict[str, type]): Dictionary mapping required field names to their expected types.
        optional_fields (Dict[str, type]): Dictionary mapping optional field names to their expected types.
    """
    
    def __init__(self, db):
        """
        Initialize the DataTransformer with database connection.
        
        Args:
            db: Database connection object
        """
        logger.info("Initializing DataTransformer")
        self.db = db
        self.required_fields = {
            'creative_id': int,
            'ad_tag': str,
            'ad_item_id': str,
            'campaign_id': str,
            'ad_type': str
        }
        self.optional_fields = {
            'ad_item_keywords': str,
            'ad_item_categories': str,
            'creative_keywords': str,
            'creative_categories': str
        }
        logger.debug(f"Required fields: {list(self.required_fields.keys())}")
        logger.debug(f"Optional fields: {list(self.optional_fields.keys())}")
    
    def parse_keywords_or_categories(self, value: str) -> List[str]:
        """
        Parse keywords or categories from string format.
        Handles both comma-separated and curly-brace-wrapped lists.
        Args:
            value: Comma-separated string or curly-brace-wrapped string of keywords or categories
        Returns:
            List of individual keywords or categories
        """
        if not value:
            return []
        # Remove curly braces if present
        value = value.strip('{}')
        return [item.strip().strip('"') for item in value.split(',') if item.strip()]

    def generate_campaign_pool_entries(self, row: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        Generate campaign pool entries for a single CSV row.
        
        Args:
            row: Dictionary containing CSV row data
        
        Returns:
            List of campaign pool entries
        """
        entries = []
        base_entry = {
            'ad_tag': row['ad_tag'],
            'ad_item_id': row['ad_item_id'],
            'creative_id': row['creative_id'],
            'campaign_id': row['campaign_id'],
            'ad_type': row['ad_type']
        }

        # Add base entry without keywords/categories
        entries.append(base_entry.copy())

        # Process ad item keywords
        if 'ad_item_keywords' in row and row['ad_item_keywords']:
            keywords = self.parse_keywords_or_categories(row['ad_item_keywords'])
            for keyword in keywords:
                entry = base_entry.copy()
                entry['keyword'] = keyword
                entries.append(entry)

        # Process ad item categories
        if 'ad_item_categories' in row and row['ad_item_categories']:
            categories = self.parse_keywords_or_categories(row['ad_item_categories'])
            for category in categories:
                entry = base_entry.copy()
                entry['category'] = category
                entries.append(entry)

        # Process creative keywords
        if 'creative_keywords' in row and row['creative_keywords']:
            keywords = self.parse_keywords_or_categories(row['creative_keywords'])
            for keyword in keywords:
                entry = base_entry.copy()
                entry['keyword'] = keyword
                entries.append(entry)

        # Process creative categories
        if 'creative_categories' in row and row['creative_categories']:
            categories = self.parse_keywords_or_categories(row['creative_categories'])
            for category in categories:
                entry = base_entry.copy()
                entry['category'] = category
                entries.append(entry)

        return entries

    def process_csv(self, csv_path: str) -> bool:
        """
        Process a CSV file and generate campaign pool entries.
        
        Args:
            csv_path: Path to the CSV file
        
        Returns:
            bool: True if processing was successful, False otherwise
        """
        start_time = time.time()
        rows_processed = 0
        rows_generated = 0

        try:
            with open(csv_path, 'r') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    rows_processed += 1
                    print(f"Processing row: {row}")
                    if not self.validate_row(row):
                        print(f"Skipping invalid row: {row}")
                        continue

                    entries = self.generate_campaign_pool_entries(row)
                    for entry in entries:
                        print(f"Attempting to insert entry: {entry}")
                        entry_id = self.db.insert_campaign_pool_entry(entry)
                        if entry_id != -1:
                            print(f"Inserted entry with id {entry_id}")
                            rows_generated += 1
                        else:
                            raise Exception(f"Failed to insert entry: {entry}")

            self.db.log_campaign_pool_metrics(rows_processed, rows_generated)
            duration = time.time() - start_time
            print(f"Processed {rows_processed} rows, generated {rows_generated} entries in {duration:.2f} seconds")
            return True

        except Exception as e:
            print(f"Error processing CSV file: {e}")
            return False

    def validate_row(self, row: Dict[str, str]) -> bool:
        """
        Validate a CSV row.
        
        Args:
            row: Dictionary containing CSV row data
        
        Returns:
            bool: True if row is valid, False otherwise
        """
        print(f"Validating row: {row}")
        # Check required fields
        for field, field_type in self.required_fields.items():
            if field not in row:
                print(f"Missing required field: {field}")
                return False
            try:
                # Convert to required type
                if field_type == int:
                    row[field] = int(row[field])
                else:
                    row[field] = field_type(row[field])
            except ValueError:
                print(f"Invalid type for field {field}: {row[field]}")
                return False

        # Check optional fields
        for field in self.optional_fields:
            if field in row and row[field]:
                try:
                    # Ensure all optional fields are strings
                    row[field] = str(row[field])
                except ValueError:
                    print(f"Invalid type for optional field {field}: {row[field]}")
                    return False

        return True

    def parse_category_ids(self, category_str: str) -> List[int]:
        """
        Parse category IDs from a string format into a list of integers.
        
        Args:
            category_str (str): String containing category IDs in format "{1019,1007,1006}"
        
        Returns:
            List[int]: List of parsed category IDs
        """
        logger.debug(f"Parsing category IDs from: {category_str}")
        
        if pd.isna(category_str) or not isinstance(category_str, str):
            logger.warning(f"Invalid category string: {category_str}")
            return []
        
        try:
            # Handle format like "{1019,1007,1006}"
            clean_str = category_str.strip('{}')
            ids = [int(x.strip()) for x in clean_str.split(',') if x.strip()]
            logger.debug(f"Successfully parsed {len(ids)} category IDs")
            return ids
        except (ValueError, AttributeError) as e:
            logger.error(f"Failed to parse categories: {str(e)}, Input: {category_str}")
            return []
    
    def _validate_ad_request_id(self, ad_request_id: str) -> bool:
        """
        Validate that the adRequestId contains the required suffix format.
        
        Args:
            ad_request_id (str): The adRequestId to validate
            
        Returns:
            bool: True if valid, False otherwise
            
        The adRequestId must:
        1. Not be empty
        2. Contain exactly one forward slash
        3. Have a UUID part that is at least 8 characters
        4. Have a valid suffix containing only alphanumeric characters, hyphens, or underscores
        """
        if not ad_request_id or not isinstance(ad_request_id, str):
            logger.error("adRequestId is empty or not a string")
            return False
            
        # Check for exactly one forward slash
        if ad_request_id.count('/') != 1:
            logger.error(f"adRequestId must contain exactly one forward slash: {ad_request_id}")
            return False
            
        # Split into UUID and suffix parts
        uuid_part, suffix = ad_request_id.split('/')
        
        # Validate UUID part
        if len(uuid_part) < 8:
            logger.error(f"UUID part must be at least 8 characters: {uuid_part}")
            return False
            
        # Validate suffix
        if not suffix:
            logger.error("Suffix part is empty")
            return False
            
        # Check suffix for valid characters
        valid_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_')
        if not all(c in valid_chars for c in suffix):
            logger.error(f"Suffix contains invalid characters: {suffix}")
            return False
            
        return True
    
    def transform_row(self, row: pd.Series) -> Optional[Dict[str, Any]]:
        """
        Transform a single row of data into the target format.
        
        Args:
            row (pd.Series): Row of data to transform
            
        Returns:
            Optional[Dict[str, Any]]: Transformed data or None if validation fails
        """
        logger.debug(f"Transforming row: {row.to_dict()}")
        
        # Check for required fields
        if 'creative_id' not in row or row['creative_id'] is None:
            logger.warning("Skipping row due to missing or null creative_id")
            return None
        if 'ad_tag' not in row or row['ad_tag'] is None:
            logger.error("Required field is null: ad_tag")
            return None
        
        if not self.validate_row(row):
            logger.warning("Row validation failed, skipping transformation")
            return None
        
        try:
            # Use snake_case keys for output
            transformed = {
                'campaign_id': str(row.get('campaign_id', '')),
                'ad_item_id': int(row['ad_item_id']) if not pd.isna(row.get('ad_item_id')) else None,
                'ad_tag': str(row.get('ad_tag', '')),
                'ad_type': str(row.get('ad_type', 'Display')),
                'creative_id': int(row['creative_id']),
                'page_category_ids': self.parse_category_ids(row.get('ad_item_categories', '{}'))
            }
            # Remove None values and empty strings
            transformed = {k: v for k, v in transformed.items() if v is not None and v != ''}
            logger.debug(f"Successfully transformed row: {json.dumps(transformed)}")
            return transformed
        except Exception as e:
            logger.error(f"Error transforming row: {str(e)}")
            return None
    
    def transform_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform the entire dataframe, keeping only valid rows.
        
        Args:
            df (pd.DataFrame): Input dataframe to transform
            
        Returns:
            pd.DataFrame: Transformed dataframe containing only valid rows
            
        Example:
            >>> transformer = DataTransformer()
            >>> df = pd.read_csv('input.csv')
            >>> transformed_df = transformer.transform_dataframe(df)
        """
        logger.info(f"Starting transformation of dataframe with {len(df)} rows")
        logger.debug(f"DataFrame columns: {list(df.columns)}")
        transformed_rows = []
        invalid_rows = 0
        
        for idx, row in df.iterrows():
            logger.debug(f"Processing row {idx}")
            transformed_row = self.transform_row(row)
            if transformed_row:
                transformed_rows.append(transformed_row)
                logger.debug(f"Row {idx} transformed successfully")
            else:
                invalid_rows += 1
                logger.warning(f"Row {idx} failed validation")
        
        result_df = pd.DataFrame(transformed_rows)
        logger.info(f"Transformation complete. {len(transformed_rows)} valid rows, {invalid_rows} invalid rows")
        if invalid_rows > 0:
            logger.warning(f"Found {invalid_rows} invalid rows during transformation")
        return result_df

    def transform(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Transform the input DataFrame into a list of dictionaries.
        Args:
            df (pd.DataFrame): Input DataFrame
        Returns:
            List[Dict[str, Any]]: Transformed data
        """
        logger.info(f"Starting transformation of dataframe with {len(df)} rows")
        transformed_data = []
        invalid_rows = 0
        
        for index, row in df.iterrows():
            try:
                # Check for required fields
                if pd.isna(row.get('creative_id')) or pd.isna(row.get('ad_tag')):
                    logger.warning(f"Skipping row due to missing or null creative_id or ad_tag")
                    logger.warning(f"Row {index} failed validation")
                    invalid_rows += 1
                    continue
                
                # Convert creative_id to integer, handling NaN values
                try:
                    creative_id = int(row['creative_id'])
                except (ValueError, TypeError):
                    logger.warning(f"Invalid creative_id value in row {index}: {row['creative_id']}")
                    invalid_rows += 1
                    continue
                
                # Create transformed row with consistent column names
                transformed_row = {
                    'campaign_id': str(row['campaign_id']),
                    'ad_item_id': str(row['ad_item_id']),
                    'ad_tag': str(row['ad_tag']),
                    'ad_type': str(row['ad_type']),
                    'creative_id': creative_id,
                    'page_category_ids': self.parse_category_ids(row.get('ad_item_categories', '{}'))
                }
                
                transformed_data.append(transformed_row)
                
            except Exception as e:
                logger.error(f"Error transforming row {index}: {str(e)}")
                invalid_rows += 1
                continue
        
        logger.info(f"Transformation complete. {len(transformed_data)} valid rows, {invalid_rows} invalid rows")
        if invalid_rows > 0:
            logger.warning(f"Found {invalid_rows} invalid rows during transformation")
            
        return transformed_data 

if __name__ == "__main__":
    import sys
    from click_ninja_army.core.database import Database

    if len(sys.argv) != 2:
        print("Usage: python data_transformer.py <csv_file>")
        sys.exit(1)

    csv_file = sys.argv[1]
    db = Database("click_ninja.db")
    db.connect()
    transformer = DataTransformer(db)
    success = transformer.process_csv(csv_file)
    if success:
        print("CSV processing completed successfully.")
    else:
        print("CSV processing failed.")
    db.close() 
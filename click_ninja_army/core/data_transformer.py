"""
Data Transformer for Click Ninja Army

This module handles the transformation of CSV data into API-ready format.
It provides validation, type checking, and data cleaning functionality.

Key Features:
- CSV data validation
- Type conversion
- Category ID parsing
- Data transformation
- Error logging

Example:
    >>> transformer = DataTransformer()
    >>> df = pd.read_csv('input.csv')
    >>> transformed_data = transformer.transform_dataframe(df)
"""

import logging
from typing import Dict, List, Any, Optional
import pandas as pd
import json
import time

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
    
    def __init__(self):
        """
        Initialize the DataTransformer with required and optional field definitions.
        
        Required fields:
        - ad_tag (str): Tag associated with the ad (required for all operations)
        - campaign_id (str): Unique identifier for the campaign
        
        Optional fields:
        - ad_item_id (str): Unique identifier for the ad item
        - ad_type (str): Type of the ad (e.g., 'Display', 'Video')
        - ad_item_categories (str): Categories associated with the ad item
        """
        logger.info("Initializing DataTransformer")
        self.required_fields = {
            'ad_tag': str,
            'campaign_id': str
        }
        self.optional_fields = {
            'ad_item_id': str,
            'ad_type': str,
            'ad_item_categories': str
        }
        logger.debug(f"Required fields: {list(self.required_fields.keys())}")
        logger.debug(f"Optional fields: {list(self.optional_fields.keys())}")
    
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
    
    def validate_row(self, row: pd.Series) -> bool:
        """
        Validate that all required fields are present and of correct type.
        
        Args:
            row (pd.Series): Row of data to validate
            
        Returns:
            bool: True if row is valid, False otherwise
        """
        logger.debug(f"Validating row: {row.to_dict()}")
        
        # Check required fields
        for field, field_type in self.required_fields.items():
            if field not in row:
                logger.error(f"Missing required field: {field}")
                return False
            if pd.isna(row[field]):
                logger.error(f"Required field is null: {field}")
                return False
            if not isinstance(row[field], field_type):
                try:
                    row[field] = field_type(row[field])
                    logger.debug(f"Converted {field} to {field_type.__name__}")
                except (ValueError, TypeError) as e:
                    logger.error(f"Invalid type for field {field}: {type(row[field])}, Error: {str(e)}")
                    return False
        
        # Check optional fields if present
        for field, field_type in self.optional_fields.items():
            if field in row and not pd.isna(row[field]):
                if not isinstance(row[field], field_type):
                    try:
                        row[field] = field_type(row[field])
                        logger.debug(f"Converted {field} to {field_type.__name__}")
                    except (ValueError, TypeError) as e:
                        logger.error(f"Invalid type for optional field {field}: {type(row[field])}, Error: {str(e)}")
                        return False
        
        logger.debug("Row validation successful")
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
        
        if not self.validate_row(row):
            logger.warning("Row validation failed, skipping transformation")
            return None
            
        try:
            # Create base payload with required fields and defaults
            transformed = {
                'adTag': str(row.get('ad_tag', '')),  # Default to empty string if missing
                'campaign_id': str(row.get('campaign_id', '')),  # Default to empty string if missing
                'adItemId': int(row['ad_item_id']) if not pd.isna(row.get('ad_item_id')) else None,
                'adType': str(row.get('ad_type', 'Display')),  # Default to 'Display' if missing
                'creativeId': int(row['creative_id']) if not pd.isna(row.get('creative_id')) else None,
                'customerId': str(row.get('campaign_id', '')),  # Use campaign_id as customerId for API
                'payload': {
                    'sessionId': f"session_{row.get('campaign_id', '')}_{row.get('ad_item_id', '')}" if not pd.isna(row.get('ad_item_id')) else None,
                    'sessionExpiry': str(int(time.time()) + 3600)  # 1 hour from now
                }
            }
            
            # Add category IDs if present
            if 'ad_item_categories' in row and not pd.isna(row['ad_item_categories']):
                transformed['pageCategoryIds'] = self.parse_category_ids(row['ad_item_categories'])
            
            # Remove None values and empty strings
            transformed = {k: v for k, v in transformed.items() if v is not None and v != ''}
            transformed['payload'] = {k: v for k, v in transformed['payload'].items() if v is not None and v != ''}
            
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
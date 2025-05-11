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
    
    Example:
        >>> transformer = DataTransformer()
        >>> row = pd.Series({'campaign_id': '123', 'ad_item_id': '456'})
        >>> transformed = transformer.transform_row(row)
    """
    
    def __init__(self):
        """
        Initialize the DataTransformer with required field definitions.
        
        The required fields are:
        - campaign_id (str): Unique identifier for the campaign
        - ad_item_id (str): Unique identifier for the ad item
        - ad_tag (str): Tag associated with the ad
        - ad_type (str): Type of the ad (e.g., 'Display', 'Video')
        - ad_item_categories (str): Categories associated with the ad item
        """
        logger.info("Initializing DataTransformer")
        self.required_fields = {
            'campaign_id': str,
            'ad_item_id': str,
            'ad_tag': str,
            'ad_type': str,
            'ad_item_categories': str
        }
        logger.debug(f"Required fields configured: {list(self.required_fields.keys())}")
    
    def parse_category_ids(self, category_str: str) -> List[int]:
        """
        Parse category IDs from a string format into a list of integers.
        
        Args:
            category_str (str): String containing category IDs in format "{1019,1007,1006}"
        
        Returns:
            List[int]: List of parsed category IDs
            
        Example:
            >>> transformer = DataTransformer()
            >>> ids = transformer.parse_category_ids("{1019,1007,1006}")
            >>> print(ids)
            [1019, 1007, 1006]
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
            
        Example:
            >>> transformer = DataTransformer()
            >>> row = pd.Series({'campaign_id': '123', 'ad_item_id': '456'})
            >>> is_valid = transformer.validate_row(row)
        """
        logger.debug(f"Validating row: {row.to_dict()}")
        
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
        logger.debug("Row validation successful")
        return True
    
    def transform_row(self, row: pd.Series) -> Optional[Dict[str, Any]]:
        """
        Transform a single row of data into the target format.
        
        Args:
            row (pd.Series): Row of data to transform
            
        Returns:
            Optional[Dict[str, Any]]: Transformed data or None if validation fails
            
        Example:
            >>> transformer = DataTransformer()
            >>> row = pd.Series({
            ...     'campaign_id': '123',
            ...     'ad_item_id': '456',
            ...     'ad_tag': 'tag1',
            ...     'ad_type': 'Display',
            ...     'ad_item_categories': '{1019,1007}'
            ... })
            >>> transformed = transformer.transform_row(row)
        """
        logger.debug(f"Transforming row: {row.to_dict()}")
        
        if not self.validate_row(row):
            logger.warning("Row validation failed, skipping transformation")
            return None
            
        try:
            transformed = {
                'campaign_id': str(row['campaign_id']),
                'ad_item_id': str(row['ad_item_id']),
                'ad_tag': str(row['ad_tag']),
                'ad_type': str(row['ad_type']),
                'page_category_ids': self.parse_category_ids(row['ad_item_categories'])
            }
            logger.debug(f"Successfully transformed row: {transformed}")
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
"""
Request Generator for Click Ninja Army

This module provides a unified interface for generating ad requests across different ad types.
It handles request payload creation, API communication, and response processing.

Key Features:
- Multiple ad type support
- Request payload generation
- API communication
- Error handling
- Response processing

Example:
    >>> generator = RequestGenerator(config)
    >>> request_data = {
    ...     'campaign_id': 'camp_123',
    ...     'ad_item_id': 'item_456',
    ...     'ad_tag': 'tag_1',
    ...     'ad_type': 'Display',
    ...     'page_category_ids': [1019, 1007]
    ... }
    >>> request_id = generator.generate_request(request_data)
"""

import logging
import requests
from typing import Dict, Any, Optional
from datetime import datetime
import json
import time

logger = logging.getLogger(__name__)

class RequestGenerator:
    """
    Unified request generator for different ad types.
    
    This class provides a single interface for:
    1. Creating request payloads
    2. Managing API communication
    3. Handling request responses
    4. Processing ad server responses
    5. Error handling and logging
    
    Attributes:
        config (Dict[str, Any]): Configuration settings
        session (requests.Session): HTTP session for API communication
    
    Example:
        >>> config = {
        ...     'api_url': 'https://api.example.com',
        ...     'api_token': 'your_token',
        ...     'publisher_id': 'pub_123',
        ...     'guest_id': 'guest_456'
        ... }
        >>> generator = RequestGenerator(config)
        >>> request_id = generator.generate_request(request_data)
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the request generator.
        
        Args:
            config (Dict[str, Any]): Configuration settings containing:
                - api_url (str): Base URL for API requests
                - api_token (str): API authentication token
                - publisher_id (str): Publisher identifier
                - guest_id (str): Guest identifier
                - request_timeout (int): Request timeout in seconds
        """
        logger.info("Initializing RequestGenerator")
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {config["api_token"]}',
            'Content-Type': 'application/json'
        })
        logger.debug("RequestGenerator initialized with API configuration")

    def _normalize_field_name(self, field_name: str) -> str:
        """
        Normalize field names to match API requirements.
        
        Args:
            field_name (str): Original field name
        
        Returns:
            str: Normalized field name
        
        Example:
            >>> generator._normalize_field_name('campaignId')
            'campaign_id'
        """
        logger.debug(f"Normalizing field name: {field_name}")
        normalized = field_name.lower().replace(' ', '_')
        logger.debug(f"Normalized to: {normalized}")
        return normalized

    def create_request_payload(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a request payload from campaign data.
        
        Args:
            request_data (Dict[str, Any]): Request data containing:
                - campaign_id (str): Campaign identifier
                - ad_item_id (str): Ad item identifier
                - ad_tag (str): Ad tag
                - ad_type (str): Type of ad
                - page_category_ids (List[int]): Category IDs
        
        Returns:
            Dict[str, Any]: API-ready request payload
        
        Example:
            >>> request_data = {
            ...     'campaign_id': 'camp_123',
            ...     'ad_item_id': 'item_456',
            ...     'ad_tag': 'tag_1',
            ...     'ad_type': 'Display',
            ...     'page_category_ids': [1019, 1007]
            ... }
            >>> payload = generator.create_request_payload(request_data)
        """
        try:
            logger.debug(f"Creating payload for ad type: {request_data['ad_type']}")
            logger.debug(f"Campaign ID: {request_data.get('campaign_id', 'unknown')}")
            
            # Base payload structure
            payload = {
                'publisher_id': self.config['publisher_id'],
                'guest_id': self.config['guest_id'],
                'campaign_id': request_data['campaign_id'],
                'ad_tag': request_data['ad_tag'],
                'ad_type': request_data['ad_type'].lower(),
                'page_category_ids': request_data.get('page_category_ids', []),
                'timestamp': datetime.now().isoformat()
            }
            logger.debug("Base payload structure created")
            
            # Add ad type specific fields
            if request_data['ad_type'].lower() == 'display':
                payload.update({
                    'ad_item_id': request_data.get('ad_item_id'),
                    'ad_size': request_data.get('ad_size', '300x250')
                })
                logger.debug("Added display-specific fields to payload")
            elif request_data['ad_type'].lower() == 'video':
                payload.update({
                    'video_duration': request_data.get('video_duration', 30),
                    'video_quality': request_data.get('video_quality', 'high')
                })
                logger.debug("Added video-specific fields to payload")
            
            logger.debug(f"Created payload: {json.dumps(payload)}")
            return payload
            
        except Exception as e:
            logger.error(f"Failed to create request payload: {str(e)}")
            logger.error(f"Request data: {json.dumps(request_data)}")
            raise

    def generate_request(self, request_data: Dict[str, Any]) -> Optional[str]:
        """
        Generate a single ad request.
        
        Args:
            request_data (Dict[str, Any]): Request data containing:
                - campaign_id (str): Campaign identifier
                - ad_item_id (str): Ad item identifier
                - ad_tag (str): Ad tag
                - ad_type (str): Type of ad
                - page_category_ids (List[int]): Category IDs
        
        Returns:
            Optional[str]: Generated request ID if successful, None otherwise
        
        Example:
            >>> request_data = {
            ...     'campaign_id': 'camp_123',
            ...     'ad_item_id': 'item_456',
            ...     'ad_tag': 'tag_1',
            ...     'ad_type': 'Display',
            ...     'page_category_ids': [1019, 1007]
            ... }
            >>> request_id = generator.generate_request(request_data)
        """
        try:
            logger.info(f"Generating request for campaign {request_data['campaign_id']}")
            
            # Validate ad type
            if request_data['ad_type'] not in ['Display', 'Video']:
                logger.error(f"Unsupported ad type: {request_data['ad_type']}")
                raise ValueError(f"Unsupported ad type: {request_data['ad_type']}")
            
            # Create request payload
            payload = self.create_request_payload(request_data)
            logger.debug(f"Created payload: {json.dumps(payload)}")
            
            # Make API request
            logger.info(f"Making API request to {self.config['api_url']}/requests")
            start_time = time.time()
            response = self.session.post(
                f"{self.config['api_url']}/requests",
                json=payload,
                timeout=self.config.get('request_timeout', 10)
            )
            response_time = time.time() - start_time
            logger.debug(f"API request completed in {response_time:.2f} seconds")
            
            response.raise_for_status()
            
            # Process response
            result = response.json()
            request_id = result.get('request_id')
            logger.info(f"Successfully generated request: {request_id}")
            logger.debug(f"Full response: {json.dumps(result)}")
            return request_id
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            if hasattr(e.response, 'text'):
                logger.error(f"Response content: {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Request generation failed: {str(e)}")
            return None 
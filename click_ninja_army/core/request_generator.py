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
from datetime import datetime, timezone
import json
import time
import math

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
        ...     'guest_id': 'guest_456',
        ...     'ad_server_impressions_url': 'https://impression.server.com',
        ...     'ad_server_clicks_url': 'https://click.server.com',
        ...     'request_timeout': 10
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
                - ad_server_impressions_url (str): URL for impression tracking
                - ad_server_clicks_url (str): URL for click tracking
        """
        logger.info("Initializing RequestGenerator")
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {config.api.auth_token}',
            'Content-Type': 'application/json',
            'X-Api-Key': '2AHJwFShwrg8rD1'
        })
        logger.debug("RequestGenerator initialized with API configuration")

    def create_impression_payload(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create an impression request payload.
        
        Args:
            request_data (Dict[str, Any]): Request data containing:
                - adTag (str): Ad tag
                - adItemId (int): Ad item identifier
                - adRequestId (str): Request identifier
                - creativeId (int): Creative identifier
                - customerId (str): Customer identifier
                - payload (Dict[str, Any]): Additional payload data
        
        Returns:
            Dict[str, Any]: API-ready impression payload
        """
        try:
            logger.debug("Creating impression payload")
            def safe_int(val):
                return int(val) if val is not None and not (isinstance(val, float) and math.isnan(val)) else None
            # Format displayedAt with 3 digits for milliseconds and timezone info
            displayed_at = datetime.now(timezone.utc).isoformat(timespec='milliseconds')
            
            # Ensure creativeId is a valid integer (default to 1 if not provided)
            creative_id = safe_int(request_data.get('creativeId', 1))
            if creative_id is None:
                creative_id = 1
                
            payload = {
                'adTag': request_data['adTag'],
                'adItemId': safe_int(request_data.get('adItemId', None)),
                'adRequestId': request_data.get('adRequestId', ''),
                'creativeId': creative_id,
                'cache': request_data.get('cache', False),
                'customerId': request_data.get('customerId', ''),
                'displayedAt': displayed_at,
                'payload': request_data.get('payload', {
                    'sessionId': request_data.get('sessionId', ''),
                    'sessionExpiry': request_data.get('sessionExpiry', '')
                })
            }
            
            logger.debug(f"Created impression payload: {json.dumps(payload)}")
            return payload
            
        except Exception as e:
            logger.error(f"Failed to create impression payload: {str(e)}")
            raise

    def create_click_payload(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a click request payload.
        
        Args:
            request_data (Dict[str, Any]): Request data containing:
                - adItemId (int): Ad item identifier
                - adTag (str): Ad tag
                - adRequestId (str): Request identifier
                - creativeId (int): Creative identifier
                - customerId (str): Customer identifier
                - payload (Dict[str, Any]): Additional payload data
        
        Returns:
            Dict[str, Any]: API-ready click payload
        """
        try:
            logger.debug("Creating click payload")
            def safe_int(val):
                return int(val) if val is not None and not (isinstance(val, float) and math.isnan(val)) else None
            # Format displayedAt and clickedAt with 3 digits for milliseconds and timezone info
            now_iso = datetime.now(timezone.utc).isoformat(timespec='milliseconds')
            
            # Ensure creativeId is a valid integer (default to 1 if not provided)
            creative_id = safe_int(request_data.get('creativeId', 1))
            if creative_id is None:
                creative_id = 1
                
            payload = {
                'adItemId': safe_int(request_data.get('adItemId', None)),
                'adTag': request_data['adTag'],
                'adRequestId': request_data.get('adRequestId', ''),
                'creativeId': creative_id,
                'customerId': request_data.get('customerId', ''),
                'displayedAt': request_data.get('displayedAt', now_iso),
                'clickedAt': now_iso,
                'payload': request_data.get('payload', {
                    'sessionId': request_data.get('sessionId', ''),
                    'sessionExpiry': request_data.get('sessionExpiry', '')
                })
            }
            
            logger.debug(f"Created click payload: {json.dumps(payload)}")
            return payload
            
        except Exception as e:
            logger.error(f"Failed to create click payload: {str(e)}")
            raise

    def generate_request(self, request_data: Dict[str, Any]) -> Optional[str]:
        """
        Generate a single ad request.
        
        Args:
            request_data (Dict[str, Any]): Request data containing:
                - adTag (str): Ad tag (required)
                - adItemId (int): Ad item identifier (optional)
                - adRequestId (str): Request identifier (optional)
                - creativeId (int): Creative identifier (optional)
                - customerId (str): Customer identifier (optional)
                - payload (Dict[str, Any]): Additional payload data (optional)
        
        Returns:
            Optional[str]: Generated request ID if successful, None otherwise
        """
        try:
            logger.info("Generating request")
            
            # Print full request data for debugging
            print("\n=== FULL REQUEST DATA ===")
            print(json.dumps(request_data, indent=2))
            
            # Validate required fields
            if 'adTag' not in request_data:
                logger.error("Missing required field: adTag")
                raise ValueError("Request data must contain 'adTag' field")
            
            # Determine operation type and create appropriate payload
            operation_type = request_data.get('operation_type', 'impression')
            if operation_type == 'impression':
                payload = self.create_impression_payload(request_data)
                endpoint = self.config.api.ad_server_impressions_url
            elif operation_type == 'click':
                payload = self.create_click_payload(request_data)
                endpoint = self.config.api.ad_server_clicks_url
            else:
                logger.error(f"Unsupported operation type: {operation_type}")
                raise ValueError(f"Unsupported operation type: {operation_type}")
            
            # Print full request details
            print("\n=== FULL REQUEST DETAILS ===")
            print(f"Endpoint: {endpoint}")
            print(f"Operation Type: {operation_type}")
            print("\n=== REQUEST HEADERS ===")
            for header, value in self.session.headers.items():
                print(f"{header}: {value}")
            
            print("\n=== REQUEST PAYLOAD ===")
            print(json.dumps(payload, indent=2))
            
            # Make API request
            logger.info(f"Making API request to {endpoint}")
            response = self.session.post(
                endpoint,
                json=payload,
                timeout=self.config.api.request_timeout
            )
            
            # Print response details
            print("\n=== RESPONSE DETAILS ===")
            print(f"Status Code: {response.status_code}")
            print("Response Headers:")
            for header, value in response.headers.items():
                print(f"{header}: {value}")
            print("\nResponse Body:")
            
            # Handle response based on operation type
            if operation_type in ['impression', 'click']:
                if response.status_code == 204:
                    print("204 No Content (Success)")
                    logger.info(f"{operation_type.capitalize()} request successful (204 No Content)")
                    return None  # No request ID to return for these
                else:
                    # Print and log error body if not 204
                    try:
                        print(json.dumps(response.json(), indent=2))
                    except Exception:
                        print(response.text)
                    response.raise_for_status()
                    return None
            else:
                # For ad request API (expecting JSON)
                try:
                    print(json.dumps(response.json(), indent=2))
                except Exception:
                    print(response.text)
                response.raise_for_status()
                response_data = response.json()
                request_id = response_data.get('requestId')
                if not request_id:
                    logger.error("No request ID in response")
                    return None
                logger.info(f"Successfully generated request with ID: {request_id}")
                return request_id
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Failed to generate request: {str(e)}")
            raise 
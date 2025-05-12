"""
Workflow Coordinator - Manages the integration of Scout and Strike Ninjas
"""

import logging
import time
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from click_ninja_army.config.config import config
from .scout import ScoutNinja, RequestConfig
from .strike import StrikeNinja, OperationConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class CoordinatorConfig:
    """Configuration for the workflow coordinator"""
    # Database configuration
    db_path: str
    
    # API configuration
    base_url: str
    auth_token: str
    publisher_id: str
    guest_id: str
    
    # Ad server URLs
    ad_server_url: str
    ad_server_impressions_url: str
    ad_server_clicks_url: str
    
    # Scout Ninja configuration
    scout_rate_limit: float
    scout_burst_limit: int
    scout_worker_count: int
    
    # Strike Ninja configuration
    strike_worker_count: int
    operation_timeout: int
    max_retries: int
    retry_delay: float

class WorkflowCoordinator:
    """Coordinates the workflow between Scout and Strike Ninjas"""
    
    def __init__(self, config: CoordinatorConfig):
        """Initialize the workflow coordinator."""
        logger.info("Initializing WorkflowCoordinator")
        self.config = config
        
        # Initialize Scout Ninja
        logger.debug("Initializing Scout Ninja")
        scout_config = RequestConfig(
            base_url=config.base_url,
            auth_token=config.auth_token,
            publisher_id=config.publisher_id,
            guest_id=config.guest_id,
            ad_server_url=config.ad_server_url,
            ad_server_impressions_url=config.ad_server_impressions_url,
            ad_server_clicks_url=config.ad_server_clicks_url
        )
        self.scout = ScoutNinja(
            request_config=scout_config,
            db_connection_string=config.db_path,
            rate_limit=config.scout_rate_limit,
            burst_limit=config.scout_burst_limit,
            worker_count=config.scout_worker_count
        )
        
        # Initialize Strike Ninja
        logger.debug("Initializing Strike Ninja")
        strike_config = OperationConfig(
            base_url=config.base_url,
            auth_token=config.auth_token,
            publisher_id=config.publisher_id,
            guest_id=config.guest_id,
            ad_server_url=config.ad_server_url,
            ad_server_impressions_url=config.ad_server_impressions_url,
            ad_server_clicks_url=config.ad_server_clicks_url,
            timeout=config.operation_timeout,
            max_retries=config.max_retries,
            retry_delay=config.retry_delay
        )
        self.strike = StrikeNinja(
            operation_config=strike_config,
            db_connection_string=config.db_path,
            worker_count=config.strike_worker_count
        )
        logger.info("WorkflowCoordinator initialized successfully")

    def start(self):
        """Start the workflow."""
        try:
            logger.info("Starting workflow coordinator")
            logger.debug("Starting Scout Ninja")
            self.scout.start()
            logger.debug("Starting Strike Ninja")
            self.strike.start()
            logger.info("Workflow coordinator started successfully")
        except Exception as e:
            logger.error(f"Failed to start workflow coordinator: {str(e)}")
            raise

    def stop(self):
        """Stop the workflow."""
        try:
            logger.info("Stopping workflow coordinator")
            logger.debug("Stopping Scout Ninja")
            self.scout.stop()
            logger.debug("Stopping Strike Ninja")
            self.strike.stop()
            logger.info("Workflow coordinator stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping workflow coordinator: {str(e)}")
            raise

    def submit_request(self, request_data: Dict[str, Any]) -> str:
        """Submit a single request to the workflow."""
        try:
            logger.info(f"Submitting request for ad type: {request_data.get('adType', 'unknown')}")
            
            # Validate request data
            if not isinstance(request_data, dict):
                logger.error("Invalid request data: not a dictionary")
                raise ValueError("Request data must be a dictionary")
                
            if 'adType' not in request_data:
                logger.error("Invalid request data: missing adType field")
                raise ValueError("Request data must contain 'adType' field")
                
            # Generate request using Scout Ninja
            logger.debug("Generating request via Scout Ninja")
            request_id = self.scout.request_generator.generate_request(request_data)
            if not request_id:
                logger.error("Failed to generate request")
                raise ValueError("Failed to generate request")
                
            logger.info(f"Successfully generated request: {request_id}")
            return request_id
        except Exception as e:
            logger.error(f"Error submitting request: {str(e)}")
            raise

    def wait_for_completion(self, request_id: str, timeout: int = 30) -> Dict[str, Any]:
        """Wait for a request to complete."""
        try:
            logger.info(f"Waiting for request {request_id} to complete (timeout: {timeout}s)")
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                # Check request status in database
                with self.scout.db_conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT status, retries 
                        FROM request_pool 
                        WHERE request_id = %s
                    """, (request_id,))
                    result = cursor.fetchone()
                    
                    if result:
                        status, retries = result
                        if status in ['completed', 'failed']:
                            logger.info(f"Request {request_id} completed with status: {status}")
                            return {
                                'status': status,
                                'retries': retries,
                                'metrics': {
                                    'scout': self.scout.get_performance_metrics(),
                                    'strike': self.strike.get_performance_metrics()
                                }
                            }
                
                time.sleep(0.1)
            
            logger.warning(f"Request {request_id} timed out after {timeout} seconds")
            return {
                'status': 'timeout',
                'message': f'Request {request_id} timed out after {timeout} seconds',
                'metrics': {
                    'scout': self.scout.get_performance_metrics(),
                    'strike': self.strike.get_performance_metrics()
                }
            }
        except Exception as e:
            logger.error(f"Error waiting for request {request_id} completion: {str(e)}")
            raise

    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        return {
            'scout': self.scout.get_performance_metrics(),
            'strike': self.strike.get_performance_metrics()
        }

    def process_campaign(self, campaign: Dict[str, Any], request_count: int) -> Dict[str, Any]:
        """Process a campaign through the workflow."""
        try:
            campaign_id = campaign.get('campaign_id', 'unknown')
            logger.info(f"Processing campaign {campaign_id} with {request_count} requests")
            logger.debug(f"Campaign data: {json.dumps(campaign)}")
            
            # Generate requests using Scout Ninja
            logger.debug(f"Generating {request_count} requests for campaign {campaign_id}")
            start_time = time.time()
            success_count = self.scout.generate_requests([campaign], request_count)
            generation_time = time.time() - start_time
            
            if success_count == 0:
                logger.error(f"Failed to generate any requests for campaign {campaign_id}")
                return {
                    "status": "error",
                    "message": "Failed to generate any requests",
                    "metrics": {
                        "scout": self.scout.get_performance_metrics(),
                        "strike": self.strike.get_performance_metrics()
                    }
                }
            
            logger.info(f"Generated {success_count} requests in {generation_time:.2f} seconds")
            
            # Execute operations using Strike Ninja
            logger.info(f"Executing operations for {success_count} requests from campaign {campaign_id}")
            start_time = time.time()
            self.strike.execute_operations(
                request_ids=[f"req_{i}" for i in range(success_count)],
                operation_type="test_operation"
            )
            execution_time = time.time() - start_time
            
            logger.info(f"Successfully processed campaign {campaign_id}")
            logger.debug(f"Campaign processing metrics: generation_time={generation_time:.2f}s, execution_time={execution_time:.2f}s")
            
            return {
                "status": "success",
                "message": f"Processed {success_count} requests",
                "metrics": {
                    "scout": self.scout.get_performance_metrics(),
                    "strike": self.strike.get_performance_metrics(),
                    "generation_time": generation_time,
                    "execution_time": execution_time
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing campaign {campaign.get('campaign_id', 'unknown')}: {str(e)}")
            logger.debug(f"Campaign data: {json.dumps(campaign)}")
            return {
                "status": "error",
                "message": str(e),
                "metrics": {
                    "scout": self.scout.get_performance_metrics(),
                    "strike": self.strike.get_performance_metrics()
                }
            }

def create_coordinator() -> WorkflowCoordinator:
    """Create a coordinator instance using the hardcoded config object"""
    logger.info("Creating WorkflowCoordinator instance")
    coordinator_config = CoordinatorConfig(
        db_path=config.db_path,
        base_url=config.api.base_url,
        auth_token=config.api.auth_token,
        publisher_id=config.api.publisher_id,
        guest_id=config.api.guest_id,
        ad_server_url=config.api.ad_server_url,
        ad_server_impressions_url=config.api.ad_server_impressions_url,
        ad_server_clicks_url=config.api.ad_server_clicks_url,
        scout_rate_limit=config.rate_limit,
        scout_burst_limit=config.burst_limit,
        scout_worker_count=config.worker_count,
        strike_worker_count=config.worker_count,
        operation_timeout=config.request_timeout,
        max_retries=3,
        retry_delay=1.0
    )
    logger.debug("Coordinator configuration created")
    return WorkflowCoordinator(coordinator_config) 
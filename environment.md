"""
Configuration module for Click Ninja Army.
Handles loading and validation of environment variables.
"""

import os
from dataclasses import dataclass
from typing import Optional, List, Dict
from dotenv import load_dotenv

# Database Configuration
DB_CONNECTION_STRING=postgresql://click_ninja_test:clickninja@localhost:5432/click_ninja_test

# API Configuration
API_ENVIRONMENT=DEV
API_BASE_URL=https://dev.shyftcommerce.com/server
API_AUTH_TOKEN=test_token
PUBLISHER_ID=PET67
GUEST_ID=G-PET34567

# Development Mode
DEBUG_MODE=true
TEST_MODE=true

# Load environment variables from .env file
load_dotenv()

@dataclass
class DatabaseConfig:
    """Database configuration settings."""
    connection_string: str = os.getenv('DB_CONNECTION_STRING', 'postgresql://user:clickninja@localhost:5432/click_ninja_db')
    schema_version: str = os.getenv('DB_SCHEMA_VERSION', '1.0')

@dataclass
class APIConfig:
    """API configuration settings."""
    base_url: str = os.getenv('API_BASE_URL', 'https://dev.shyftcommerce.com/server')
    auth_token: str = os.getenv('API_AUTH_TOKEN', '')
    publisher_id: str = os.getenv('PUBLISHER_ID', 'PET67')
    guest_id: str = os.getenv('GUEST_ID', 'G-PET34567')
    environment: str = os.getenv('API_ENVIRONMENT', 'DEV')  # DEV or PDEV

@dataclass
class AdSlotConfig:
    """Ad slot configuration settings."""
    ad_size: str = os.getenv('AD_SIZE', 'adSize4')
    ad_count: int = int(os.getenv('AD_COUNT', '40'))
    ad_tag: str = os.getenv('AD_TAG', 'petco/cp-creative-targeting-test/category/product/product/desktop')

@dataclass
class UserConfig:
    """User configuration settings."""
    network_ip: str = os.getenv('NETWORK_IP', '127.0.0.1')
    page_type: str = os.getenv('PAGE_TYPE', 'category')
    page_category_ids: List[int] = os.getenv('PAGE_CATEGORY_IDS', '10049').split(',')
    search_keyword: Optional[str] = os.getenv('SEARCH_KEYWORD', None)

@dataclass
class DeviceConfig:
    """Device configuration settings."""
    device_id: str = os.getenv('DEVICE_ID', 'test-device-id')
    user_agent: str = os.getenv('USER_AGENT', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)')
    language: str = os.getenv('LANGUAGE', 'en-US')
    platform: str = os.getenv('PLATFORM', 'macOS')
    screen_size: str = os.getenv('SCREEN_SIZE', '1920x1080')

@dataclass
class ScoutConfig:
    """Scout Ninja configuration settings."""
    rate_limit: int = int(os.getenv('SCOUT_RATE_LIMIT', '100'))
    burst_limit: int = int(os.getenv('SCOUT_BURST_LIMIT', '200'))
    worker_count: int = int(os.getenv('SCOUT_WORKER_COUNT', '10'))
    ad_types: List[str] = os.getenv('AD_TYPES', 'Product,NativeFixed,NativeDynamic,Display,Video').split(',')
    request_timeout: int = int(os.getenv('REQUEST_TIMEOUT', '30'))

@dataclass
class StrikeConfig:
    """Strike Ninja configuration settings."""
    worker_count: int = int(os.getenv('STRIKE_WORKER_COUNT', '10'))
    operation_timeout: int = int(os.getenv('OPERATION_TIMEOUT', '30'))
    max_retries: int = int(os.getenv('MAX_RETRIES', '3'))
    retry_delay: int = int(os.getenv('RETRY_DELAY', '5'))
    click_tracking: bool = os.getenv('CLICK_TRACKING', 'true').lower() == 'true'
    impression_tracking: bool = os.getenv('IMPRESSION_TRACKING', 'true').lower() == 'true'

@dataclass
class LoggingConfig:
    """Logging configuration settings."""
    level: str = os.getenv('LOG_LEVEL', 'INFO')
    file: str = os.getenv('LOG_FILE', 'logs/click_ninja.log')
    format: str = os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    request_logging: bool = os.getenv('REQUEST_LOGGING', 'true').lower() == 'true'
    response_logging: bool = os.getenv('RESPONSE_LOGGING', 'true').lower() == 'true'

@dataclass
class MonitoringConfig:
    """Performance monitoring configuration settings."""
    enabled: bool = os.getenv('ENABLE_METRICS', 'true').lower() == 'true'
    interval: int = int(os.getenv('METRICS_INTERVAL', '60'))
    retention: int = int(os.getenv('METRICS_RETENTION', '7'))
    track_response_times: bool = os.getenv('TRACK_RESPONSE_TIMES', 'true').lower() == 'true'
    track_error_rates: bool = os.getenv('TRACK_ERROR_RATES', 'true').lower() == 'true'

@dataclass
class ErrorConfig:
    """Error handling configuration settings."""
    notification_email: str = os.getenv('ERROR_NOTIFICATION_EMAIL', 'admin@example.com')
    notification_threshold: int = int(os.getenv('ERROR_NOTIFICATION_THRESHOLD', '10'))
    retry_on_timeout: bool = os.getenv('RETRY_ON_TIMEOUT', 'true').lower() == 'true'
    retry_on_network_error: bool = os.getenv('RETRY_ON_NETWORK_ERROR', 'true').lower() == 'true'

@dataclass
class ResourceConfig:
    """Resource management configuration settings."""
    max_memory_usage: int = int(os.getenv('MAX_MEMORY_USAGE', '80'))
    max_cpu_usage: int = int(os.getenv('MAX_CPU_USAGE', '80'))
    worker_restart_interval: int = int(os.getenv('WORKER_RESTART_INTERVAL', '3600'))
    max_concurrent_requests: int = int(os.getenv('MAX_CONCURRENT_REQUESTS', '1000'))

@dataclass
class SecurityConfig:
    """Security configuration settings."""
    encryption_key: str = os.getenv('ENCRYPTION_KEY', '')
    ssl_verify: bool = os.getenv('SSL_VERIFY', 'true').lower() == 'true'
    api_key_rotation_interval: int = int(os.getenv('API_KEY_ROTATION_INTERVAL', '86400'))
    session_expiry: int = int(os.getenv('SESSION_EXPIRY', '1905341811'))

@dataclass
class DevelopmentConfig:
    """Development mode configuration settings."""
    debug_mode: bool = os.getenv('DEBUG_MODE', 'false').lower() == 'true'
    test_mode: bool = os.getenv('TEST_MODE', 'false').lower() == 'true'
    mock_api: bool = os.getenv('MOCK_API', 'false').lower() == 'true'
    mock_response_delay: int = int(os.getenv('MOCK_RESPONSE_DELAY', '100'))

@dataclass
class Config:
    """Main configuration class combining all settings."""
    database: DatabaseConfig = DatabaseConfig()
    api: APIConfig = APIConfig()
    ad_slot: AdSlotConfig = AdSlotConfig()
    user: UserConfig = UserConfig()
    device: DeviceConfig = DeviceConfig()
    scout: ScoutConfig = ScoutConfig()
    strike: StrikeConfig = StrikeConfig()
    logging: LoggingConfig = LoggingConfig()
    monitoring: MonitoringConfig = MonitoringConfig()
    error: ErrorConfig = ErrorConfig()
    resource: ResourceConfig = ResourceConfig()
    security: SecurityConfig = SecurityConfig()
    development: DevelopmentConfig = DevelopmentConfig()

    def validate(self) -> None:
        """Validate configuration settings."""
        if not self.database.connection_string:
            raise ValueError("Database connection string is required")
        
        if not self.api.auth_token:
            raise ValueError("API authentication token is required")
        
        if not self.api.publisher_id:
            raise ValueError("Publisher ID is required")
        
        if not self.api.guest_id:
            raise ValueError("Guest ID is required")
        
        if self.scout.rate_limit <= 0:
            raise ValueError("Scout rate limit must be positive")
        
        if self.scout.burst_limit <= 0:
            raise ValueError("Scout burst limit must be positive")
        
        if self.scout.worker_count <= 0:
            raise ValueError("Scout worker count must be positive")
        
        if self.strike.worker_count <= 0:
            raise ValueError("Strike worker count must be positive")
        
        if self.strike.operation_timeout <= 0:
            raise ValueError("Operation timeout must be positive")
        
        if self.strike.max_retries < 0:
            raise ValueError("Maximum retries cannot be negative")
        
        if self.strike.retry_delay < 0:
            raise ValueError("Retry delay cannot be negative")
        
        if not self.ad_slot.ad_tag:
            raise ValueError("Ad tag is required")
        
        if self.ad_slot.ad_count <= 0:
            raise ValueError("Ad count must be positive")
        
        if not self.device.device_id:
            raise ValueError("Device ID is required")
        
        if not self.device.user_agent:
            raise ValueError("User agent is required")

# Create global configuration instance
config = Config()

def get_config() -> Config:
    """Get the global configuration instance."""
    return config 
"""
Hardcoded configuration for Click Ninja Army.
All environment variables are now set directly in this file.
"""

from dataclasses import dataclass, field
from typing import Optional

@dataclass
class APIConfig:
    """API configuration settings."""
    base_url: str = "https://dev.shyftcommerce.com/server"
    auth_token: str = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJjbGllbnQtMjAyNC0wNy0zMF8xNC41Ny4yOCIsImlhdCI6MTcyMjM2NTg1Mn0.ggtEOcIVoUpYAhOd_BqK_ov8HH3cozEq3R6ve1NVFczYc1qOfIhaJU1242gB7sSQfGN-Peze5TmT42bz4oecIj9piWvWQGDxLJ_cU77gRPummCbG3uq6F2UOafutvX2NvArelrNxbnmGdGHmoyAsHkK1KAuPOW5hBlqjlUMZt-bEgFrVdSAJPx0bzauqjf4hA_ZVqJrLlTotsOjAMEhHPDyaLUqKu4L5HXZEGUSh5ijnbDbzO_zMB35DnKaBZhEcQR3nhzfHlX1Fk1TaQqZaO7X7TX9Q9yMeFmiy6TLq4FV7kyNWY8ygZSxAymeWogjmRXD9XGKO5wd_QUBvCQ7uAg"
    publisher_id: str = "PET67"
    guest_id: str = "G-PET34567"
    ad_server_url: str = "https://dev.shyftcommerce.com/server/rmn-requests"
    ad_server_impressions_url: str = "https://dev.shyftcommerce.com/server/rmn-impressions"
    ad_server_clicks_url: str = "https://dev.shyftcommerce.com/server/rmn-clicks"
    request_timeout: int = 10

@dataclass
class Config:
    # API Configuration
    api: APIConfig = field(default_factory=APIConfig)

    # Database Configuration (SQLite)
    db_path: str = "click_ninja.db"

    # Worker Configuration
    worker_count: int = 5
    request_timeout: int = 10

    # Rate Limiting
    rate_limit: float = 10.0
    burst_limit: int = 20

    # Other options (add as needed)
    debug_mode: bool = True
    test_mode: bool = False

    def validate(self) -> Optional[str]:
        if not self.api.auth_token:
            return "API_TOKEN is required"
        if not self.db_path:
            return "DB_PATH is required"
        if not self.api.ad_server_url:
            return "AD_SERVER_URL must be configured"
        if not self.api.ad_server_impressions_url:
            return "AD_SERVER_IMPRESSIONS_URL must be configured"
        if not self.api.ad_server_clicks_url:
            return "AD_SERVER_CLICKS_URL must be configured"
        return None

# Global config instance
config = Config() 
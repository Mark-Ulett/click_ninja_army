"""
Hardcoded configuration for Click Ninja Army.
All environment variables are now set directly in this file.
"""

from dataclasses import dataclass
from typing import Optional

@dataclass
class Config:
    # API Configuration
    api_url: str = "https://dev.shyftcommerce.com/server"
    api_token: str = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJjbGllbnQtMjAyNC0wNy0zMF8xNC41Ny4yOCIsImlhdCI6MTcyMjM2NTg1Mn0.ggtEOcIVoUpYAhOd_BqK_ov8HH3cozEq3R6ve1NVFczYc1qOfIhaJU1242gB7sSQfGN-Peze5TmT42bz4oecIj9piWvWQGDxLJ_cU77gRPummCbG3uq6F2UOafutvX2NvArelrNxbnmGdGHmoyAsHkK1KAuPOW5hBlqjlUMZt-bEgFrVdSAJPx0bzauqjf4hA_ZVqJrLlTotsOjAMEhHPDyaLUqKu4L5HXZEGUSh5ijnbDbzO_zMB35DnKaBZhEcQR3nhzfHlX1Fk1TaQqZaO7X7TX9Q9yMeFmiy6TLq4FV7kyNWY8ygZSxAymeWogjmRXD9XGKO5wd_QUBvCQ7uAgre"
    publisher_id: str = "PET67"
    guest_id: str = "G-PET34567"

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
        if not self.api_token:
            return "API_TOKEN is required"
        if not self.db_path:
            return "DB_PATH is required"
        return None

# Global config instance
config = Config() 
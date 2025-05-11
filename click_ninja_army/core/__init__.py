"""
Core components for Click Ninja Army
"""

import logging
import os
from datetime import datetime
from .data_transformer import DataTransformer

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/click_ninja_{datetime.now().strftime("%Y%m%d")}.log'),
        logging.StreamHandler()
    ]
)

# Create logger
logger = logging.getLogger(__name__)
logger.info("Click Ninja Army core module initialized")

__all__ = ['DataTransformer'] 
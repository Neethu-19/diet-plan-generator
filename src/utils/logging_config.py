"""
Logging configuration for the application.
"""
import logging
import sys
from src.config import settings


def setup_logging():
    """Configure logging with appropriate format and level."""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Set specific loggers
    logging.getLogger("uvicorn").setLevel(log_level)
    logging.getLogger("fastapi").setLevel(log_level)
    
    return logging.getLogger(__name__)


logger = setup_logging()

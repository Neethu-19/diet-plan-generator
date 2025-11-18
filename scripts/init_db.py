"""
Database initialization script.
Creates tables and runs initial setup.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.database import init_db, check_db_connection
from src.utils.logging_config import logger


def main():
    """Initialize database."""
    logger.info("Starting database initialization")
    
    # Check connection
    if not check_db_connection():
        logger.error("Cannot connect to database. Please check DATABASE_URL")
        sys.exit(1)
    
    logger.info("Database connection successful")
    
    # Create tables
    try:
        init_db()
        logger.info("Database initialization complete")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

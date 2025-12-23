"""
Initialize PostgreSQL database with all tables
Creates comprehensive clinic knowledge schema
"""

import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.db_engine import engine
from core.models_sql import SQLModel

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def init_database():
    """Create all tables in PostgreSQL"""
    try:
        logger.info("Connecting to Railway PostgreSQL...")
        logger.info(f"Database URL: {str(engine.url).split('@')[1]}")  # Don't log password
        
        logger.info("\nCreating tables...")
        SQLModel.metadata.create_all(engine)
        
        logger.info("\n✓ Database initialization complete!")
        logger.info("\nCreated tables:")
        for table in SQLModel.metadata.sorted_tables:
            logger.info(f"  - {table.name}")
        
        return True
    except Exception as e:
        logger.error(f"\n✗ Error creating tables: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)

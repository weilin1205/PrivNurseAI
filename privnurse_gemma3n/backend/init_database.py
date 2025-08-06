"""
Database initialization script for PrivNurse AI
Handles both new installations and migrations
"""
import sys
import logging
from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError, ProgrammingError
from database import engine, init_db
from models import Base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_patient_category_enum():
    """Check patient_category enum has correct values"""
    try:
        with engine.connect() as conn:
            # Check if patients table exists
            inspector = inspect(engine)
            if 'patients' not in inspector.get_table_names():
                logger.info("Patients table doesn't exist yet, will be created with correct enum values")
                return
            
            # Log current enum values for verification
            result = conn.execute(text("""
                SELECT COLUMN_TYPE 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'patients' 
                AND COLUMN_NAME = 'patient_category'
                AND TABLE_SCHEMA = DATABASE()
            """))
            
            row = result.fetchone()
            if row:
                column_type = row[0]
                logger.info(f"Current patient_category type: {column_type}")
                    
    except Exception as e:
        logger.error(f"Error checking patient_category enum: {e}")
        pass

def initialize_database():
    """Initialize database tables"""
    try:
        # Check current enum values (for logging only)
        check_patient_category_enum()
        
        # Create/update all tables
        logger.info("Creating/updating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialization completed successfully")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

if __name__ == "__main__":
    initialize_database()
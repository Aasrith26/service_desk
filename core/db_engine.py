"""
Database engine configuration
Shared database engine to avoid circular imports
"""

import os
from sqlmodel import create_engine
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# PostgreSQL Connection for Railway (Public URL)
# Use the DATABASE_PUBLIC_URL from Railway variables
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:ZqNTDiWFLVjpIaOlPbaMqvDawADkklLn@tramway.proxy.rlwy.net:54361/railway"
)

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL, 
    echo=False,
    pool_pre_ping=True,  # Verify connections before using
    pool_size=5,
    max_overflow=10
)

from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, JSON, Boolean
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# Enhanced PostgreSQL configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgresql:sum12345@localhost:5432/sentientgeeks_ats_resume_matcher")

# PostgreSQL specific engine configuration
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=0,
    pool_pre_ping=True,
    echo=False  # Set to True for SQL debugging
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Create all tables
def create_tables():
    Base.metadata.create_all(bind=engine)

# Drop all tables (for reset)
def drop_tables():
    Base.metadata.drop_all(bind=engine)

import os
import sys
from sqlalchemy import create_engine
from dotenv import load_dotenv
from backend.app.models.history_models import MatchingHistory


# Load environment variables
load_dotenv()

# Add backend to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.app.models.database import Base, engine
from backend.app.models.jd_models import JobDescription, JDStructuringSession
from backend.app.models.resume_models import Resume, MatchingResult

def initialize_database():
    """Initialize the PostgreSQL database with tables"""
    try:
        print("🚀 Initializing PostgreSQL database...")
        
        # Test connection
        with engine.connect() as connection:
            print("✅ Database connection successful!")
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("✅ All database tables created successfully!")
        
        print("\n📋 Created tables:")
        print("- job_descriptions")
        print("- jd_structuring_sessions") 
        print("- resumes")
        print("- matching_results")
        print("- matching_history") 
        print("\n🎉 Database initialization completed!")
        print("Your ATS Resume Matcher is ready to use with PostgreSQL!")
        
    except Exception as e:
        print(f"❌ Database initialization error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = initialize_database()
    if success:
        print("\n🏃‍♂️ You can now run your application:")
        print("python run.py")
    else:
        print("\n⚠️ Please check your database configuration and try again.")

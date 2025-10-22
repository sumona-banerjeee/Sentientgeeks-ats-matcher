import sys
import os
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from sqlalchemy import create_engine
from backend.app.models.database import Base
from backend.app.models.jd_library_models import JDLibrary, JDUsageHistory

def create_jd_library_tables():
    """Create JD Library tables in the database"""
    try:
        DATABASE_URL = os.getenv("DATABASE_URL")
        
        if not DATABASE_URL:
            raise Exception("DATABASE_URL not found in environment variables")
        
        print("Connecting to database...")
        engine = create_engine(DATABASE_URL)
        
        print("\nCreating JD Library tables...")
        
        # Create only the new tables (won't affect existing tables)
        JDLibrary.__table__.create(engine, checkfirst=True)
        JDUsageHistory.__table__.create(engine, checkfirst=True)
        
        print("JD Library tables created successfully!")
        print("\nCreated tables:")
        print("  - jd_library")
        print("  - jd_usage_history")
        
        print("\nJD Library feature is now available!")
        print("   - Save processed JDs for reuse")
        print("   - Upload resumes against saved JDs")
        print("   - Track JD usage history")
        
        return True
        
    except Exception as e:
        print(f"Error creating JD Library tables: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("JD Library Database Migration")
    print("=" * 60)
    
    success = create_jd_library_tables()
    
    if success:
        print("\nMigration completed successfully!")
        print("You can now use the JD Library feature.")
    else:
        print("\nMigration failed!")
        print("Please check the error messages above.")
    
    print("=" * 60)
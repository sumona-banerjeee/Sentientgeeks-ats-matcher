import uvicorn
import os
import sys
from dotenv import load_dotenv

# Loading environment variables
load_dotenv()

# Adding the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    # Ensuring data directories exist
    os.makedirs("./data/uploads/jds", exist_ok=True)
    os.makedirs("./data/uploads/resumes", exist_ok=True)
    os.makedirs("./data/processed", exist_ok=True)
    
    print("Starting SentientGeeks ATS Resume Matcher...")
    
    # Checking database type from environment
    database_url = os.getenv("DATABASE_URL", "")
    if "postgresql" in database_url.lower():
        print("Database: PostgreSQL (Production Ready)")
    elif "sqlite" in database_url.lower():
        print("Database: SQLite (Development Mode)")
    else:
        print("Database: Unknown")
    
    print("Server will be available at: http://localhost:8000")
    
    # Running the application
    uvicorn.run(
        "backend.app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        log_level="info"
    )

if __name__ == "__main__":
    main()

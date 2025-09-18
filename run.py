import uvicorn
import os
import sys

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    # Ensure data directories exist
    os.makedirs("./data/uploads/jds", exist_ok=True)
    os.makedirs("./data/uploads/resumes", exist_ok=True)
    os.makedirs("./data/processed", exist_ok=True)
    
    print("Starting SentientGeeks ATS Resume Matcher...")
    print("Database: SQLite (Development Mode)")
    print("Server will be available at: http://localhost:8000")
    
    # Run the application
    uvicorn.run(
        "backend.app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    main()

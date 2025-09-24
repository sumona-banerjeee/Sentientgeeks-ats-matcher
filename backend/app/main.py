from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
import os

app = FastAPI(
    title="SentientGeeks ATS Resume Matcher",
    description="AI-powered ATS Resume Matching System",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create directories
os.makedirs("./data/uploads/jds", exist_ok=True)
os.makedirs("./data/uploads/resumes", exist_ok=True)
os.makedirs("./data/processed", exist_ok=True)
os.makedirs("./frontend/static", exist_ok=True)
os.makedirs("./frontend/static/assets", exist_ok=True)
os.makedirs("./frontend/static/assets/images", exist_ok=True)
os.makedirs("./frontend/templates", exist_ok=True)

# Static files and templates
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
templates = Jinja2Templates(directory="frontend/templates")

@app.get("/")
async def read_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "SentientGeeks ATS is running!"}

@app.get("/favicon.ico")
async def favicon():
    """Return a simple favicon or 204 No Content"""
    # Try different favicon locations
    favicon_paths = [
        "frontend/static/assets/images/favicon.ico",
        "frontend/static/favicon.ico",
        "frontend/static/logo.png"
    ]
    
    for path in favicon_paths:
        if os.path.exists(path):
            media_type = "image/x-icon" if path.endswith(".ico") else "image/png"
            return FileResponse(path, media_type=media_type)
    
    # Return 204 No Content if no favicon is found
    return Response(status_code=204)

# Create tables on startup
@app.on_event("startup")
async def create_tables():
    try:
        # Import here to avoid circular imports
        from backend.app.models.database import engine, Base
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully!")
    except Exception as e:
        print(f"❌ Error creating database tables: {e}")

# Import and include routers after app initialization
try:
    from backend.app.api import jd_routes, resume_routes, matching_routes
    
    # Add interview routes import
    try:
        from backend.app.api import interview_routes
        app.include_router(interview_routes.router)
        print("✅ Interview routes loaded successfully!")
    except ImportError:
        print("⚠️ Interview routes not found - please create interview_routes.py")
    
    app.include_router(jd_routes.router)
    app.include_router(resume_routes.router)
    app.include_router(matching_routes.router)
    print("✅ API routes loaded successfully!")
    
except Exception as e:
    print(f"❌ Error loading API routes: {e}")
    import traceback
    traceback.print_exc()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

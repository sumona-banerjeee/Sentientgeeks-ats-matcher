from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
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

# Create tables on startup
@app.on_event("startup")
async def create_tables():
    try:
        from .models.database import engine, Base
        Base.metadata.create_all(bind=engine)
        print(" Database tables created successfully!")
    except Exception as e:
        print(f"Error creating database tables: {e}")

# Import and include routers after app initialization
try:
    from .api import jd_routes, resume_routes, matching_routes
    app.include_router(jd_routes.router)
    app.include_router(resume_routes.router)
    app.include_router(matching_routes.router)
    print("API routes loaded successfully!")
except Exception as e:
    print(f"Error loading API routes: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


from fastapi.responses import FileResponse
@app.get("/favicon.ico")
async def favicon():
    # Use any small image file you have
    return FileResponse("frontend/static/logo.png", media_type="image/png")

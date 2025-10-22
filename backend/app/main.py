from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
import os
import uvicorn


app = FastAPI(
    title="SentientGeeks ATS Resume Matcher API",
    description="RESTful API for AI-powered ATS Resume Matching System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)



app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],    
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



os.makedirs("./data/uploads/jds", exist_ok=True)
os.makedirs("./data/uploads/resumes", exist_ok=True)
os.makedirs("./data/processed", exist_ok=True)



app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
app.mount("/css", StaticFiles(directory="frontend/static/css"), name="css")
app.mount("/js", StaticFiles(directory="frontend/static/js"), name="js")



@app.get("/", include_in_schema=False)
async def serve_login():
    """Serve login page at root - Frontend entry point"""
    return FileResponse("frontend/templates/login.html")


@app.get("/app", include_in_schema=False)
async def serve_app():
    """Serve main application after login"""
    return FileResponse("frontend/templates/index.html")


@app.get("/login", include_in_schema=False)
async def serve_login_alt():
    """Alternative login URL"""
    return FileResponse("frontend/templates/login.html")



@app.get("/api")
async def api_root():
    """API root - shows API information"""
    return {
        "name": "SentientGeeks ATS Resume Matcher API",
        "version": "1.0.0",
        "status": "online",
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc",
            "openapi": "/openapi.json"
        },
        "endpoints": {
            "authentication": "/api/users",
            "job_descriptions": "/api/jd",
            "jd_library": "/api/jd-library",
            "resumes": "/api/resumes",
            "matching": "/api/match",
            "history": "/api/history",
            "interviews": "/api/interviews"
        }
    }


@app.get("/api/health")
async def health_check():
    """API health check endpoint"""
    return {
        "status": "healthy",
        "service": "SentientGeeks ATS API",
        "version": "1.0.0"
    }


@app.get("/api/status")
async def api_status():
    """Detailed API status"""
    return {
        "status": "online",
        "database": "connected",
        "api_version": "1.0.0",
        "endpoints_count": 26,
        "documentation": "/docs"
    }


@app.get("/health")
async def health_check_legacy():
    """Legacy health check"""
    return {"status": "healthy"}



@app.on_event("startup")
async def create_tables():
    """Initialize database tables on startup"""
    try:
        from backend.app.models.database import engine, Base
        Base.metadata.create_all(bind=engine)
        print("Database tables created successfully!")
    except Exception as e:
        print(f"Error creating database tables: {e}")



try:
    from backend.app.api import (
        jd_routes,
        resume_routes,
        matching_routes,
        interview_routes,
        history_routes,
        user_routes,
        jd_library_routes,  
    )

    app.include_router(user_routes.router, tags=["Authentication"])
    app.include_router(jd_routes.router, tags=["Job Descriptions"])
    app.include_router(jd_library_routes.router, tags=["JD Library"]) 
    app.include_router(resume_routes.router, tags=["Resumes"])
    app.include_router(matching_routes.router, tags=["Matching"])
    app.include_router(history_routes.router, tags=["History"])
    app.include_router(interview_routes.router, tags=["Interviews"])

    print("All API routes loaded successfully!")

except Exception as e:
    print(f"Error loading API routes: {e}")
    import traceback
    traceback.print_exc()


# Global setting for Increasing max upload size to 500MB
app.max_request_size = 500 * 1024 * 1024  # 500 MB



# CUSTOM ERROR HANDLER

@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Handle 404 errors with proper JSON response"""
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "message": f"The requested URL {request.url.path} was not found",
            "documentation": "/docs"
        }
    )


#Main entry point
if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🚀 Starting SentientGeeks ATS Resume Matcher API...")
    print("=" * 70)
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=True,
        limit_max_request_size=500 * 1024 * 1024  # Ensures 500MB limit in Uvicorn too
    )

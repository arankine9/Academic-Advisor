from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import os
import logging
from pathlib import Path
from backend.api.routes import router
from backend.routes import program_routes, recommendations
from backend.core.database import Base, engine, SessionLocal
from backend.services.courses import initialize_courses_from_json
from backend.services.majors import initialize_majors_from_list

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Get ABSOLUTE paths to ensure we're serving the right files
BASE_DIR = Path(__file__).resolve().parent  # Project root directory
DIST_DIR = BASE_DIR / "frontend" / "dist"   # Production build directory
INDEX_PATH = DIST_DIR / "index.html"        # Production index.html
ASSETS_DIR = DIST_DIR / "assets"            # Bundled assets directory

# Log paths for debugging
logger.info(f"Base directory: {BASE_DIR}")
logger.info(f"Dist directory: {DIST_DIR}")
logger.info(f"Dist directory exists: {DIST_DIR.exists()}")
logger.info(f"Production index.html path: {INDEX_PATH}")
logger.info(f"Production index.html exists: {INDEX_PATH.exists()}")
logger.info(f"Assets directory: {ASSETS_DIR}")
logger.info(f"Assets directory exists: {ASSETS_DIR.exists()}")

if ASSETS_DIR.exists():
    logger.info(f"Assets directory contents: {os.listdir(ASSETS_DIR)}")

# Create FastAPI app
app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes here if needed
app.include_router(router, prefix="/api")

# Include our new routers
app.include_router(program_routes.router, prefix="/api")
app.include_router(recommendations.router, prefix="/api")

@app.on_event("startup")
async def startup_event():
    # Create database tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    # Initialize session
    db = SessionLocal()
    try:
        # Initialize courses from majors.json
        initialize_courses_from_json(db)
        
        # Initialize majors from majors_list.json
        initialize_majors_from_list(db)
        logger.info("Database initialization complete.")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
    finally:
        db.close()

# Serve static files from the DIST_DIR directory
if DIST_DIR.exists():
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")

# Catch-all route to serve the frontend, this must be the last route
@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    logger.info(f"Requested path: /{full_path}")
    
    # If the path is to a known API endpoint, return 404
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API route not found")
    
    if DIST_DIR.exists():
        logger.info(f"Serving from production build in {DIST_DIR}")
        # Serve the index.html for any non-API route
        return FileResponse(INDEX_PATH)
    else:
        logger.warning("Production build not found, redirecting to development server")
        # Redirect to development server
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=f"http://localhost:5173/{full_path}")

# Run the application
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    logger.info(f"Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port) 
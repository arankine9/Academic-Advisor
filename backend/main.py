from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import os
import logging
import sys
import subprocess
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.core.database import get_db, create_tables
from backend.services.courses import initialize_courses_from_json
from backend.api.routes import router as api_router

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
FRONTEND_DIST_DIR = os.path.join("frontend", "dist")

# Function to build the frontend
def build_frontend():
    frontend_dir = Path("frontend").absolute()
    
    # Check if npm is installed
    try:
        subprocess.run(['npm', '--version'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.error("Error: npm is not installed. Please install Node.js and npm.")
        return False
        
    # Check if node_modules exists, if not, install dependencies
    if not (frontend_dir / 'node_modules').exists():
        logger.info("Installing React dependencies...")
        try:
            subprocess.run(['npm', 'install'], cwd=frontend_dir, check=True)
            logger.info("Dependencies installed successfully.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Error installing dependencies: {e}")
            return False
    
    # Build the React frontend
    logger.info("Building React frontend...")
    try:
        subprocess.run(['npm', 'run', 'build'], cwd=frontend_dir, check=True)
        logger.info("Frontend built successfully.")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error building frontend: {e}")
        return False

# Define lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create tables and initialize courses
    create_tables()
    db = next(get_db())
    initialize_courses_from_json(db)
    
    # Build the frontend if needed
    if not os.path.exists(FRONTEND_DIST_DIR):
        build_frontend()
    yield
    # Shutdown: Clean up resources if needed
    pass

# Create FastAPI app with lifespan
app = FastAPI(lifespan=lifespan, title="Academic Advisor API")

# Add CORS middleware - limited to what's needed for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Consider restricting this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the API router with prefix
app.include_router(api_router, prefix="/api")

# Mount static files
if os.path.exists(FRONTEND_DIST_DIR):
    # Mount only the assets from dist directory
    assets_dir = os.path.join(FRONTEND_DIST_DIR, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
        logger.info(f"Mounted assets directory: {assets_dir}")
    else:
        logger.warning(f"Assets directory not found: {assets_dir}")
    
    # Static directory mounting removed since we're now using React's asset system

# Root route handler - serves the React app
@app.get("/")
async def root():
    if os.path.exists(os.path.join(FRONTEND_DIST_DIR, "index.html")):
        return FileResponse(os.path.join(FRONTEND_DIST_DIR, "index.html"))
    else:
        return {
            "error": "React frontend is not built",
            "message": "The application is starting up. Please try again in a moment."
        }

# Serve the React app for all other routes
@app.get("/{full_path:path}")
async def serve_react(full_path: str):
    # Skip API routes
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not Found")
    
    # Return the index.html for all frontend routes (let React handle routing)
    if os.path.exists(FRONTEND_DIST_DIR):
        return FileResponse(os.path.join(FRONTEND_DIST_DIR, "index.html"))
    else:
        raise HTTPException(status_code=503, detail="Application is starting up. Please try again in a moment.")

# Run the application
if __name__ == "__main__":
    import uvicorn
    
    # Start FastAPI server
    port = int(os.getenv("PORT", "8000"))
    logger.info(f"Starting FastAPI server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
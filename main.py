from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import os
import logging
from pathlib import Path
from backend.api.routes import router

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

# Explicitly serve the production index.html for the root path
@app.get("/")
async def serve_index():
    if not INDEX_PATH.exists():
        logger.error(f"Production index.html not found at {INDEX_PATH}")
        raise HTTPException(status_code=404, detail="Index file not found")
    logger.info(f"Serving production index.html from {INDEX_PATH}")
    return FileResponse(INDEX_PATH)

# Mount the assets directory for bundled JavaScript and CSS
if ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")
    logger.info(f"Mounted assets directory: {ASSETS_DIR}")

# Mount vite.svg if it exists
vite_svg_path = DIST_DIR / "vite.svg"
if vite_svg_path.exists():
    @app.get("/vite.svg")
    async def serve_vite_svg():
        logger.info(f"Serving vite.svg from {vite_svg_path}")
        return FileResponse(vite_svg_path, media_type="image/svg+xml")

# Serve the SPA index for all other routes (client-side routing)
@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    # Skip API routes
    if full_path.startswith("api/"):
        logger.info(f"API route: {full_path}")
        raise HTTPException(status_code=404, detail="API route not found")
    
    # Serve the production index.html for client-side routing
    logger.info(f"Serving production index.html for path: /{full_path}")
    return FileResponse(INDEX_PATH)

# Run the application
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    logger.info(f"Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
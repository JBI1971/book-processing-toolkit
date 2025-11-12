"""
FastAPI backend for Book Review Interface
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import routers
from api.works import router as works_router
from api.translate import router as translate_router
from api.edit import router as edit_router
from api.toc import router as toc_router
from api.analysis import router as analysis_router

# Create FastAPI app
app = FastAPI(
    title="Book Review API",
    description="API for reviewing and editing processed book JSON files",
    version="1.0.0"
)

# Add CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vite and Create React App defaults
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(works_router, prefix="/api", tags=["works"])
app.include_router(translate_router, prefix="/api", tags=["translation"])
app.include_router(edit_router, prefix="/api", tags=["editing"])
app.include_router(toc_router, prefix="/api", tags=["toc"])
app.include_router(analysis_router, prefix="/api", tags=["analysis"])


@app.get("/")
async def root():
    """Root endpoint - API information"""
    return {
        "name": "Book Review API",
        "version": "1.0.0",
        "endpoints": {
            "works": "/api/works",
            "translate": "/api/translate",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("BACKEND_PORT", 8000))

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        reload=True,  # Enable auto-reload during development
        log_level="info"
    )

"""
Main FastAPI Application
Entry point for the Intelligent Tutoring System API.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.api.v1 import api_router

# Setup logging
setup_logging(level=settings.LOG_LEVEL)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("=" * 60)
    logger.info(f"Starting {settings.APP_NAME}")
    logger.info(f"Debug Mode: {settings.DEBUG}")
    logger.info(f"API Prefix: {settings.API_V1_PREFIX}")
    logger.info("=" * 60)
    
    # Ensure storage directories exist
    settings.STORAGE_BASE_DIR.mkdir(parents=True, exist_ok=True)
    settings.DOCUMENT_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    settings.VECTOR_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    settings.MEMORY_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    
    logger.info("✓ Storage directories initialized")
    
    yield
    
    # Shutdown
    logger.info(f"Shutting down {settings.APP_NAME}")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered intelligent tutoring system with document-based learning",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# ============================================================================
# CORS CONFIGURATION - MUST BE FIRST MIDDLEWARE
# ============================================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, PUT, DELETE, OPTIONS, etc.)
    allow_headers=["*"],  # Allow all headers
    expose_headers=["*"],
    max_age=3600,  # Cache preflight requests for 1 hour
)

# ============================================================================
# INCLUDE ROUTERS - AFTER CORS
# ============================================================================
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Intelligent Tutoring System API",
        "version": "1.0.0",
        "docs": "/api/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.APP_NAME
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
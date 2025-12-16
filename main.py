"""
Builder AI Engine - Python FastAPI Implementation
Main application entry point
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn

from app.api.routes import router
from app.config.settings import settings
from app.core.app_state_manager import app_state_manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    print(f"🚀 Starting Builder AI Engine on port {settings.PORT}")
    print(f"📦 Sandbox Provider: {settings.SANDBOX_PROVIDER}")
    print(f"🤖 Default AI Model: {settings.DEFAULT_AI_MODEL}")
    yield
    # Cleanup on shutdown
    await app_state_manager.cleanup_all()
    print("👋 Shutting down Builder AI Engine")

# Initialize FastAPI app
app = FastAPI(
    title="Builder AI Engine API",
    description="Pure Python AI Engine for code generation and sandbox management",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": str(exc),
            "message": "Internal server error"
        }
    )

# Include API routes
app.include_router(router, prefix="/api")

# Health check endpoint
@app.get("/")
async def root():
    return {
        "message": "Builder AI Engine - Python Edition",
        "status": "running",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "builder-ai-engine",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )

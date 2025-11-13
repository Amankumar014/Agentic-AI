"""
Baby Monitor Backend - Main Application Entrypoint
FastAPI server for baby monitoring with Azure Vision AI integration.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
from pathlib import Path

from src.api import router
from src.models import init_db
from src.config import get_settings, ensure_directories


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI application.
    Handles startup and shutdown events.
    """
    # Startup
    print("=" * 60)
    print("BABY MONITOR BACKEND - STARTING UP")
    print("=" * 60)
    
    # Ensure temp directory exists
    print("\n📁 Ensuring directories exist...")
    ensure_directories()
    print("✅ Directories ready")
    
    # Initialize database
    print("\n🗄️  Initializing database...")
    init_db()
    print("✅ Database initialized")
    
    # Load settings to validate configuration
    settings = get_settings()
    print("\n⚙️  Configuration loaded:")
    print(f"   • Azure Endpoint: {settings.AZURE_OPENAI_ENDPOINT or '(not configured)'}")
    print(f"   • Database: {settings.DATABASE_URL}")
    print(f"   • Frame Interval: {settings.FRAME_ANALYZE_INTERVAL}s")
    print(f"   • SMTP Host: {settings.SMTP_HOST or '(not configured)'}")
    print(f"   • Twilio SID: {settings.TWILIO_SID or '(not configured)'}")
    
    print("\n" + "=" * 60)
    print("🚀 Baby Monitor Backend Ready!")
    print("=" * 60)
    print("\nAPI Documentation available at:")
    print("  • Swagger UI: http://localhost:8000/docs")
    print("  • ReDoc: http://localhost:8000/redoc")
    print("\nEndpoints:")
    print("  • POST /api/v1/frames/  - Upload and analyze frame")
    print("  • GET  /api/v1/alerts/  - Get recent alerts")
    print("  • GET  /api/v1/logs/    - Get frame analysis logs")
    print("  • GET  /api/v1/health/  - Health check")
    print("  • GET  /api/v1/stats/   - System statistics")
    print("\n" + "=" * 60 + "\n")
    
    yield
    
    # Shutdown
    print("\n" + "=" * 60)
    print("BABY MONITOR BACKEND - SHUTTING DOWN")
    print("=" * 60)
    print("✅ Cleanup complete")


# Create FastAPI application
app = FastAPI(
    title="Baby Monitor API",
    description="Backend API for AI-powered baby monitoring system with Azure Vision",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(router, prefix="/api/v1", tags=["Baby Monitor"])

# Mount static files (if directory exists)
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
async def root():
    """
    Serve the web interface for phone camera uploads.
    """
    static_file = Path(__file__).parent / "static" / "index.html"
    if static_file.exists():
        return FileResponse(static_file)
    
    # Fallback to API info if no static files
    return {
        "service": "Baby Monitor API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/api/v1/health/"
    }


if __name__ == "__main__":
    # Run the application with Uvicorn
    print("\n🚀 Starting Baby Monitor Backend Server...")
    print("Press Ctrl+C to stop\n")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Enable auto-reload during development
        log_level="info"
    )

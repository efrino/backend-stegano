import os
import logging
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError

# Load environment variables first
load_dotenv()

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL")

# App Runner port configuration
PORT = int(os.getenv("PORT", 8000))

# Optimize for ML workloads
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["PYTHONUNBUFFERED"] = "1"

# Logging setup with better formatting for App Runner
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Configure logging for App Runner
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "app.log"), encoding='utf-8'),
        logging.StreamHandler(sys.stdout)  # Use stdout for App Runner logs
    ]
)

logger = logging.getLogger(__name__)

# Global variables for database
engine = None
SessionLocal = None

def verify_ml_dependencies():
    """Verify that ML dependencies are properly installed"""
    try:
        import torch
        import torchvision
        import cv2
        import skimage
        import imagehash
        import numpy as np
        
        logger.info("ML Dependencies Check:")
        logger.info(f"- PyTorch version: {torch.__version__}")
        logger.info(f"- TorchVision version: {torchvision.__version__}")
        logger.info(f"- OpenCV version: {cv2.__version__}")
        logger.info(f"- Scikit-Image version: {skimage.__version__}")
        logger.info(f"- NumPy version: {np.__version__}")
        logger.info("SUCCESS: All ML dependencies loaded successfully")
        return True
        
    except ImportError as e:
        logger.error(f"FAILED: ML dependency import error: {e}")
        return False

def create_database_engine():
    """Create database engine optimized for AWS RDS on App Runner"""
    if not DATABASE_URL:
        logger.error("DATABASE_URL not found in environment variables")
        return None
    
    try:
        # AWS RDS optimized connection parameters for App Runner
        connect_args = {}
        
        # Add SSL configuration for AWS RDS if not in URL
        if "amazonaws.com" in DATABASE_URL and "sslmode" not in DATABASE_URL:
            connect_args["sslmode"] = "require"
            logger.info("AWS RDS detected - enabling SSL")
        
        # Optimized for App Runner with ML workloads
        db_engine = create_engine(
            DATABASE_URL,
            pool_pre_ping=True,           # Verify connections before use
            pool_recycle=1800,            # Shorter recycle for App Runner (30 min)
            pool_timeout=30,              # Shorter timeout for App Runner
            max_overflow=10,              # Reasonable overflow for App Runner
            pool_size=3,                  # Smaller pool for App Runner with ML workloads
            echo=False,                   # Set to True for SQL debugging
            connect_args=connect_args
        )
        
        # Test the connection
        logger.info("Testing AWS RDS connection...")
        with db_engine.connect() as conn:
            result = conn.execute(text("SELECT version(), current_database(), current_user"))
            row = result.fetchone()
            logger.info(f"SUCCESS: Connected to database '{row[1]}' as user '{row[2]}'")
            logger.info(f"PostgreSQL version: {row[0]}")
        
        return db_engine
        
    except OperationalError as e:
        logger.error(f"FAILED: Could not connect to AWS RDS database: {e}")
        logger.error("AWS RDS Connection Troubleshooting:")
        logger.error("1. Check if RDS security group allows App Runner access")
        logger.error("2. Verify DATABASE_URL environment variable is set correctly")
        logger.error("3. Ensure RDS instance is publicly accessible")
        logger.error("4. Check RDS instance status is 'Available'")
        return None
    except Exception as e:
        logger.error(f"Unexpected database error: {e}")
        return None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Steganography API on AWS App Runner...")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Platform: App Runner")
    logger.info(f"Port: {PORT}")
    
    # Verify ML dependencies first
    logger.info("Verifying ML dependencies...")
    if not verify_ml_dependencies():
        logger.error("CRITICAL: ML dependencies not properly installed")
        sys.exit(1)
    
    # Initialize database connection
    global engine, SessionLocal
    engine = create_database_engine()
    
    if engine is None:
        logger.error("CRITICAL: Failed to connect to database. Server will exit.")
        sys.exit(1)
    else:
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        # Import here to avoid circular imports
        try:
            from app.db.database import Base
            logger.info("Creating/verifying database tables...")
            Base.metadata.create_all(bind=engine)
            logger.info("SUCCESS: Database tables created/verified successfully")
        except Exception as e:
            logger.error(f"FAILED: Could not create database tables: {e}")
            sys.exit(1)
    
    logger.info("SUCCESS: Steganography API startup complete - Ready for requests!")
    yield
    
    # Shutdown
    logger.info("Shutting down Steganography API...")

# Create FastAPI app with lifespan
app = FastAPI(
    title="Steganography API",
    description="Advanced steganography API with ML capabilities on AWS App Runner",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration optimized for App Runner
origins = [
    "http://localhost:3000",
    "http://192.168.56.1:3000", 
    "https://www.pajangan.online",
    "https://pajangan.online",
    "https://mn6wdkh7yy.ap-southeast-1.awsapprunner.com",  # Your App Runner URL
    # Add any other frontend domains you need
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enhanced health check endpoint for App Runner
@app.get("/health")
async def health_check():
    if engine is None:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT current_database(), current_user, version()"))
            row = result.fetchone()
            
            # Check ML dependencies
            ml_status = "available"
            try:
                import torch
                import cv2
                torch_device = "cpu"
                ml_status = "available"
            except:
                ml_status = "unavailable"
            
            return {
                "status": "healthy",
                "database": "connected",
                "db_name": row[0],
                "db_user": row[1],
                "environment": "production",
                "platform": "aws_apprunner",
                "ml_dependencies": ml_status,
                "torch_device": torch_device if ml_status == "available" else None,
                "timestamp": "2025-08-06T13:00:00Z"
            }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Steganography API with ML capabilities is running on AWS App Runner!",
        "docs": "/docs",
        "health": "/health",
        "version": "1.0.0",
        "features": ["steganography", "image_processing", "machine_learning"]
    }

# Import and include routers
try:
    from app.api.routes import users, auth, uploads, explore, payments, extract, likes, artwork_me
    from app.api.routes.artworks import router as artworks_router
    from app.api.routes import purchase
    
    app.include_router(users.router, prefix="/api/users", tags=["Users"])
    app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
    app.include_router(uploads.router, prefix="/api/artwork", tags=["Artworks"])
    app.include_router(artworks_router, prefix="/api/artworks", tags=["Artworks"])
    app.include_router(explore.router, prefix="/api/explores", tags=["Explores"])
    app.include_router(artwork_me.router, prefix="/api", tags=["artwork"])
    app.include_router(payments.router, prefix="/api/payments", tags=["Payments"])
    app.include_router(extract.router, prefix="/api/extract", tags=["Extract"])
    app.include_router(likes.router, prefix="/api/likes", tags=["Likes"])
    app.include_router(purchase.router, prefix="/api/my", tags=["Purchase"])
    
    logger.info("SUCCESS: All API routers included successfully")
    
except ImportError as e:
    logger.error(f"FAILED: Could not import routers: {e}")
    logger.error("Please check your project structure and dependencies")

# Mount static files
static_dir = "static"
if not os.path.exists(static_dir):
    os.makedirs(static_dir)
    logger.info(f"Created static directory: {static_dir}")

app.mount("/static", StaticFiles(directory=static_dir), name="static")

if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting Steganography API server on port {PORT}...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=PORT,
        reload=False,          # Disable reload for production
        workers=1,             # Single worker for App Runner
        access_log=True,       # Enable access logs for App Runner
        log_level="info"       # Set log level
    )
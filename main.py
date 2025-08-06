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

# Logging setup
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "app.log")),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Global variables for database
engine = None
SessionLocal = None

def create_database_engine():
    """Create database engine with error handling"""
    if not DATABASE_URL:
        logger.error("DATABASE_URL not found in environment variables")
        return None
    
    try:
        db_engine = create_engine(
            DATABASE_URL,
            pool_pre_ping=True,
            pool_recycle=300,
            pool_timeout=30,
            max_overflow=10,
            echo=False
        )
        
        # Test the connection
        with db_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            logger.info("Successfully connected to database")
        
        return db_engine
        
    except OperationalError as e:
        logger.error(f"Failed to connect to database: {e}")
        
        # Try localhost as fallback
        if "35.197.149.115" in DATABASE_URL:
            logger.info("Attempting localhost fallback...")
            localhost_url = DATABASE_URL.replace("35.197.149.115", "localhost")
            try:
                db_engine = create_engine(localhost_url, pool_pre_ping=True)
                with db_engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                logger.info("Connected to localhost database")
                return db_engine
            except Exception:
                logger.error("Localhost fallback failed")
        
        return None
    except Exception as e:
        logger.error(f"Unexpected database error: {e}")
        return None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting FastAPI server...")
    
    global engine, SessionLocal
    engine = create_database_engine()
    
    if engine is None:
        logger.error("Failed to connect to database. Server will start but database operations will fail.")
    else:
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        # Import here to avoid circular imports
        try:
            from app.db.database import Base
            Base.metadata.create_all(bind=engine)
            logger.info("Database tables created/verified")
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
    
    logger.info("Server startup complete")
    yield
    
    # Shutdown
    logger.info("Server shutdown complete")

# Create FastAPI app with lifespan
app = FastAPI(
    title="Steganography API",
    description="API for steganography application",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
origins = [
    "http://localhost:3000",
    "http://192.168.56.1:3000",
    "https://www.pajangan.online",
    "https://pajangan.online",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health_check():
    if engine is None:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Database connection failed")

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
    
    logger.info("All routers included successfully")
    
except ImportError as e:
    logger.error(f"Failed to import routers: {e}")

# Mount static files
static_dir = "static"
if not os.path.exists(static_dir):
    os.makedirs(static_dir)
    logger.info(f"Created static directory: {static_dir}")

app.mount("/static", StaticFiles(directory=static_dir), name="static")
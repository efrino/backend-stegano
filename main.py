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
        logging.FileHandler(os.path.join(LOG_DIR, "app.log"), encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Global variables for database
engine = None
SessionLocal = None

def create_database_engine():
    """Create database engine optimized for AWS RDS"""
    if not DATABASE_URL:
        logger.error("DATABASE_URL not found in environment variables")
        return None
    
    try:
        # AWS RDS optimized connection parameters
        connect_args = {}
        
        # Add SSL configuration for AWS RDS if not in URL
        if "amazonaws.com" in DATABASE_URL and "sslmode" not in DATABASE_URL:
            connect_args["sslmode"] = "require"
            logger.info("AWS RDS detected - enabling SSL")
        
        db_engine = create_engine(
            DATABASE_URL,
            pool_pre_ping=True,           # Verify connections before use
            pool_recycle=3600,            # Recycle connections every hour (AWS RDS timeout)
            pool_timeout=60,              # Wait up to 60 seconds for connection
            max_overflow=20,              # Allow more connections for production
            pool_size=10,                 # Base connection pool size
            echo=False,                   # Set to True for SQL debugging
            connect_args=connect_args     # SSL and other connection arguments
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
        
        # Provide helpful troubleshooting information for AWS RDS
        if "amazonaws.com" in DATABASE_URL:
            logger.error("AWS RDS Connection Troubleshooting:")
            logger.error("1. Check if the database instance is 'Available' in AWS Console")
            logger.error("2. Verify security group allows inbound connections on port 5432")
            logger.error("3. Confirm the database credentials are correct")
            logger.error("4. Check if your IP address is allowed in the security group")
            logger.error("5. Verify the database name exists")
        
        return None
    except Exception as e:
        logger.error(f"Unexpected database error: {e}")
        return None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting FastAPI server with AWS RDS...")
    
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
    
    logger.info("SUCCESS: Server startup complete - AWS RDS ready!")
    yield
    
    # Shutdown
    logger.info("Server shutdown complete")

# Create FastAPI app with lifespan
app = FastAPI(
    title="Steganography API",
    description="API for steganography application with AWS RDS",
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
            # More comprehensive health check for production
            result = conn.execute(text("SELECT current_database(), current_user, version()"))
            row = result.fetchone()
            
            return {
                "status": "healthy",
                "database": "connected",
                "db_name": row[0],
                "db_user": row[1],
                "environment": "production" if "amazonaws.com" in DATABASE_URL else "development",
                "timestamp": "2025-08-06T12:55:00Z"
            }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Database connection failed: {str(e)}")

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
    logger.info("Starting development server...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["app"]
    )
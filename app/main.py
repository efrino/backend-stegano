# import os
# import logging
# from fastapi import FastAPI
# from fastapi.staticfiles import StaticFiles
# from fastapi.middleware.cors import CORSMiddleware
# from dotenv import load_dotenv
# from app.db.database import Base, engine
# from app.api.routes import users, auth, uploads, explore, payments, extract, likes, artwork_me
# from app.api.routes.artworks import router as artworks_router
# from app.api.routes import purchase
# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker

# load_dotenv()


# app = FastAPI()

# DATABASE_URL = os.getenv("DATABASE_URL")

# engine = create_engine(DATABASE_URL)
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# # Base.metadata.create_all(bind=engine)

# # Logging setup
# LOG_DIR = "logs"
# os.makedirs(LOG_DIR, exist_ok=True)

# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
#     handlers=[
#         logging.FileHandler(os.path.join(LOG_DIR, "app.log")),
#         logging.StreamHandler()
#     ]
# )

# logger = logging.getLogger(__name__)
# logger.info("Server FastAPI dimulai...")

# # CORS
# origins = [
#     "http://localhost:3000",
#     "http://192.168.56.1:3000",
#     "https://www.pajangan.online",
# ]

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=origins,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


# app.include_router(users.router, prefix="/api/users", tags=["Users"])
# app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
# app.include_router(uploads.router, prefix="/api/artwork", tags=["Artworks"])
# app.include_router(artworks_router, prefix="/api/artworks", tags=["Artworks"])
# app.include_router(explore.router, prefix="/api/explores", tags=["Explores"])
# app.include_router(artwork_me.router, prefix="/api", tags=["artwork"])
# app.include_router(payments.router, prefix="/api/payments", tags=["Payments"])
# app.include_router(extract.router, prefix="/api/extract", tags=["Extract"])
# app.include_router(likes.router, prefix="/api/likes", tags=["Likes"])
# app.include_router(purchase.router, prefix="/api/my", tags=["Purchase"]) 
# app.mount("/static", StaticFiles(directory="static"), name="static")

import os
import logging
import sys
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError

# Load environment variables first
load_dotenv()

# Import after loading .env to ensure database URL is available
from app.db.database import Base, get_db
from app.api.routes import users, auth, uploads, explore, payments, extract, likes, artwork_me
from app.api.routes.artworks import router as artworks_router
from app.api.routes import purchase

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

def create_database_engine():
    """Create database engine with error handling"""
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        logger.error("DATABASE_URL not found in environment variables")
        sys.exit(1)
    
    try:
        engine = create_engine(
            database_url,
            pool_pre_ping=True,  # Verify connections before use
            pool_recycle=300,    # Recycle connections every 5 minutes
            pool_timeout=30,     # Wait up to 30 seconds for a connection
            max_overflow=10,     # Allow up to 10 connections beyond pool_size
            echo=False           # Set to True for SQL query logging
        )
        
        # Test the connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            logger.info(f"Successfully connected to database: {database_url.split('@')[1] if '@' in database_url else 'hidden'}")
        
        return engine
        
    except OperationalError as e:
        logger.error(f"Failed to connect to database: {e}")
        logger.error("Please check if:")
        logger.error("1. The database server is running")
        logger.error("2. The connection details in DATABASE_URL are correct")
        logger.error("3. The server accepts connections from your IP")
        logger.error("4. Firewall settings allow the connection")
        
        # Try localhost as fallback if remote connection fails
        if "35.197.149.115" in database_url:
            logger.info("Attempting to use localhost database as fallback...")
            localhost_url = database_url.replace("35.197.149.115", "localhost")
            try:
                engine = create_engine(localhost_url, pool_pre_ping=True)
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                logger.info("Successfully connected to localhost database")
                return engine
            except Exception as fallback_error:
                logger.error(f"Localhost fallback also failed: {fallback_error}")
        
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error creating database engine: {e}")
        sys.exit(1)

def create_app():
    """Create and configure FastAPI application"""
    app = FastAPI(
        title="Steganography API",
        description="API for steganography application",
        version="1.0.0"
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
    
    # Include routers
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
    
    # Mount static files
    static_dir = "static"
    if not os.path.exists(static_dir):
        os.makedirs(static_dir)
        logger.info(f"Created static directory: {static_dir}")
    
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    
    # Health check endpoint
    @app.get("/health")
    async def health_check():
        try:
            # Test database connection
            db = next(get_db())
            db.execute(text("SELECT 1"))
            db.close()
            return {"status": "healthy", "database": "connected"}
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            raise HTTPException(status_code=503, detail="Service unavailable")
    
    return app

def initialize_database():
    """Initialize database tables"""
    try:
        engine = create_database_engine()
        
        # Create tables
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        
        return engine
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        sys.exit(1)

# Initialize the application
logger.info("Starting FastAPI server...")

# Initialize database
engine = initialize_database()

# Create SessionLocal for dependency injection
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create FastAPI app
app = create_app()

# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info("Server startup complete")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Server shutdown complete")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["app"]
    )
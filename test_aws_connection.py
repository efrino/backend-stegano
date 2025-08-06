#!/usr/bin/env python3
"""
Test script for AWS RDS connection
Run this before starting your main application to verify connectivity
"""
import os
import sys
from dotenv import load_dotenv
import psycopg2
from sqlalchemy import create_engine, text

# Load environment variables
load_dotenv()

def test_psycopg2_connection():
    """Test direct psycopg2 connection"""
    print("🔍 Testing direct psycopg2 connection...")
    
    # Connection parameters
    host = "stegano.cvoi8i4o83ra.ap-southeast-1.rds.amazonaws.com"
    port = 5432
    database = "postgres"  # Connect to default database first
    username = "postgres"
    password = input("Enter your RDS password: ").strip()
    
    try:
        # Test connection
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=username,
            password=password,
            sslmode="require",
            connect_timeout=30
        )
        
        cursor = conn.cursor()
        
        # Get database info
        cursor.execute("SELECT version(), current_database(), current_user;")
        result = cursor.fetchone()
        
        print("✅ psycopg2 connection successful!")
        print(f"   PostgreSQL version: {result[0]}")
        print(f"   Connected to database: {result[1]}")
        print(f"   Connected as user: {result[2]}")
        
        # Check if steganography database exists
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = 'steganography';")
        db_exists = cursor.fetchone()
        
        if db_exists:
            print("✅ Database 'steganography' exists")
        else:
            print("⚠️  Database 'steganography' does not exist")
            create_db = input("Do you want to create it? (y/n): ").strip().lower()
            if create_db == 'y':
                cursor.execute("CREATE DATABASE steganography;")
                conn.commit()
                print("✅ Database 'steganography' created successfully")
        
        cursor.close()
        conn.close()
        
        return password
        
    except psycopg2.Error as e:
        print(f"❌ psycopg2 connection failed: {e}")
        print("\nTroubleshooting tips:")
        print("1. Check your password")
        print("2. Verify security group allows your IP address")
        print("3. Confirm RDS instance is running")
        print("4. Check if RDS instance is publicly accessible")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None

def test_sqlalchemy_connection(password):
    """Test SQLAlchemy connection"""
    print("\n🔍 Testing SQLAlchemy connection...")
    
    database_url = f"postgresql://postgres:{password}@stegano.cvoi8i4o83ra.ap-southeast-1.rds.amazonaws.com:5432/steganography?sslmode=require"
    
    try:
        engine = create_engine(
            database_url,
            pool_pre_ping=True,
            pool_recycle=3600,
            pool_timeout=60,
            echo=True  # Show SQL queries
        )
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version(), current_database(), current_user"))
            row = result.fetchone()
            
            print("✅ SQLAlchemy connection successful!")
            print(f"   Database: {row[1]}")
            print(f"   User: {row[2]}")
            
            # Test table creation
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS test_table (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
            
            # Test insert
            conn.execute(text("INSERT INTO test_table (name) VALUES ('test_connection')"))
            conn.commit()
            
            # Test select
            result = conn.execute(text("SELECT COUNT(*) FROM test_table"))
            count = result.fetchone()[0]
            print(f"✅ Test table operations successful (rows: {count})")
            
            # Cleanup
            conn.execute(text("DROP TABLE IF EXISTS test_table"))
            conn.commit()
            
        return True
        
    except Exception as e:
        print(f"❌ SQLAlchemy connection failed: {e}")
        return False

def generate_env_file(password):
    """Generate .env file with correct DATABASE_URL"""
    print("\n📝 Generating .env configuration...")
    
    database_url = f"postgresql://postgres:{password}@stegano.cvoi8i4o83ra.ap-southeast-1.rds.amazonaws.com:5432/steganography?sslmode=require"
    
    env_content = f"""# AWS RDS Production Configuration
DATABASE_URL={database_url}

# API Configuration  
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
BACKEND_API_BASE_URL=http://localhost:8000
FRONTEND_BASE_URL=https://pajangan.online

# JWT Configuration
SECRET_KEY=09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080

# Midtrans Payment Configuration
MIDTRANS_SERVER_KEY=SB-Mid-server-h0ioErmlY553Kp2KMHS_FRGF
MIDTRANS_CLIENT_KEY=SB-Mid-client-D_uap6a6bGmgKEJM
MIDTRANS_NOTIFICATION_URL_BASE=https://846a5b6b4aa1.ngrok-free.app/api/payments/payment-callback

# Email Configuration
MAIL_USERNAME=artwork.portfolio.rights@gmail.com
MAIL_PASSWORD=bmchbakpcysvlrxf 
MAIL_FROM=artwork.portfolio.rights@gmail.com
MAIL_PORT=587
MAIL_SERVER=smtp.gmail.com
MAIL_STARTTLS=True
MAIL_SSL_TLS=False 
"""
    
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print("✅ .env file updated with AWS RDS configuration")

def main():
    print("🚀 AWS RDS Connection Test")
    print("=" * 50)
    
    # Test psycopg2 connection first
    password = test_psycopg2_connection()
    
    if password:
        # Test SQLAlchemy connection
        if test_sqlalchemy_connection(password):
            # Generate .env file
            generate_env_file(password)
            
            print("\n" + "=" * 50)
            print("✅ All tests passed! Your application should work with AWS RDS")
            print("🚀 You can now run: python main.py")
        else:
            print("\n❌ SQLAlchemy test failed. Check your configuration.")
    else:
        print("\n❌ Basic connection test failed. Please fix connection issues first.")

if __name__ == "__main__":
    main()
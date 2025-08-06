#!/usr/bin/env python3
"""
Quick test AWS RDS connection after security group fix
"""
import socket
import time
import psycopg2
from datetime import datetime

def test_port_connection(host, port, timeout=10):
    """Test if port is accessible"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception as e:
        print(f"Socket error: {e}")
        return False

def test_postgres_connection(host, port, user, password, database="postgres"):
    """Test PostgreSQL connection"""
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            connect_timeout=30,
            sslmode="require"
        )
        
        cursor = conn.cursor()
        cursor.execute("SELECT version(), current_database(), current_user;")
        result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return True, result
    except Exception as e:
        return False, str(e)

def main():
    print("🚀 Quick AWS RDS Connection Test")
    print("=" * 50)
    print(f"Time: {datetime.now()}")
    print(f"Your IP: 114.10.44.196")
    
    host = "stegano.cvoi8i4o83ra.ap-southeast-1.rds.amazonaws.com"
    port = 5432
    
    print(f"\n🔍 Testing connection to: {host}:{port}")
    
    # Test 1: Port connectivity (with multiple attempts)
    print("📡 Testing port connectivity...")
    
    for attempt in range(3):
        print(f"   Attempt {attempt + 1}/3: ", end="", flush=True)
        
        if test_port_connection(host, port, 15):
            print("✅ PORT OPEN!")
            break
        else:
            print("❌ Port blocked")
            if attempt < 2:
                print("   Waiting 10 seconds before retry...")
                time.sleep(10)
    else:
        print("\n❌ All port tests failed. Security group might need more time to apply.")
        print("💡 Wait 2-3 minutes and try again, or check security group configuration.")
        return
    
    # Test 2: PostgreSQL connection
    print("\n🔐 Testing PostgreSQL connection...")
    password = input("Enter your RDS password (evrino123): ").strip()
    if not password:
        password = "evrino123"
    
    success, result = test_postgres_connection(host, port, "postgres", password)
    
    if success:
        print("✅ PostgreSQL connection successful!")
        print(f"   Database: {result[1]}")
        print(f"   User: {result[2]}")
        print(f"   Version: {result[0][:50]}...")
        
        # Test steganography database
        print("\n📊 Testing steganography database...")
        success2, result2 = test_postgres_connection(host, port, "postgres", password, "steganography")
        
        if success2:
            print("✅ steganography database accessible!")
        else:
            print(f"⚠️ steganography database issue: {result2}")
            if "does not exist" in str(result2):
                print("💡 Need to create steganography database")
                create_db = input("Create steganography database? (y/n): ").lower()
                if create_db == 'y':
                    try:
                        conn = psycopg2.connect(
                            host=host, port=port, user="postgres", 
                            password=password, database="postgres",
                            sslmode="require"
                        )
                        conn.autocommit = True
                        cursor = conn.cursor()
                        cursor.execute("CREATE DATABASE steganography;")
                        cursor.close()
                        conn.close()
                        print("✅ steganography database created!")
                    except Exception as e:
                        print(f"❌ Failed to create database: {e}")
        
        # Generate working .env
        print("\n📝 Generating .env file...")
        database_url = f"postgresql://postgres:{password}@{host}:5432/steganography?sslmode=require"
        
        env_content = f"""# AWS RDS Production Configuration - WORKING!
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
        
        print("✅ .env file created successfully!")
        print("\n🎉 CONNECTION TEST PASSED!")
        print("🚀 You can now run: python main.py")
        
    else:
        print(f"❌ PostgreSQL connection failed: {result}")
        print("\n🔧 Troubleshooting:")
        print("1. Check password is correct")
        print("2. Verify security group rule is applied")
        print("3. Wait 2-3 minutes for AWS changes to take effect")

if __name__ == "__main__":
    main()
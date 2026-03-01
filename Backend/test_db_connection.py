#!/usr/bin/env python3
"""
Quick script to test database connection with current .env settings
"""
from dotenv import load_dotenv
import os
import psycopg2

load_dotenv()

print("=" * 60)
print("Testing Database Connection")
print("=" * 60)
print()

database_url = os.getenv("DATABASE_URL")
if database_url:
    # Mask password in URL for display
    from urllib.parse import urlparse
    p = urlparse(database_url)
    safe_url = f"{p.scheme}://{p.username}:***@{p.hostname}:{p.port or 5432}{p.path}"
    print(f"Using: DATABASE_URL ({p.hostname})")
else:
    print(f"Database: {os.getenv('PGDATABASE')}")
    print(f"User: {os.getenv('PGUSER')}")
    print(f"Host: {os.getenv('PGHOST')}")
    print(f"Port: {os.getenv('PGPORT')}")
print()

try:
    print("Attempting connection...")
    if database_url:
        conn = psycopg2.connect(database_url)
    else:
        conn = psycopg2.connect(
            dbname=os.getenv("PGDATABASE"),
            user=os.getenv("PGUSER"),
            password=os.getenv("PGPASSWORD"),
            host=os.getenv("PGHOST"),
            port=os.getenv("PGPORT"),
        )
    print("[OK] Connection successful!")
    
    # Test query
    cursor = conn.cursor()
    cursor.execute("SELECT version();")
    version = cursor.fetchone()[0]
    print(f"PostgreSQL Version: {version.split(',')[0]}")
    
    # Check if users table exists
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'users'
        );
    """)
    table_exists = cursor.fetchone()[0]
    print(f"Users table exists: {'Yes' if table_exists else 'No'}")
    
    cursor.close()
    conn.close()
    print()
    print("=" * 60)
    print("[OK] All tests passed! Database is ready.")
    print("=" * 60)
    
except psycopg2.OperationalError as e:
    print(f"[FAIL] Connection failed: {e}")
    print()
    print("Troubleshooting steps:")
    if database_url:
        print("1. Check DATABASE_URL in Backend/.env (Neon dashboard for correct URL)")
        print("2. Ensure the URL includes ?sslmode=require")
    else:
        print("1. Verify PostgreSQL is running (check Services)")
        print("2. Check PGPASSWORD and other PG* vars in .env")
    print()
    print("=" * 60)
except Exception as e:
    print(f"[FAIL] Error: {e}")
    print("=" * 60)


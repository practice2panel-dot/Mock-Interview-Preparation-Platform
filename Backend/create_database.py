#!/usr/bin/env python3
"""
Quick script to create PostgreSQL database if it doesn't exist.
Run this before starting the server if you get "database does not exist" error.
"""
import os
import sys
from dotenv import load_dotenv
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Load environment variables
load_dotenv()

def create_database():
    """Ensure database is reachable. With Neon, the database already exists."""
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        try:
            print("Connecting to database (DATABASE_URL / Neon)...")
            conn = psycopg2.connect(database_url)
            conn.close()
            print("Database connection successful. ✓")
            return True
        except psycopg2.OperationalError as e:
            print(f"Error connecting to database: {e}")
            print("Check DATABASE_URL in Backend/.env file.")
            return False
        except Exception as e:
            print(f"Error: {e}")
            return False

    # Legacy: local PostgreSQL – create database if it doesn't exist
    dbname = os.getenv("PGDATABASE", "interview_db")
    user = os.getenv("PGUSER", "postgres")
    password = os.getenv("PGPASSWORD")
    host = os.getenv("PGHOST", "localhost")
    port = os.getenv("PGPORT", "5432")
    if not password:
        print("Error: PGPASSWORD not set in .env file")
        return False
    try:
        print(f"Connecting to PostgreSQL server at {host}:{port}...")
        conn = psycopg2.connect(
            dbname='postgres', user=user, password=password, host=host, port=port
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,))
        if cursor.fetchone():
            print(f"Database '{dbname}' already exists. ✓")
        else:
            print(f"Creating database '{dbname}'...")
            cursor.execute(f'CREATE DATABASE "{dbname}"')
            print(f"Database '{dbname}' created successfully! ✓")
        cursor.close()
        conn.close()
        return True
    except psycopg2.OperationalError as e:
        print(f"Error connecting to PostgreSQL: {e}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("PostgreSQL Database Setup")
    print("=" * 60)
    print()
    
    if create_database():
        print()
        print("=" * 60)
        print("Success! You can now start the backend server.")
        print("=" * 60)
        sys.exit(0)
    else:
        print()
        print("=" * 60)
        print("Failed to create database. Please check the errors above.")
        print("=" * 60)
        sys.exit(1)






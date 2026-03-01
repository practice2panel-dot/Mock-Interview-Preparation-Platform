#!/usr/bin/env python3
"""
Verify database connectivity and check existing tables.
This script simply checks that the database is accessible and tables exist.
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db_handler import get_pg_connection

def verify_database_connection():
    """Verify database connection and check existing tables"""
    try:
        print("🔍 Checking database connection...")
        conn = get_pg_connection()
        print("✅ Database connection successful!")
        
        # Check existing tables
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)
            
            tables = [row[0] for row in cursor.fetchall()]
            
            if tables:
                print(f"\n📊 Found {len(tables)} existing tables:")
                for table in tables:
                    # Count questions in each table
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cursor.fetchone()[0]
                        print(f"  ✓ {table} ({count} questions)")
                    except Exception as e:
                        print(f"  ⚠️ {table} (error counting: {e})")
                
                print(f"\n✅ Database is ready with {len(tables)} tables!")
                print("\nAvailable API endpoints:")
                for table in tables:
                    if table == 'behavioralquestions':
                        print(f"  GET /api/questions/behavioral/{{any_skill}}  # Uses '{table}' table")
                    elif '_' in table:
                        parts = table.split('_')
                        if len(parts) >= 2:
                            interview_type = parts[0]
                            skill = '_'.join(parts[1:])
                            print(f"  GET /api/questions/{interview_type}/{skill}  # Uses '{table}' table")
                    else:
                        print(f"  GET /api/questions/technical/{table}  # Uses '{table}' table")
            else:
                print("⚠️ No tables found in the database")
                
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("Please check your database configuration in the .env file")
        return False
    finally:
        if 'conn' in locals():
            conn.close()
    
    return True

if __name__ == '__main__':
    verify_database_connection()

#!/usr/bin/env python3
"""
Utility script to manage users in the database.
Usage:
  python manage_users.py list              # List all users
  python manage_users.py delete <email>   # Delete user by email
  python manage_users.py clear             # Clear all users (DANGEROUS!)
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db_handler import get_pg_connection

def list_all_users():
    """List all users in the database"""
    try:
        conn = get_pg_connection()
        
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, email, full_name, is_verified, created_at, last_login
                FROM users 
                ORDER BY created_at DESC
            """)
            
            users = cursor.fetchall()
            
            if not users:
                print("[INFO] No users found in database")
                return
            
            print(f"\n[INFO] Found {len(users)} user(s):\n")
            print(f"{'ID':<5} {'Email':<40} {'Name':<30} {'Verified':<10} {'Created At':<20}")
            print("-" * 120)
            
            for user in users:
                user_id, email, name, verified, created_at, last_login = user
                verified_str = "Yes" if verified else "No"
                created_str = created_at.strftime("%Y-%m-%d %H:%M") if created_at else "N/A"
                print(f"{user_id:<5} {email:<40} {name[:30]:<30} {verified_str:<10} {created_str:<20}")
            
            print()
            
    except Exception as e:
        print(f"[ERROR] Error listing users: {str(e)}")
    finally:
        if 'conn' in locals():
            conn.close()

def delete_user_by_email(email):
    """Delete a user from the database by email"""
    try:
        conn = get_pg_connection()
        
        with conn.cursor() as cursor:
            # Check if user exists
            cursor.execute("SELECT id, email, full_name FROM users WHERE email = %s", (email.lower(),))
            user = cursor.fetchone()
            
            if not user:
                print(f"[ERROR] User with email '{email}' not found in database")
                return False
            
            user_id, user_email, user_name = user
            print(f"[FOUND] User: {user_name} ({user_email})")
            
            # Delete user
            cursor.execute("DELETE FROM users WHERE email = %s", (email.lower(),))
            conn.commit()
            
            print(f"[SUCCESS] User '{user_email}' deleted successfully!")
            return True
            
    except Exception as e:
        print(f"[ERROR] Error deleting user: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def clear_all_users():
    """Clear all users from the database (DANGEROUS!)"""
    try:
        conn = get_pg_connection()
        
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM users")
            count = cursor.fetchone()[0]
            
            if count == 0:
                print("[INFO] No users to delete")
                return
            
            print(f"[WARNING] This will delete ALL {count} user(s) from the database!")
            confirm = input("Type 'DELETE ALL' to confirm: ")
            
            if confirm != 'DELETE ALL':
                print("[CANCELLED] Deletion cancelled")
                return
            
            cursor.execute("DELETE FROM users")
            conn.commit()
            
            print(f"[SUCCESS] All users deleted successfully!")
            
    except Exception as e:
        print(f"[ERROR] Error clearing users: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("[INFO] User Management Utility")
        print("\nUsage:")
        print("  python manage_users.py list              # List all users")
        print("  python manage_users.py delete <email>     # Delete user by email")
        print("  python manage_users.py clear              # Clear all users (DANGEROUS!)")
        print("\nExample:")
        print("  python manage_users.py delete test@example.com")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == 'list':
        list_all_users()
    elif command == 'delete':
        if len(sys.argv) < 3:
            print("[ERROR] Email required")
            print("Usage: python manage_users.py delete <email>")
            sys.exit(1)
        email = sys.argv[2]
        delete_user_by_email(email)
    elif command == 'clear':
        clear_all_users()
    else:
        print(f"[ERROR] Unknown command: {command}")
        print("Available commands: list, delete, clear")
        sys.exit(1)


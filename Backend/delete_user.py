#!/usr/bin/env python3
"""
Utility script to delete a user from the database by email.
Usage: python delete_user.py <email>
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db_handler import get_pg_connection

def delete_user_by_email(email):
    """Delete a user from the database by email"""
    try:
        conn = get_pg_connection()
        
        with conn.cursor() as cursor:
            # Check if user exists
            cursor.execute("SELECT id, email, full_name FROM users WHERE email = %s", (email.lower(),))
            user = cursor.fetchone()
            
            if not user:
                print(f"❌ User with email '{email}' not found in database")
                return False
            
            user_id, user_email, user_name = user
            print(f"📧 Found user: {user_name} ({user_email})")
            
            # Confirm deletion
            confirm = input(f"⚠️  Are you sure you want to delete this user? (yes/no): ")
            if confirm.lower() != 'yes':
                print("❌ Deletion cancelled")
                return False
            
            # Delete user
            cursor.execute("DELETE FROM users WHERE email = %s", (email.lower(),))
            conn.commit()
            
            print(f"✅ User '{user_email}' deleted successfully!")
            return True
            
    except Exception as e:
        print(f"❌ Error deleting user: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
        return False
    finally:
        if 'conn' in locals():
            conn.close()

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
                print("📭 No users found in database")
                return
            
            print(f"\n📋 Found {len(users)} user(s):\n")
            print(f"{'ID':<5} {'Email':<40} {'Name':<30} {'Verified':<10} {'Created At':<20}")
            print("-" * 120)
            
            for user in users:
                user_id, email, name, verified, created_at, last_login = user
                verified_str = "Yes" if verified else "No"
                created_str = created_at.strftime("%Y-%m-%d %H:%M") if created_at else "N/A"
                print(f"{user_id:<5} {email:<40} {name[:30]:<30} {verified_str:<10} {created_str:<20}")
            
            print()
            
    except Exception as e:
        print(f"❌ Error listing users: {str(e)}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("📋 Available users in database:")
        list_all_users()
        print("\n💡 Usage: python delete_user.py <email>")
        print("   Example: python delete_user.py test@example.com")
        sys.exit(1)
    
    email = sys.argv[1]
    delete_user_by_email(email)


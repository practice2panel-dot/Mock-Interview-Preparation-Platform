import psycopg2
from psycopg2 import sql
import os
from dotenv import load_dotenv

def get_pg_connection():
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        # Neon or any PostgreSQL URL (SSL is in the URL: sslmode=require)
        return psycopg2.connect(database_url)
    # Fallback: individual vars (e.g. local dev)
    dbname = os.getenv("PGDATABASE")
    user = os.getenv("PGUSER")
    password = os.getenv("PGPASSWORD")
    host = os.getenv("PGHOST")
    port = os.getenv("PGPORT")
    missing = [
        name for name, val in (
            ("PGDATABASE", dbname),
            ("PGUSER", user),
            ("PGPASSWORD", password),
            ("PGHOST", host),
            ("PGPORT", port),
        ) if not val
    ]
    if missing:
        raise RuntimeError(
            "Set DATABASE_URL in .env (e.g. Neon) or set: " + ", ".join(missing)
        )
    return psycopg2.connect(dbname=dbname, user=user, password=password, host=host, port=port)

def create_table_if_not_exists(conn, table_name):
    with conn.cursor() as cursor:
        # Ensure case-insensitive text type is available
        cursor.execute("CREATE EXTENSION IF NOT EXISTS citext;")
        create_query = sql.SQL(
            """
            CREATE TABLE IF NOT EXISTS {table} (
                id SERIAL PRIMARY KEY,
                question CITEXT UNIQUE,
                explanation TEXT
            );
            """
        ).format(table=sql.Identifier(table_name))
        cursor.execute(create_query)
def insert_qna_rows(table_name, qna_rows):
    if not qna_rows:
        return
    conn = get_pg_connection()
    try:
        create_table_if_not_exists(conn, table_name)
        insert_query = sql.SQL(
            "INSERT INTO {table} (question, explanation) VALUES (%s, %s) ON CONFLICT (question) DO NOTHING"
        ).format(table=sql.Identifier(table_name))
        with conn.cursor() as cursor:
            for question, explanation in qna_rows:
                cursor.execute(insert_query, (question, explanation))
        conn.commit()
    finally:
        conn.close()

def create_users_table():
    """Create users table for authentication if it doesn't exist"""
    conn = get_pg_connection()
    try:
        with conn.cursor() as cursor:
            # Ensure case-insensitive text type is available
            cursor.execute("CREATE EXTENSION IF NOT EXISTS citext;")
            
            create_query = """
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    email CITEXT UNIQUE NOT NULL,
                    password_hash VARCHAR(255),
                    full_name VARCHAR(255) NOT NULL,
                    student_id VARCHAR(100),
                    phone VARCHAR(20),
                    is_verified BOOLEAN DEFAULT FALSE,
                    verification_code VARCHAR(6),
                    verification_expires TIMESTAMP,
                    reset_token VARCHAR(6),
                    reset_expires TIMESTAMP,
                    google_id VARCHAR(255) UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE
                );
            """
            cursor.execute(create_query)
            conn.commit()
            return True, None
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()

def drop_dashboard_tables():
    """Remove dashboard-related tables if they exist."""
    conn = get_pg_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS skill_prep_questions;")
            cursor.execute("DROP TABLE IF EXISTS skill_prep_progress;")
            cursor.execute("DROP TABLE IF EXISTS dashboard_favorites;")
            cursor.execute("DROP TABLE IF EXISTS dashboard_practice_sessions;")
            cursor.execute("DROP TABLE IF EXISTS dashboard_skill_attempts;")
            cursor.execute("DROP TABLE IF EXISTS dashboard_skill_questions;")
            cursor.execute("DROP TABLE IF EXISTS dashboard_skill_progress;")
        conn.commit()
        return True, None
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()

__all__ = [
    "get_pg_connection",
    "create_table_if_not_exists",
    "insert_qna_rows",
    "create_users_table",
    "drop_dashboard_tables",
]

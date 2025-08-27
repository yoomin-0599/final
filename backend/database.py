import os
import sqlite3
from typing import Optional, Any, Dict, List

# Load environment variables safely
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# PostgreSQL imports (optional)
try:
    import psycopg2
    import psycopg2.extras
    POSTGRES_AVAILABLE = True
except ImportError:
    psycopg2 = None
    POSTGRES_AVAILABLE = False

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL")
DB_TYPE = os.getenv("DB_TYPE", "sqlite").lower()
SQLITE_PATH = os.getenv("SQLITE_PATH", "/opt/render/project/src/news.db")

class DatabaseConnection:
    def __init__(self):
        self.db_type = DB_TYPE
        self.database_url = DATABASE_URL
        self.sqlite_path = SQLITE_PATH
        
    def get_connection(self):
        """Get database connection based on configuration"""
        if self.database_url and POSTGRES_AVAILABLE:
            return self._get_postgres_connection()
        else:
            return self._get_sqlite_connection()
    
    def _get_postgres_connection(self):
        """Get PostgreSQL connection"""
        conn = psycopg2.connect(self.database_url)
        conn.cursor_factory = psycopg2.extras.RealDictCursor
        return conn
    
    def _get_sqlite_connection(self):
        """Get SQLite connection"""
        conn = sqlite3.connect(self.sqlite_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    
    def execute_query(self, query: str, params: tuple = ()) -> List[Dict]:
        """Execute a SELECT query and return results"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            results = cursor.fetchall()
            return [dict(row) for row in results]
        finally:
            conn.close()
    
    def execute_update(self, query: str, params: tuple = ()) -> int:
        """Execute INSERT/UPDATE/DELETE query and return affected rows"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()
    
    def init_database(self):
        """Initialize database tables"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            # Articles table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS articles (
                    id SERIAL PRIMARY KEY,
                    title TEXT,
                    link TEXT UNIQUE,
                    published TEXT,
                    source TEXT,
                    raw_text TEXT,
                    summary TEXT,
                    keywords TEXT,
                    category TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """ if self.database_url else """
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT,
                    link TEXT UNIQUE,
                    published TEXT,
                    source TEXT,
                    raw_text TEXT,
                    summary TEXT,
                    keywords TEXT,
                    category TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                );
            """)
            
            # Favorites table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS favorites (
                    article_id INTEGER UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """ if self.database_url else """
                CREATE TABLE IF NOT EXISTS favorites (
                    article_id INTEGER UNIQUE,
                    created_at TEXT DEFAULT (datetime('now'))
                );
            """)
            
            # Create indexes
            if not self.database_url:  # SQLite indexes
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(published DESC)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source)")
            
            conn.commit()
            print(f"Database initialized successfully ({self.db_type})")
            
        except Exception as e:
            print(f"Database initialization failed: {e}")
            conn.rollback()
        finally:
            conn.close()

# Global database instance
db = DatabaseConnection()

def get_db_connection():
    """Get database connection (for backward compatibility)"""
    return db.get_connection()

def init_db():
    """Initialize database (for backward compatibility)"""
    return db.init_database()
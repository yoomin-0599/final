import os
import sqlite3
import json
import logging
from typing import Optional, Any, Dict, List
from urllib.parse import urlparse

# Try to import psycopg2 - it might not be available in all environments
try:
    from psycopg2.pool import SimpleConnectionPool
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False
    SimpleConnectionPool = None

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    from psycopg2 import sql
    POSTGRES_AVAILABLE = PSYCOPG2_AVAILABLE and True
except ImportError:
    psycopg2 = None
    POSTGRES_AVAILABLE = False

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL")
DB_TYPE = os.getenv("DB_TYPE", "auto").lower()
SQLITE_PATH = os.getenv("SQLITE_PATH", "/tmp/news.db")

class DatabaseConnection:
    def __init__(self):
        self.database_url = DATABASE_URL
        self.sqlite_path = SQLITE_PATH
        self.pool = None
        
        # Auto-detect database type
        if DB_TYPE == "auto":
            if self.database_url and POSTGRES_AVAILABLE and "postgres" in self.database_url:
                self.db_type = "postgresql"
            else:
                self.db_type = "sqlite"
        else:
            self.db_type = DB_TYPE
        
        # Initialize PostgreSQL connection pool if using PostgreSQL
        if self.db_type == "postgresql":
            self._init_postgres_pool()
        
        logger.info(f"Database type: {self.db_type}")
        
    def _init_postgres_pool(self):
        """Initialize PostgreSQL connection pool"""
        if not self.database_url or not POSTGRES_AVAILABLE or not PSYCOPG2_AVAILABLE:
            logger.warning("PostgreSQL not available, falling back to SQLite")
            self.db_type = "sqlite"
            return
            
        try:
            # Handle different PostgreSQL URL formats
            database_url = self.database_url
            if database_url.startswith('postgres://'):
                database_url = database_url.replace('postgres://', 'postgresql://', 1)
            
            if SimpleConnectionPool:
                self.pool = SimpleConnectionPool(
                    minconn=1,
                    maxconn=10,
                    dsn=database_url
                )
                logger.info("✅ PostgreSQL connection pool initialized")
            else:
                raise ImportError("SimpleConnectionPool not available")
            
        except Exception as e:
            logger.error(f"❌ PostgreSQL connection failed: {e}")
            logger.info("🔄 Falling back to SQLite")
            self.db_type = "sqlite"
            self.pool = None
    
    def get_connection(self):
        """Get database connection based on configuration"""
        if self.db_type == "postgresql" and self.pool:
            try:
                return self.pool.getconn()
            except Exception as e:
                logger.error(f"Error getting PostgreSQL connection: {e}")
                return self._get_sqlite_connection()
        else:
            return self._get_sqlite_connection()
    
    def return_connection(self, conn):
        """Return connection to pool (PostgreSQL only)"""
        if self.db_type == "postgresql" and self.pool and conn:
            try:
                self.pool.putconn(conn)
            except Exception as e:
                logger.error(f"Error returning connection to pool: {e}")
        elif conn and self.db_type == "sqlite":
            conn.close()
    
    def _get_postgres_connection(self):
        """Get PostgreSQL connection"""
        database_url = self.database_url
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        
        conn = psycopg2.connect(database_url)
        return conn
    
    def _get_sqlite_connection(self):
        """Get SQLite connection"""
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.sqlite_path), exist_ok=True)
        conn = sqlite3.connect(self.sqlite_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    
    def execute_query(self, query: str, params: tuple = ()) -> List[Dict]:
        """Execute a SELECT query and return results"""
        conn = self.get_connection()
        try:
            if self.db_type == "postgresql":
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            else:
                cursor = conn.cursor()
                
            cursor.execute(query, params)
            results = cursor.fetchall()
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Query execution error: {e}")
            raise
        finally:
            self.return_connection(conn)
    
    def execute_update(self, query: str, params: tuple = ()) -> int:
        """Execute INSERT/UPDATE/DELETE query and return affected rows"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount
        except Exception as e:
            logger.error(f"Update execution error: {e}")
            conn.rollback()
            raise
        finally:
            self.return_connection(conn)
    
    def init_database(self):
        """Initialize database tables"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            if self.db_type == "postgresql":
                self._create_postgres_tables(cursor)
            else:
                self._create_sqlite_tables(cursor)
            
            conn.commit()
            logger.info(f"✅ Database initialized successfully ({self.db_type})")
            
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            conn.rollback()
            raise
        finally:
            self.return_connection(conn)
    
    def _create_postgres_tables(self, cursor):
        """Create PostgreSQL tables with enhanced schema"""
        # Articles table with JSONB for keywords
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                link TEXT UNIQUE NOT NULL,
                published TIMESTAMP,
                source TEXT,
                raw_text TEXT,
                summary TEXT,
                keywords JSONB,
                category TEXT,
                language TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Favorites table with proper foreign key
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS favorites (
                id SERIAL PRIMARY KEY,
                article_id INTEGER REFERENCES articles(id) ON DELETE CASCADE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(article_id)
            )
        """)
        
        # Collections table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS collections (
                id SERIAL PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                rules JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Collection articles junction table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS collection_articles (
                id SERIAL PRIMARY KEY,
                collection_id INTEGER REFERENCES collections(id) ON DELETE CASCADE,
                article_id INTEGER REFERENCES articles(id) ON DELETE CASCADE,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(collection_id, article_id)
            )
        """)
        
        # Create indexes for better performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(published DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_keywords ON articles USING GIN(keywords)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_collection_articles_collection ON collection_articles(collection_id)")
        
        # Update trigger for updated_at
        cursor.execute("""
            CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ language 'plpgsql';
        """)
        
        cursor.execute("""
            DROP TRIGGER IF EXISTS update_articles_updated_at ON articles;
            CREATE TRIGGER update_articles_updated_at 
                BEFORE UPDATE ON articles 
                FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        """)
    
    def _create_sqlite_tables(self, cursor):
        """Create SQLite tables"""
        # Articles table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                link TEXT UNIQUE NOT NULL,
                published TEXT,
                source TEXT,
                raw_text TEXT,
                summary TEXT,
                keywords TEXT,
                category TEXT,
                language TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)
        
        # Favorites table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_id INTEGER REFERENCES articles(id) ON DELETE CASCADE,
                created_at TEXT DEFAULT (datetime('now')),
                UNIQUE(article_id)
            )
        """)
        
        # Collections table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS collections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                rules TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)
        
        # Collection articles junction table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS collection_articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                collection_id INTEGER REFERENCES collections(id) ON DELETE CASCADE,
                article_id INTEGER REFERENCES articles(id) ON DELETE CASCADE,
                added_at TEXT DEFAULT (datetime('now')),
                UNIQUE(collection_id, article_id)
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(published DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_collection_articles_collection ON collection_articles(collection_id)")
    
    def insert_article(self, article_data: Dict) -> Optional[int]:
        """Insert new article and return ID"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            # Convert keywords list to JSON string
            keywords_json = None
            if article_data.get('keywords'):
                if isinstance(article_data['keywords'], list):
                    keywords_json = json.dumps(article_data['keywords'])
                else:
                    keywords_json = article_data['keywords']
            
            if self.db_type == "postgresql":
                cursor.execute("""
                    INSERT INTO articles (title, link, published, source, raw_text, summary, keywords, category, language)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (link) DO UPDATE SET
                        title = EXCLUDED.title,
                        summary = EXCLUDED.summary,
                        keywords = EXCLUDED.keywords,
                        updated_at = CURRENT_TIMESTAMP
                    RETURNING id
                """, (
                    article_data.get('title'),
                    article_data.get('link'),
                    article_data.get('published'),
                    article_data.get('source'),
                    article_data.get('raw_text'),
                    article_data.get('summary'),
                    keywords_json,
                    article_data.get('category'),
                    article_data.get('language')
                ))
                result = cursor.fetchone()
                article_id = result[0] if result else None
            else:
                cursor.execute("""
                    INSERT OR REPLACE INTO articles (title, link, published, source, raw_text, summary, keywords, category, language)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    article_data.get('title'),
                    article_data.get('link'),
                    article_data.get('published'),
                    article_data.get('source'),
                    article_data.get('raw_text'),
                    article_data.get('summary'),
                    keywords_json,
                    article_data.get('category'),
                    article_data.get('language')
                ))
                article_id = cursor.lastrowid
            
            conn.commit()
            return article_id
            
        except Exception as e:
            logger.error(f"Error inserting article: {e}")
            conn.rollback()
            return None
        finally:
            self.return_connection(conn)
    
    def get_articles_with_filters(self, limit: int = 100, offset: int = 0, **filters) -> List[Dict]:
        """Get articles with advanced filtering"""
        conditions = []
        params = []
        
        # Build WHERE conditions based on database type
        placeholder = "%s" if self.db_type == "postgresql" else "?"
        
        if filters.get('source'):
            conditions.append(f"a.source = {placeholder}")
            params.append(filters['source'])
        
        if filters.get('search'):
            if self.db_type == "postgresql":
                conditions.append(f"(a.title ILIKE {placeholder} OR a.summary ILIKE {placeholder} OR a.keywords::text ILIKE {placeholder})")
            else:
                conditions.append(f"(a.title LIKE {placeholder} OR a.summary LIKE {placeholder} OR a.keywords LIKE {placeholder})")
            search_param = f"%{filters['search']}%"
            params.extend([search_param, search_param, search_param])
        
        if filters.get('date_from'):
            conditions.append(f"DATE(a.published) >= {placeholder}")
            params.append(filters['date_from'])
        
        if filters.get('date_to'):
            conditions.append(f"DATE(a.published) <= {placeholder}")
            params.append(filters['date_to'])
        
        if filters.get('favorites_only'):
            conditions.append("f.article_id IS NOT NULL")
        
        # Build final query
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        query = f"""
            SELECT a.*, 
                   CASE WHEN f.article_id IS NOT NULL THEN TRUE ELSE FALSE END as is_favorite
            FROM articles a
            LEFT JOIN favorites f ON a.id = f.article_id
            WHERE {where_clause}
            ORDER BY a.published DESC
            LIMIT {placeholder} OFFSET {placeholder}
        """
        
        params.extend([limit, offset])
        results = self.execute_query(query, tuple(params))
        
        # Parse keywords JSON
        for article in results:
            if article.get('keywords'):
                try:
                    if isinstance(article['keywords'], str):
                        article['keywords'] = json.loads(article['keywords'])
                except (json.JSONDecodeError, TypeError):
                    article['keywords'] = []
        
        return results
    
    def get_keyword_stats(self, limit: int = 50) -> List[Dict]:
        """Get keyword statistics with database-specific optimizations"""
        if self.db_type == "postgresql":
            query = """
                SELECT keyword, COUNT(*) as count
                FROM articles,
                     jsonb_array_elements_text(keywords) as keyword
                WHERE keywords IS NOT NULL
                GROUP BY keyword
                ORDER BY count DESC
                LIMIT %s
            """
            return self.execute_query(query, (limit,))
        else:
            # SQLite implementation - parse JSON in Python
            query = "SELECT keywords FROM articles WHERE keywords IS NOT NULL AND keywords != ''"
            results = self.execute_query(query)
            
            keyword_counts = {}
            for row in results:
                try:
                    keywords = json.loads(row['keywords']) if row['keywords'] else []
                    for keyword in keywords:
                        if keyword and keyword.strip():
                            keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1
                except (json.JSONDecodeError, TypeError):
                    continue
            
            # Sort and limit
            sorted_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
            return [{"keyword": k, "count": v} for k, v in sorted_keywords]
    
    def close_all_connections(self):
        """Close all database connections"""
        if self.pool:
            self.pool.closeall()
            logger.info("Database connection pool closed")

# Global database instance
db = DatabaseConnection()

def get_db_connection():
    """Get database connection (for backward compatibility)"""
    return db.get_connection()

def init_db():
    """Initialize database (for backward compatibility)"""
    return db.init_database()
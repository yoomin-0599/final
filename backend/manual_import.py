import json
import sqlite3
from datetime import datetime
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def create_tables():
    """Create necessary tables"""
    conn = sqlite3.connect('news.db')
    cursor = conn.cursor()
    
    # Create articles table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS articles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        link TEXT UNIQUE,
        published TEXT,
        source TEXT,
        summary TEXT,
        keywords TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create favorites table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS favorites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        article_id INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (article_id) REFERENCES articles (id)
    )
    ''')
    
    conn.commit()
    conn.close()

def import_jsonl():
    """Import JSONL data to database"""
    try:
        create_tables()
        
        conn = sqlite3.connect('news.db')
        cursor = conn.cursor()
        
        imported_count = 0
        
        with open('../archive_last_year.jsonl', 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    article = json.loads(line.strip())
                    
                    # Extract keywords if available
                    keywords = article.get('keywords', '')
                    if isinstance(keywords, list):
                        keywords = ','.join(keywords)
                    
                    cursor.execute('''
                    INSERT OR IGNORE INTO articles 
                    (title, link, published, source, summary, keywords)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        article.get('title', ''),
                        article.get('link', ''),
                        article.get('published', ''),
                        article.get('source', ''),
                        article.get('summary', ''),
                        keywords
                    ))
                    
                    if cursor.rowcount > 0:
                        imported_count += 1
                    
                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    print(f"Error importing article: {e}")
                    continue
        
        conn.commit()
        conn.close()
        
        print(f"Successfully imported {imported_count} articles")
        return imported_count
        
    except FileNotFoundError:
        print("JSONL file not found")
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 0

if __name__ == "__main__":
    import_jsonl()
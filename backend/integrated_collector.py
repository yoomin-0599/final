"""
Integrated news collector for production use
Works with the existing backend system
"""

import os
import sqlite3
import requests
import feedparser
import json
from datetime import datetime
from typing import List, Dict, Optional
import sys

# Use environment-aware database connection
def get_production_db_path():
    """Get the correct database path for the environment"""
    if os.getenv('DATABASE_URL'):
        # PostgreSQL connection - we'll use SQLite for now as fallback
        return os.getenv('SQLITE_PATH', '/tmp/news.db')
    else:
        # Local development
        return 'backend/news.db'

class NewsCollector:
    def __init__(self):
        self.db_path = get_production_db_path()
        self.feeds = [
            {"feed_url": "https://it.donga.com/feeds/rss/", "source": "IT동아", "category": "IT"},
            {"feed_url": "https://rss.etnews.com/Section902.xml", "source": "전자신문_속보", "category": "IT"},
            {"feed_url": "https://rss.etnews.com/Section901.xml", "source": "전자신문_오늘의뉴스", "category": "IT"},
            {"feed_url": "https://techcrunch.com/feed/", "source": "TechCrunch", "category": "Tech"},
            {"feed_url": "https://www.theverge.com/rss/index.xml", "source": "The Verge", "category": "Tech"},
            {"feed_url": "https://www.wired.com/feed/rss", "source": "WIRED", "category": "Tech"},
            {"feed_url": "https://www.engadget.com/rss.xml", "source": "Engadget", "category": "Tech"},
        ]
        self.headers = {"User-Agent": "Mozilla/5.0 (NewsCollector/1.0)"}
    
    def init_database(self):
        """Initialize database with proper error handling"""
        try:
            # Create directory if needed
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            cursor = conn.cursor()
            
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
                    created_at TEXT DEFAULT (datetime('now'))
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS favorites (
                    article_id INTEGER UNIQUE,
                    created_at TEXT DEFAULT (datetime('now'))
                )
            """)
            
            # Create indexes for better performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(published DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_created ON articles(created_at DESC)")
            
            conn.commit()
            conn.close()
            
            print(f"✅ Database initialized at: {self.db_path}")
            return True
            
        except Exception as e:
            print(f"❌ Database initialization failed: {e}")
            return False
    
    def collect_from_feed(self, feed_url: str, source: str, category: str, max_items: int = 15) -> List[Dict]:
        """Collect articles from RSS feed with error handling"""
        try:
            print(f"📡 Collecting from {source}...")
            
            # Parse RSS feed
            feed = feedparser.parse(feed_url)
            if not hasattr(feed, 'entries') or not feed.entries:
                print(f"❌ No entries found for {source}")
                return []
            
            articles = []
            for entry in feed.entries[:max_items]:
                try:
                    # Extract article data
                    title = getattr(entry, 'title', '').strip()
                    link = getattr(entry, 'link', '').strip()
                    
                    if not title or not link:
                        continue
                    
                    # Get published date
                    published = getattr(entry, 'published', '')
                    if not published:
                        published = getattr(entry, 'updated', datetime.now().strftime('%Y-%m-%d'))
                    
                    # Get summary
                    summary = getattr(entry, 'summary', '')
                    if summary and len(summary) > 500:
                        summary = summary[:500] + '...'
                    
                    # Extract simple keywords from title
                    keywords = self.extract_simple_keywords(title)
                    
                    article = {
                        'title': title,
                        'link': link,
                        'published': published,
                        'source': source,
                        'raw_text': summary,
                        'summary': summary,
                        'keywords': json.dumps(keywords, ensure_ascii=False),
                        'category': category
                    }
                    
                    articles.append(article)
                    
                except Exception as e:
                    print(f"⚠️ Error processing entry from {source}: {e}")
                    continue
            
            print(f"✅ Collected {len(articles)} articles from {source}")
            return articles
            
        except Exception as e:
            print(f"❌ Error collecting from {source}: {e}")
            return []
    
    def extract_simple_keywords(self, text: str) -> List[str]:
        """Extract simple keywords from text"""
        if not text:
            return []
        
        # Simple keyword extraction
        import re
        words = re.findall(r'[가-힣]+|[A-Za-z]+', text.lower())
        
        # Filter common words
        stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 
                     '그리고', '하지만', '그런데', '또한', '그래서', '따라서', '그러나'}
        
        keywords = [w for w in words if len(w) > 2 and w not in stop_words][:10]
        return keywords
    
    def save_articles(self, articles: List[Dict]) -> Dict[str, int]:
        """Save articles to database"""
        if not articles:
            return {'inserted': 0, 'updated': 0, 'skipped': 0}
        
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        cursor = conn.cursor()
        
        stats = {'inserted': 0, 'updated': 0, 'skipped': 0}
        
        for article in articles:
            try:
                # Try to insert
                cursor.execute("""
                    INSERT OR IGNORE INTO articles 
                    (title, link, published, source, raw_text, summary, keywords, category)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    article['title'],
                    article['link'],
                    article['published'], 
                    article['source'],
                    article['raw_text'],
                    article['summary'],
                    article['keywords'],
                    article['category']
                ))
                
                if cursor.rowcount > 0:
                    stats['inserted'] += 1
                else:
                    stats['skipped'] += 1
                    
            except Exception as e:
                print(f"⚠️ Error saving article: {e}")
                stats['skipped'] += 1
        
        conn.commit()
        conn.close()
        
        return stats
    
    def run_collection(self):
        """Run the full news collection process"""
        print("🚀 Starting integrated news collection...")
        
        # Initialize database
        if not self.init_database():
            print("❌ Cannot proceed without database")
            return False
        
        # Collect from all feeds
        all_articles = []
        for feed in self.feeds:
            articles = self.collect_from_feed(
                feed['feed_url'], 
                feed['source'], 
                feed.get('category', 'News')
            )
            all_articles.extend(articles)
        
        if not all_articles:
            print("❌ No articles collected")
            return False
        
        # Save articles
        stats = self.save_articles(all_articles)
        
        print(f"📊 Collection complete:")
        print(f"   - Total processed: {len(all_articles)}")
        print(f"   - Newly inserted: {stats['inserted']}")
        print(f"   - Skipped (duplicates): {stats['skipped']}")
        
        # Show database stats
        try:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM articles")
            total = cursor.fetchone()[0]
            cursor.execute("SELECT source, COUNT(*) FROM articles GROUP BY source ORDER BY COUNT(*) DESC")
            by_source = cursor.fetchall()
            conn.close()
            
            print(f"📈 Database stats:")
            print(f"   - Total articles: {total}")
            for source, count in by_source:
                print(f"   - {source}: {count}")
        except Exception as e:
            print(f"⚠️ Error getting stats: {e}")
        
        return True
    
    def get_articles(self, limit: int = 10) -> List[Dict]:
        """Get recent articles"""
        try:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, title, link, published, source, summary, category
                FROM articles 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (limit,))
            
            articles = []
            for row in cursor.fetchall():
                articles.append({
                    'id': row[0],
                    'title': row[1],
                    'link': row[2],
                    'published': row[3],
                    'source': row[4],
                    'summary': row[5],
                    'category': row[6]
                })
            
            conn.close()
            return articles
            
        except Exception as e:
            print(f"❌ Error getting articles: {e}")
            return []

# Standalone execution
if __name__ == "__main__":
    collector = NewsCollector()
    success = collector.run_collection()
    
    if success:
        print("\n📰 Sample of collected articles:")
        articles = collector.get_articles(5)
        for i, article in enumerate(articles, 1):
            print(f"{i}. [{article['source']}] {article['title'][:60]}...")
    else:
        print("❌ Collection failed")
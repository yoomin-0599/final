"""
Simple news collector for testing and development
Standalone script that can run independently
"""

import sqlite3
import requests
import feedparser
import json
import os
from datetime import datetime
from typing import List, Dict

# Simple configuration - expanded feed list
FEEDS = [
    # Korean Tech News
    {"feed_url": "https://it.donga.com/feeds/rss/", "source": "IT동아"},
    {"feed_url": "https://rss.etnews.com/Section902.xml", "source": "전자신문_속보"},
    {"feed_url": "https://rss.etnews.com/Section901.xml", "source": "전자신문_오늘의뉴스"},
    {"feed_url": "https://zdnet.co.kr/news/news_xml.asp", "source": "ZDNet Korea"},
    {"feed_url": "https://www.itworld.co.kr/rss/all.xml", "source": "ITWorld Korea"},
    {"feed_url": "https://www.bloter.net/feed", "source": "Bloter"},
    {"feed_url": "https://byline.network/feed/", "source": "Byline Network"},
    {"feed_url": "https://platum.kr/feed", "source": "Platum"},
    {"feed_url": "https://www.boannews.com/media/news_rss.xml", "source": "보안뉴스"},
    {"feed_url": "https://it.chosun.com/rss.xml", "source": "IT조선"},
    
    # Global Tech News
    {"feed_url": "https://techcrunch.com/feed/", "source": "TechCrunch"},
    {"feed_url": "https://www.theverge.com/rss/index.xml", "source": "The Verge"},
    {"feed_url": "https://www.engadget.com/rss.xml", "source": "Engadget"},
    {"feed_url": "https://www.wired.com/feed/rss", "source": "WIRED"},
    {"feed_url": "https://www.technologyreview.com/feed/", "source": "MIT Tech Review"},
    {"feed_url": "https://arstechnica.com/feed/", "source": "Ars Technica"},
    {"feed_url": "https://feeds.feedburner.com/venturebeat/SZYF", "source": "VentureBeat"},
    {"feed_url": "https://thenextweb.com/feed", "source": "The Next Web"},
    {"feed_url": "https://www.zdnet.com/news/rss.xml", "source": "ZDNet"},
    {"feed_url": "https://www.cnet.com/rss/news/", "source": "CNET News"},
]

DB_PATH = "simple_news.db"
HEADERS = {"User-Agent": "Mozilla/5.0 (NewsAgent/1.0)"}

def init_simple_db():
    """Initialize simple database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            link TEXT UNIQUE NOT NULL,
            published TEXT,
            source TEXT,
            summary TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS favorites (
            article_id INTEGER UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()
    print("✅ Simple database initialized")

def collect_from_feed(feed_url: str, source: str, max_items: int = 10) -> List[Dict]:
    """Collect news from a single RSS feed"""
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
                article = {
                    'title': getattr(entry, 'title', '').strip(),
                    'link': getattr(entry, 'link', '').strip(),
                    'published': getattr(entry, 'published', datetime.now().strftime('%Y-%m-%d')),
                    'source': source,
                    'summary': getattr(entry, 'summary', '')[:500] if hasattr(entry, 'summary') else ''
                }
                
                if article['title'] and article['link']:
                    articles.append(article)
                    
            except Exception as e:
                print(f"⚠️ Error processing entry from {source}: {e}")
                continue
        
        print(f"✅ Collected {len(articles)} articles from {source}")
        return articles
        
    except Exception as e:
        print(f"❌ Error collecting from {source}: {e}")
        return []

def save_articles(articles: List[Dict]) -> Dict[str, int]:
    """Save articles to database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    stats = {'inserted': 0, 'skipped': 0}
    
    for article in articles:
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO articles (title, link, published, source, summary)
                VALUES (?, ?, ?, ?, ?)
            """, (
                article['title'],
                article['link'], 
                article['published'],
                article['source'],
                article['summary']
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

def collect_all_feeds():
    """Collect news from all feeds and save to DB"""
    all_articles = []
    for feed in FEEDS:
        articles = collect_from_feed(feed['feed_url'], feed['source'])
        all_articles.extend(articles)
    
    if all_articles:
        stats = save_articles(all_articles)
        return len(all_articles), stats
    return 0, {'inserted': 0, 'skipped': 0}

def run_simple_collection():
    """Run simple news collection"""
    print("🚀 Starting simple news collection...")
    
    # Initialize database
    init_simple_db()
    
    # Collect from all feeds
    all_articles = []
    for feed in FEEDS:
        articles = collect_from_feed(feed['feed_url'], feed['source'])
        all_articles.extend(articles)
    
    if not all_articles:
        print("❌ No articles collected")
        return
    
    # Save articles
    stats = save_articles(all_articles)
    
    print(f"📊 Collection complete:")
    print(f"   - Total collected: {len(all_articles)}")
    print(f"   - Newly inserted: {stats['inserted']}")
    print(f"   - Skipped (duplicates): {stats['skipped']}")
    
    # Show database stats
    conn = sqlite3.connect(DB_PATH)
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

def get_recent_articles(limit: int = 10) -> List[Dict]:
    """Get recent articles from database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, title, link, published, source, summary, created_at
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
            'created_at': row[6]
        })
    
    conn.close()
    return articles

if __name__ == "__main__":
    run_simple_collection()
    
    print("\n📰 Recent articles:")
    recent = get_recent_articles(5)
    for i, article in enumerate(recent, 1):
        print(f"{i}. [{article['source']}] {article['title'][:60]}...")
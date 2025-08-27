from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict, Optional, Set
import sqlite3
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import asyncio
import requests
import feedparser
import re

# Load environment variables if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Import keyword extraction function
try:
    from keyword_maker import extract_keywords
except ImportError:
    # Fallback to simple keyword extraction if keyword_maker is not available
    def extract_keywords(text: str):
        """Simple keyword extraction fallback"""
        keywords = []
        tech_terms = ['AI', 'API', 'IoT', 'Cloud', 'Data', 'Security', 'Web', 'Mobile']
        for term in tech_terms:
            if term.lower() in text.lower():
                keywords.append(term)
        return keywords[:8]

# Simple database path for production
DB_PATH = os.getenv('SQLITE_PATH', '/tmp/news.db')
print(f"Using database at: {DB_PATH}")

def get_db_connection():
    """Get database connection with proper error handling"""
    try:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        # Create directory if needed
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

def init_db():
    """Initialize database with proper structure"""
    try:
        conn = get_db_connection()
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
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS collections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                rules TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS collection_articles (
                collection_id INTEGER,
                article_id INTEGER,
                FOREIGN KEY (collection_id) REFERENCES collections(id),
                FOREIGN KEY (article_id) REFERENCES articles(id),
                UNIQUE(collection_id, article_id)
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(published DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_collection_articles ON collection_articles(collection_id, article_id)")
        
        conn.commit()
        conn.close()
        print("✅ Database initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False

app = FastAPI()

# OpenAI API Key from environment variable
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DB 초기화는 첫 번째 요청 시에만 수행
_db_initialized = False

def ensure_db_initialized():
    global _db_initialized
    if not _db_initialized:
        try:
            init_db()
            _db_initialized = True
        except Exception as e:
            print(f"Database initialization failed: {e}")
            # Continue without initialization

class Article(BaseModel):
    id: int
    title: str
    link: str
    published: str
    source: str
    summary: Optional[str]
    keywords: Optional[str]
    created_at: Optional[str]
    is_favorite: bool = False

class FavoriteRequest(BaseModel):
    article_id: int

class KeywordStats(BaseModel):
    keyword: str
    count: int

class NetworkNode(BaseModel):
    id: str
    label: str
    value: int

class NetworkEdge(BaseModel):
    from_node: str = None
    to: str
    value: int

    model_config = {"field_alias_generator": None}
    
    def dict(self, **kwargs):
        data = super().model_dump(**kwargs)
        if 'from_node' in data:
            data['from'] = data.pop('from_node')
        return data

class CollectionRequest(BaseModel):
    name: str
    rules: Optional[Dict] = None

class NewsCollectionRequest(BaseModel):
    days: int = 30
    max_pages: int = 5

# get_db_connection is now imported from database module

@app.get("/api/articles")
async def get_articles(
    limit: int = Query(100, le=2000),
    offset: int = Query(0, ge=0),
    source: Optional[str] = None,
    search: Optional[str] = None,
    favorites_only: bool = False,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
):
    ensure_db_initialized()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM articles WHERE 1=1"
    params = []
    
    if source:
        query += " AND source = ?"
        params.append(source)
    
    if search:
        query += " AND (title LIKE ? OR summary LIKE ? OR keywords LIKE ?)"
        search_param = f"%{search}%"
        params.extend([search_param, search_param, search_param])
    
    if favorites_only:
        query += " AND id IN (SELECT article_id FROM favorites)"
    
    if date_from:
        query += " AND DATE(published) >= ?"
        params.append(date_from)
    
    if date_to:
        query += " AND DATE(published) <= ?"
        params.append(date_to)
    
    query += " ORDER BY published DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    cursor.execute(query, params)
    articles = []
    
    favorite_ids = set()
    cursor.execute("SELECT article_id FROM favorites")
    favorite_ids = {row[0] for row in cursor.fetchall()}
    
    cursor.execute(query, params)
    for row in cursor.fetchall():
        article = dict(row)
        article['is_favorite'] = article['id'] in favorite_ids
        articles.append(article)
    
    conn.close()
    return articles

@app.get("/api/sources")
async def get_sources():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT source FROM articles ORDER BY source")
    sources = [row[0] for row in cursor.fetchall()]
    conn.close()
    return sources

@app.get("/api/keywords/stats")
async def get_keyword_stats(limit: int = Query(50, le=200)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT keywords FROM articles WHERE keywords IS NOT NULL")
    
    keyword_counter = {}
    for row in cursor.fetchall():
        keywords = row[0].split(',') if row[0] else []
        for kw in keywords:
            kw = kw.strip()
            if kw:
                keyword_counter[kw] = keyword_counter.get(kw, 0) + 1
    
    conn.close()
    
    sorted_keywords = sorted(keyword_counter.items(), key=lambda x: x[1], reverse=True)[:limit]
    return [{"keyword": k, "count": v} for k, v in sorted_keywords]

@app.get("/api/keywords/network")
async def get_keyword_network(limit: int = Query(30, le=100)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT keywords FROM articles WHERE keywords IS NOT NULL")
    
    keyword_docs = []
    for row in cursor.fetchall():
        keywords = row[0].split(',') if row[0] else []
        keywords = [kw.strip() for kw in keywords if kw.strip()]
        if keywords:
            keyword_docs.append(keywords)
    
    conn.close()
    
    keyword_counter = {}
    cooccurrence = {}
    
    for doc_keywords in keyword_docs:
        for kw in doc_keywords:
            keyword_counter[kw] = keyword_counter.get(kw, 0) + 1
        
        for i, kw1 in enumerate(doc_keywords):
            for kw2 in doc_keywords[i+1:]:
                pair = tuple(sorted([kw1, kw2]))
                cooccurrence[pair] = cooccurrence.get(pair, 0) + 1
    
    top_keywords = sorted(keyword_counter.items(), key=lambda x: x[1], reverse=True)[:limit]
    top_keyword_set = {k for k, _ in top_keywords}
    
    nodes = [{"id": kw, "label": kw, "value": count} for kw, count in top_keywords]
    edges = []
    
    for (kw1, kw2), weight in cooccurrence.items():
        if kw1 in top_keyword_set and kw2 in top_keyword_set and weight > 1:
            edges.append({"from": kw1, "to": kw2, "value": weight})
    
    return {"nodes": nodes, "edges": edges}

@app.get("/api/favorites")
async def get_favorites():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.* FROM articles a
        JOIN favorites f ON a.id = f.article_id
        ORDER BY f.created_at DESC
    """)
    
    favorites = []
    for row in cursor.fetchall():
        article = dict(row)
        article['is_favorite'] = True
        favorites.append(article)
    
    conn.close()
    return favorites

@app.post("/api/favorites/add")
async def add_favorite(request: FavoriteRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT OR IGNORE INTO favorites (article_id) VALUES (?)",
            (request.article_id,)
        )
        conn.commit()
        return {"success": True, "message": "Favorite added"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()

@app.delete("/api/favorites/{article_id}")
async def remove_favorite(article_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM favorites WHERE article_id = ?", (article_id,))
    conn.commit()
    conn.close()
    
    return {"success": True, "message": "Favorite removed"}

@app.get("/api/stats")
async def get_stats():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM articles")
    total_articles = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT source) FROM articles")
    total_sources = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM favorites")
    total_favorites = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT DATE(published) as date, COUNT(*) as count 
        FROM articles 
        WHERE published >= date('now', '-7 days')
        GROUP BY DATE(published)
        ORDER BY date
    """)
    daily_counts = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return {
        "total_articles": total_articles,
        "total_sources": total_sources,
        "total_favorites": total_favorites,
        "daily_counts": daily_counts
    }

# Inline news collection functions
def collect_from_rss(feed_url: str, source: str, max_items: int = 10):
    """Collect articles from RSS feed"""
    try:
        import feedparser
        import requests
        from datetime import datetime
        
        print(f"📡 Collecting from {source}...")
        
        feed = feedparser.parse(feed_url)
        if not hasattr(feed, 'entries') or not feed.entries:
            return []
        
        articles = []
        for entry in feed.entries[:max_items]:
            try:
                title = getattr(entry, 'title', '').strip()
                link = getattr(entry, 'link', '').strip()
                
                if not title or not link:
                    continue
                
                published = getattr(entry, 'published', datetime.now().strftime('%Y-%m-%d'))
                summary = getattr(entry, 'summary', '')[:500] if hasattr(entry, 'summary') else ''
                
                articles.append({
                    'title': title,
                    'link': link,
                    'published': published,
                    'source': source,
                    'summary': summary
                })
                
            except Exception:
                continue
        
        print(f"✅ Collected {len(articles)} from {source}")
        return articles
        
    except Exception as e:
        print(f"❌ Error collecting from {source}: {e}")
        return []

def save_articles_to_db(articles):
    """Save articles to database"""
    if not articles:
        return {'inserted': 0, 'skipped': 0}
    
    conn = get_db_connection()
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
                
        except Exception:
            stats['skipped'] += 1
    
    conn.commit()
    conn.close()
    return stats

def run_collection():
    """Run news collection from major sources"""
    feeds = [
        {"url": "https://it.donga.com/feeds/rss/", "source": "IT동아"},
        {"url": "https://rss.etnews.com/Section902.xml", "source": "전자신문"},
        {"url": "https://techcrunch.com/feed/", "source": "TechCrunch"},
        {"url": "https://www.theverge.com/rss/index.xml", "source": "The Verge"},
        {"url": "https://www.engadget.com/rss.xml", "source": "Engadget"},
    ]
    
    all_articles = []
    for feed in feeds:
        articles = collect_from_rss(feed["url"], feed["source"])
        all_articles.extend(articles)
    
    if all_articles:
        stats = save_articles_to_db(all_articles)
        return True, len(all_articles), stats
    
    return False, 0, {}

# 뉴스 수집 API
@app.post("/api/collect-news")
async def collect_news(background_tasks: BackgroundTasks):
    """RSS 피드에서 뉴스를 수집합니다."""
    try:
        background_tasks.add_task(run_background_collection)
        return {"message": "뉴스 수집을 시작했습니다.", "status": "started"}
    except Exception as e:
        return {"message": f"오류: {str(e)}", "status": "error"}

async def run_background_collection():
    """백그라운드 뉴스 수집"""
    try:
        success, count, stats = run_collection()
        print(f"뉴스 수집 완료: {count}개 처리, {stats.get('inserted', 0)}개 신규")
    except Exception as e:
        print(f"뉴스 수집 오류: {e}")

# 수동 뉴스 수집 엔드포인트 (즉시 실행)
@app.post("/api/collect-news-now")
async def collect_news_now():
    """즉시 뉴스를 수집합니다."""
    try:
        success, count, stats = run_collection()
        
        if success:
            # 현재 통계
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM articles")
            total = cursor.fetchone()[0]
            cursor.execute("SELECT source, COUNT(*) FROM articles GROUP BY source ORDER BY COUNT(*) DESC")
            by_source = dict(cursor.fetchall())
            conn.close()
            
            return {
                "message": f"뉴스 수집 완료: {stats.get('inserted', 0)}개 신규 추가",
                "status": "success",
                "processed": count,
                "inserted": stats.get('inserted', 0),
                "skipped": stats.get('skipped', 0),
                "total_articles": total,
                "by_source": by_source
            }
        else:
            return {"message": "뉴스 수집 실패", "status": "error"}
            
    except Exception as e:
        return {"message": f"오류: {str(e)}", "status": "error"}

# 정적 파일 서빙 설정 (React 빌드 파일)
frontend_dist = Path(__file__).parent.parent / "frontend" / "news-app" / "dist"
if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")
    
    @app.get("/")
    async def serve_frontend():
        index_path = frontend_dist / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
        else:
            return {"message": "Frontend not built. Please run 'npm run build' in frontend/news-app directory"}
else:
    @app.get("/")
    async def root():
        return {"message": "News API Server is running. Frontend not found."}

# 컬렉션 관리 API
@app.get("/api/collections")
async def get_collections():
    """모든 컬렉션 목록을 반환합니다."""
    try:
        ensure_db_initialized()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all collections
        cursor.execute("""
            SELECT c.id, c.name, c.rules, c.created_at, 
                   COUNT(ca.article_id) as article_count
            FROM collections c
            LEFT JOIN collection_articles ca ON c.id = ca.collection_id
            GROUP BY c.id
        """)
        
        collections = []
        for row in cursor.fetchall():
            collection = dict(row)
            collection['rules'] = json.loads(collection['rules']) if collection['rules'] else {}
            collection['count'] = collection['article_count']
            collections.append(collection)
        
        conn.close()
        return collections
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"컬렉션 조회 실패: {str(e)}")

@app.post("/api/collections")
async def create_collection(request: CollectionRequest):
    """새로운 컬렉션을 생성합니다."""
    try:
        ensure_db_initialized()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create the collection
        cursor.execute("""
            INSERT INTO collections (name, rules) VALUES (?, ?)
        """, (request.name, json.dumps(request.rules) if request.rules else None))
        
        collection_id = cursor.lastrowid
        
        # Add articles based on rules
        if request.rules and 'include_keywords' in request.rules:
            keywords = request.rules['include_keywords']
            keyword_filter = ' OR '.join([f"keywords LIKE '%{kw}%'" for kw in keywords])
            
            cursor.execute(f"""
                INSERT INTO collection_articles (collection_id, article_id)
                SELECT ?, id FROM articles 
                WHERE {keyword_filter}
            """, (collection_id,))
            
            added_count = cursor.rowcount
        else:
            added_count = 0
        
        conn.commit()
        conn.close()
        
        return {"message": f"컬렉션 '{request.name}' 생성 완료", "added_articles": added_count, "collection_id": collection_id}
        
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail=f"컬렉션 '{request.name}'이 이미 존재합니다.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"컬렉션 생성 실패: {str(e)}")

# 키워드 추출 API  
@app.post("/api/extract-keywords/{article_id}")
async def extract_article_keywords(article_id: int):
    """특정 기사의 키워드를 추출합니다."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT title, summary FROM articles WHERE id = ?", (article_id,))
        article = cursor.fetchone()
        
        if not article:
            raise HTTPException(status_code=404, detail="기사를 찾을 수 없습니다.")
        
        text = f"{article['title']} {article['summary'] or ''}"
        keywords = extract_keywords(text)
        
        # 키워드 업데이트
        cursor.execute("UPDATE articles SET keywords = ? WHERE id = ?", 
                      (",".join(keywords), article_id))
        conn.commit()
        conn.close()
        
        return {"keywords": keywords, "message": "키워드 추출 완료"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"키워드 추출 실패: {str(e)}")

# 번역 API
@app.post("/api/translate/{article_id}")  
async def translate_article(article_id: int):
    """특정 기사를 번역합니다."""
    try:
        ensure_db_initialized()
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM articles WHERE id = ?", (article_id,))
        article = cursor.fetchone()
        
        if not article:
            raise HTTPException(status_code=404, detail="기사를 찾을 수 없습니다.")
        
        article_dict = dict(article)
        
        # Simple translation using basic patterns (without external API)
        # This is a placeholder - in production, use proper translation API
        translated_title = article_dict['title']
        translated_summary = article_dict.get('summary', '')
        
        # Basic keyword-based translation hints
        translation_map = {
            'AI': '인공지능',
            'Machine Learning': '머신러닝',
            'Deep Learning': '딥러닝',
            'Cloud': '클라우드',
            'Security': '보안',
            'Data': '데이터',
            'API': 'API',
            'Web': '웹',
            'Mobile': '모바일',
            'Database': '데이터베이스'
        }
        
        # Check if article appears to be in English
        is_english = any(word in translated_title.lower() for word in ['the', 'and', 'or', 'is', 'to'])
        
        if is_english:
            # Apply basic translations for known terms
            for eng, kor in translation_map.items():
                if eng.lower() in translated_title.lower():
                    translated_title = f"{translated_title} ({kor} 관련)"
                    break
            
            article_dict['translated_title'] = translated_title
            article_dict['translated_summary'] = f"[자동 번역 미지원] {translated_summary[:100]}..."
            article_dict['is_translated'] = True
            message = "기본 번역 제공 (전문 번역 서비스는 API 키 설정 필요)"
        else:
            article_dict['is_translated'] = False
            message = "한국어 기사입니다"
        
        conn.close()
        
        return {"message": message, "article": article_dict}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"번역 실패: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
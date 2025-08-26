from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional, Set
import sqlite3
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
from dotenv import load_dotenv

sys.path.append(str(Path(__file__).parent.parent))
from translate_util import translate_rows_if_needed
from keyword_maker import extract_keywords

load_dotenv()

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

DB_PATH = os.getenv("DB_PATH", "news.db")

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

    class Config:
        fields = {'from_node': 'from'}

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/api/articles")
async def get_articles(
    limit: int = Query(100, le=2000),
    offset: int = Query(0, ge=0),
    source: Optional[str] = None,
    search: Optional[str] = None,
    favorites_only: bool = False
):
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
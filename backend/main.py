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
import asyncio

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

class CollectionRequest(BaseModel):
    name: str
    rules: Optional[Dict] = None

class NewsCollectionRequest(BaseModel):
    days: int = 30
    max_pages: int = 5

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
    favorites_only: bool = False,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
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

# 뉴스 수집 API
@app.post("/api/collect-news")
async def collect_news(background_tasks: BackgroundTasks, request: NewsCollectionRequest):
    """RSS 피드에서 뉴스를 수집합니다."""
    background_tasks.add_task(run_news_collection, request.days, request.max_pages)
    return {"message": "뉴스 수집을 시작했습니다.", "status": "started"}

async def run_news_collection(days: int, max_pages: int):
    """백그라운드에서 뉴스 수집을 실행합니다."""
    try:
        # archive_last_year.py 실행
        import subprocess
        cmd = [
            "python", 
            str(Path(__file__).parent.parent / "archive_last_year.py"),
            "--days", str(days),
            "--max-pages", str(max_pages)
        ]
        subprocess.run(cmd, check=True)
        print(f"뉴스 수집 완료: {days}일, {max_pages}페이지")
    except Exception as e:
        print(f"뉴스 수집 실패: {e}")

# 컬렉션 관리 API
@app.get("/api/collections")
async def get_collections():
    """모든 컬렉션 목록을 반환합니다."""
    try:
        # playlist_collections.py 활용
        from playlist_collections import ThemeCollections
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM articles")
        
        # DataFrame으로 변환
        articles_data = []
        for row in cursor.fetchall():
            articles_data.append(dict(row))
        
        if not articles_data:
            return []
        
        df = pd.DataFrame(articles_data)
        tm = ThemeCollections(df)
        
        # 기본 컬렉션들 생성 (없는 경우)
        collections_info = [
            {
                "name": "반도체 동향",
                "rules": {
                    "include_keywords": ["반도체", "메모리", "시스템반도체", "파운드리"],
                    "include_main": ["첨단 제조·기술 산업"],
                    "include_sub": ["반도체"]
                }
            },
            {
                "name": "AI/데이터센터",
                "rules": {
                    "include_keywords": ["AI", "인공지능", "데이터센터", "클라우드"],
                    "include_main": ["디지털·ICT 산업"]
                }
            }
        ]
        
        result = []
        for coll_info in collections_info:
            try:
                tm.create(coll_info["name"], coll_info["rules"])
                added = tm.autofill(coll_info["name"])
                df_coll = tm.get_dataframe(coll_info["name"], ["id", "title", "source", "published"])
                
                result.append({
                    "name": coll_info["name"],
                    "count": len(df_coll),
                    "rules": coll_info["rules"],
                    "articles": df_coll.to_dict('records') if not df_coll.empty else []
                })
            except ValueError:
                # 이미 존재하는 경우
                pass
        
        conn.close()
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"컬렉션 조회 실패: {str(e)}")

@app.post("/api/collections")
async def create_collection(request: CollectionRequest):
    """새로운 컬렉션을 생성합니다."""
    try:
        from playlist_collections import ThemeCollections
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM articles")
        
        articles_data = [dict(row) for row in cursor.fetchall()]
        if not articles_data:
            raise HTTPException(status_code=400, detail="기사 데이터가 없습니다.")
        
        df = pd.DataFrame(articles_data)
        tm = ThemeCollections(df)
        tm.create(request.name, request.rules)
        added = tm.autofill(request.name)
        
        conn.close()
        return {"message": f"컬렉션 '{request.name}' 생성 완료", "added_articles": added}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
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
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM articles WHERE id = ?", (article_id,))
        article = cursor.fetchone()
        
        if not article:
            raise HTTPException(status_code=404, detail="기사를 찾을 수 없습니다.")
        
        # DataFrame으로 변환
        df = pd.DataFrame([dict(article)])
        translated_df = translate_rows_if_needed(df)
        
        # 번역된 내용 업데이트
        translated_article = translated_df.iloc[0]
        cursor.execute("""
            UPDATE articles 
            SET title = ?, summary = ?
            WHERE id = ?
        """, (translated_article['title'], translated_article['summary'], article_id))
        
        conn.commit()
        conn.close()
        
        return {"message": "번역 완료", "translated": dict(translated_article)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"번역 실패: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
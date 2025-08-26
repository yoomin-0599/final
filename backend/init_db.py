#!/usr/bin/env python3
"""
데이터베이스 초기화 스크립트
필요한 테이블이 없으면 생성합니다.
"""

import sqlite3
import os
from pathlib import Path

DB_PATH = os.getenv("DB_PATH", "news.db")

def init_database():
    """데이터베이스와 필요한 테이블들을 생성합니다."""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # articles 테이블 생성
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            link TEXT UNIQUE NOT NULL,
            published TEXT NOT NULL,
            source TEXT NOT NULL,
            raw_text TEXT,
            summary TEXT,
            keywords TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # favorites 테이블 생성
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (article_id) REFERENCES articles(id),
            UNIQUE(article_id)
        )
    """)
    
    # 인덱스 생성
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_articles_published 
        ON articles(published DESC)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_articles_source 
        ON articles(source)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_favorites_article_id 
        ON favorites(article_id)
    """)
    
    conn.commit()
    conn.close()
    
    print(f"Database initialized at: {DB_PATH}")
    
    # 데이터베이스 정보 출력
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM articles")
    article_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM favorites")
    favorite_count = cursor.fetchone()[0]
    
    print(f"Articles: {article_count}")
    print(f"Favorites: {favorite_count}")
    
    conn.close()

if __name__ == "__main__":
    init_database()
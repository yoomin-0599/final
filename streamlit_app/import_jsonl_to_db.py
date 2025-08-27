# import_jsonl_to_db.py
# 사용법:
#   python import_jsonl_to_db.py --jsonl "C:\경로\archive_last_year.jsonl" --db "C:\경로\news.db"

#이거 터미널에 쓰기
#"""
#cd "C:\Users\User\Desktop\app (2)\app"
#python ".\import_jsonl_to_db.py" --jsonl ".\archive_last_year.jsonl" --db ".\news.db"



import os, json, sqlite3, argparse
from pathlib import Path

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = lambda *a, **k: None

def main():
    # argparse 설정
    p = argparse.ArgumentParser(description="JSONL → SQLite 적재 스크립트")
    # ⬇⬇ 변경 포인트: required 제거 + 기본값 제공
    p.add_argument("--jsonl", default="archive_last_year.jsonl", help="수입할 JSONL 경로 (기본: archive_last_year.jsonl)")
    p.add_argument("--db", default=None, help="SQLite DB 경로(.env의 DB_PATH 없으면 news.db)")
    # ⬇⬇ 인자 없으면 []를 넣어 기본값으로 파싱
    args = p.parse_args(args=None if len(sys.argv) > 1 else [])

    # .env에서 DB_PATH 읽기(있으면), 없으면 news.db
    env_path = Path(__file__).resolve().with_name(".env")
    if env_path.exists():
        load_dotenv(env_path)
    db_path = args.db or os.getenv("DB_PATH", "news.db")

    # JSONL 존재 확인
    if not os.path.exists(args.jsonl):
        raise FileNotFoundError(f"JSONL 파일이 없습니다: {args.jsonl}")

    # DB 연결 및 테이블 준비
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
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
    conn.commit()

    inserted, updated, skipped = 0, 0, 0
    with open(args.jsonl, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                skipped += 1
                continue

            title     = (r.get("title") or "").strip()
            link      = (r.get("link") or "").strip()
            published = (r.get("published") or "").strip()
            source    = (r.get("source") or "").strip()
            summary   = (r.get("summary") or "").strip()
            keywords  = r.get("keywords")

            if not (title and link):
                skipped += 1
                continue

            if isinstance(keywords, (list, tuple)):
                keywords_json = json.dumps(list(keywords), ensure_ascii=False)
            elif isinstance(keywords, str):
                keywords_json = keywords
            else:
                keywords_json = "[]"

            raw_text = r.get("raw_text", "")
            category = r.get("category", None)

            cur.execute("""
            INSERT INTO articles (title, link, published, source, raw_text, summary, keywords, category)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(link) DO UPDATE SET
                title=excluded.title,
                published=excluded.published,
                source=excluded.source,
                raw_text=COALESCE(excluded.raw_text, raw_text),
                summary=excluded.summary,
                keywords=excluded.keywords,
                category=COALESCE(excluded.category, category)
            """, (title, link, published, source, raw_text, summary, keywords_json, category))
            if cur.rowcount == 1:
                inserted += 1
            else:
                updated += 1

    conn.commit()
    conn.close()
    print(f"[완료] 신규 {inserted} · 업데이트 {updated} · 스킵 {skipped} → DB: {db_path}")

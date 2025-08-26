# translate_util.py
# 한국어 자동 번역 유틸 (OpenAI 사용, DB 캐시)
from __future__ import annotations
import os, re, json, sqlite3, time
from typing import List, Dict, Optional
from datetime import datetime

# OpenAI >= 1.x
try:
    from openai import OpenAI
except Exception:
    OpenAI = None

# 한글 여부 간단 판정
_HANGUL_RE = re.compile(r"[가-힣]")

def is_korean(text: str, min_chars: int = 5, ratio: float = 0.2) -> bool:
    if not text:
        return True
    total = max(len(text), 1)
    ko = len(_HANGUL_RE.findall(text))
    if len(text) < min_chars:
        return True
    return (ko / total) >= ratio

def _ensure_table(conn: sqlite3.Connection):
    conn.execute("""
    CREATE TABLE IF NOT EXISTS translations (
        link TEXT PRIMARY KEY,
        title_ko TEXT,
        summary_ko TEXT,
        content_hash TEXT,
        updated_at TEXT DEFAULT (datetime('now'))
    )
    """)
    conn.commit()

def _content_hash(title: str, summary: str) -> str:
    import hashlib
    raw = (title or "") + "\n" + (summary or "")
    return hashlib.sha256(raw.encode("utf-8", "ignore")).hexdigest()

def _get_cached(conn: sqlite3.Connection, link: str, expect_hash: str):
    cur = conn.execute("SELECT title_ko, summary_ko, content_hash FROM translations WHERE link=?", (link,))
    row = cur.fetchone()
    if not row:
        return None
    title_ko, summary_ko, h = row
    if h == expect_hash and (title_ko or summary_ko):
        return {"title_ko": title_ko or "", "summary_ko": summary_ko or ""}
    return None

def _set_cache(conn: sqlite3.Connection, link: str, title_ko: str, summary_ko: str, h: str):
    conn.execute("""
        INSERT INTO translations (link, title_ko, summary_ko, content_hash, updated_at)
        VALUES (?, ?, ?, ?, datetime('now'))
        ON CONFLICT(link) DO UPDATE SET
            title_ko=excluded.title_ko,
            summary_ko=excluded.summary_ko,
            content_hash=excluded.content_hash,
            updated_at=datetime('now')
    """, (link, title_ko, summary_ko, h))
    conn.commit()

def _get_client():
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key or OpenAI is None:
        return None
    try:
        return OpenAI(api_key=api_key)
    except Exception:
        return None

SYSTEM_PROMPT = (
    "당신은 기술 뉴스 번역가입니다. 다음 텍스트를 자연스러운 한국어로 번역하되, "
    "고유명사/모델명/약어(예: HBM, NPU, LLM, GPT)는 원문을 유지하거나 괄호 병기하세요. "
    "과장·추측 없이 간결하고 명확하게 번역합니다."
)

def _translate_pair(client, model: str, title: str, summary: str, timeout: float = 18.0) -> Dict[str, str]:
    # 실패 시 원문 반환(안전)
    if not client:
        return {"title_ko": title, "summary_ko": summary}
    user_text = json.dumps({"title": title or "", "summary": summary or ""}, ensure_ascii=False)
    try:
        resp = client.chat.completions.create(
            model=os.getenv("OPENAI_TRANSLATE_MODEL", model),
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"JSON으로 주어진 'title'과 'summary'를 한국어로 번역해 주세요.\n{user_text}\n출력은 JSON으로: {{'title_ko':..., 'summary_ko':...}}"}
            ],
            temperature=0.2,
            timeout=timeout,
        )
        out = resp.choices[0].message.content.strip()
        # 모델이 코드블럭을 붙이면 제거
        out = re.sub(r"^```json|```$", "", out).strip()
        data = json.loads(out)
        tko = (data.get("title_ko") or "").strip()
        sko = (data.get("summary_ko") or "").strip()
        if not tko: tko = title
        if not sko: sko = summary
        return {"title_ko": tko, "summary_ko": sko}
    except Exception:
        return {"title_ko": title, "summary_ko": summary}

def translate_rows_if_needed(rows: List[Dict], db_path: str) -> Dict[str, Dict[str, str]]:
    """
    rows: [{'link':..., 'title':..., 'summary':...}, ...]
    반환: {link: {'title_ko':..., 'summary_ko':...}, ...}
    - 이미 한글이면 pass-through
    - 캐시(hit) 우선
    - 캐시 miss → OpenAI 호출 후 캐시 저장
    """
    out: Dict[str, Dict[str, str]] = {}
    if not rows:
        return out

    enable = os.getenv("ENABLE_TRANSLATE", "1").strip() != "0"
    if not enable:
        return out

    client = _get_client()
    model = os.getenv("OPENAI_TRANSLATE_MODEL", "gpt-4o-mini")

    conn = sqlite3.connect(db_path)
    _ensure_table(conn)

    for r in rows:
        link = (r.get("link") or "").strip()
        title = (r.get("title") or "").strip()
        summary = (r.get("summary") or "").strip()
        if not link:
            continue

        # 이미 한글이면 번역 불필요
        if is_korean(title) and (not summary or is_korean(summary)):
            continue

        h = _content_hash(title, summary)
        cached = _get_cached(conn, link, h)
        if cached:
            out[link] = cached
            continue

        # API 호출(표시 페이지 범위에서만; 비용/속도 최소화)
        pair = _translate_pair(client, model, title, summary)
        _set_cache(conn, link, pair["title_ko"], pair["summary_ko"], h)
        out[link] = pair

        # 너무 빠른 연속 호출 방지(서버/요금 안전장치)
        time.sleep(0.15)

    conn.close()
    return out

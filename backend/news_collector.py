# news_collector.py
# 백엔드용 뉴스 수집 모듈
# 스트림릿 main_app.py의 수집 로직을 백엔드에서 사용할 수 있도록 재구성

from __future__ import annotations
import os, sys, json, sqlite3, time
from typing import List, Dict, Tuple, Optional, Iterable, Set
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

import numpy as np
import pandas as pd
import requests
import feedparser
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# 환경설정 로드
load_dotenv()

# 환경변수 파싱 유틸
def _strip_comment(v: str) -> str:
    v = (v or "").split('#', 1)[0].strip()
    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
        v = v[1:-1].strip()
    return v

def getenv_int(name: str, default: int) -> int:
    raw = _strip_comment(os.getenv(name, str(default)))
    m = re.search(r'-?\d+', raw)
    return int(m.group()) if m else int(default)

def getenv_float(name: str, default: float) -> float:
    raw = _strip_comment(os.getenv(name, str(default)))
    m = re.search(r'-?\d+(?:\.\d+)?', raw)
    return float(m.group()) if m else float(default)

def getenv_bool(name: str, default: bool=False) -> bool:
    raw = _strip_comment(os.getenv(name, str(default))).lower()
    return raw in ("1", "true", "t", "yes", "y", "on")

def getenv_str(name: str, default: str="") -> str:
    return _strip_comment(os.getenv(name, default))

# 설정값
MAX_RESULTS            = getenv_int("MAX_RESULTS", 10)
MAX_TOTAL_PER_SOURCE   = getenv_int("MAX_TOTAL_PER_SOURCE", 200)
RSS_BACKFILL_PAGES     = getenv_int("RSS_BACKFILL_PAGES", 3)

CONNECT_TIMEOUT        = getenv_float("CONNECT_TIMEOUT", 6.0)
READ_TIMEOUT           = getenv_float("READ_TIMEOUT", 10.0)
OPENAI_TIMEOUT         = getenv_float("OPENAI_TIMEOUT", 20.0)

ENABLE_SUMMARY         = getenv_bool("ENABLE_SUMMARY", False)
ENABLE_HTTP_CACHE      = getenv_bool("ENABLE_HTTP_CACHE", True)
HTTP_CACHE_EXPIRE      = getenv_int("HTTP_CACHE_EXPIRE", 3600)
PARALLEL_MAX_WORKERS   = getenv_int("PARALLEL_MAX_WORKERS", 8)
SKIP_UPDATE_IF_EXISTS  = getenv_bool("SKIP_UPDATE_IF_EXISTS", True)

NLP_BACKEND            = getenv_str("NLP_BACKEND", "kiwi").lower()
PER_ARTICLE_SLEEP      = getenv_float("PER_ARTICLE_SLEEP", 0.0)

STRICT_TECH_KEYWORDS   = getenv_bool("STRICT_TECH_KEYWORDS", True)
SKIP_NON_TECH          = getenv_bool("SKIP_NON_TECH", False)

OPENAI_API_KEY         = getenv_str("OPENAI_API_KEY", "")

# RSS 피드 소스
FEEDS: List[Dict[str, str]] = [
    # --- Korea (ko) ---
    {"feed_url": "https://it.donga.com/feeds/rss/",            "source": "IT동아",              "category": "IT",           "lang": "ko"},
    {"feed_url": "https://rss.etnews.com/Section902.xml",      "source": "전자신문_속보",         "category": "IT",           "lang": "ko"},
    {"feed_url": "https://rss.etnews.com/Section901.xml",      "source": "전자신문_오늘의뉴스",     "category": "IT",           "lang": "ko"},
    {"feed_url": "https://zdnet.co.kr/news/news_xml.asp",      "source": "ZDNet Korea",         "category": "IT",           "lang": "ko"},
    {"feed_url": "https://www.itworld.co.kr/rss/all.xml",      "source": "ITWorld Korea",       "category": "IT",           "lang": "ko"},
    {"feed_url": "https://www.ciokorea.com/rss/all.xml",       "source": "CIO Korea",           "category": "IT",           "lang": "ko"},
    {"feed_url": "https://www.bloter.net/feed",                "source": "Bloter",              "category": "IT",           "lang": "ko"},
    {"feed_url": "https://byline.network/feed/",               "source": "Byline Network",      "category": "IT",           "lang": "ko"},
    {"feed_url": "https://platum.kr/feed",                     "source": "Platum",              "category": "Startup",      "lang": "ko"},
    {"feed_url": "https://www.boannews.com/media/news_rss.xml","source": "보안뉴스",             "category": "Security",     "lang": "ko"},
    {"feed_url": "https://it.chosun.com/rss.xml",              "source": "IT조선",              "category": "IT",           "lang": "ko"},
    {"feed_url": "https://www.ddaily.co.kr/news_rss.php",      "source": "디지털데일리",           "category": "IT",           "lang": "ko"},
    {"feed_url": "https://www.kbench.com/rss.xml",             "source": "KBench",              "category": "IT",           "lang": "ko"},
    {"feed_url": "https://www.sedaily.com/rss/IT.xml",         "source": "서울경제 IT",           "category": "IT",           "lang": "ko"},
    {"feed_url": "https://www.hankyung.com/feed/it",           "source": "한국경제 IT",            "category": "IT",           "lang": "ko"},

    # --- Global (en) ---
    {"feed_url": "https://techcrunch.com/feed/",               "source": "TechCrunch",          "category": "Tech",         "lang": "en"},
    {"feed_url": "https://www.eetimes.com/feed/",              "source": "EE Times",            "category": "Electronics",  "lang": "en"},
    {"feed_url": "https://spectrum.ieee.org/rss/fulltext",     "source": "IEEE Spectrum",       "category": "Engineering",  "lang": "en"},
    {"feed_url": "http://export.arxiv.org/rss/cs",             "source": "arXiv CS",            "category": "Research",     "lang": "en"},
    {"feed_url": "https://www.nature.com/nel/atom.xml",        "source": "Nature Electronics",  "category": "Research",     "lang": "en"},
    {"feed_url": "https://www.technologyreview.com/feed/",     "source": "MIT Tech Review",     "category": "Tech",         "lang": "en"},
    {"feed_url": "https://www.theverge.com/rss/index.xml",     "source": "The Verge",           "category": "Tech",         "lang": "en"},
    {"feed_url": "https://www.wired.com/feed/rss",             "source": "WIRED",               "category": "Tech",         "lang": "en"},
    {"feed_url": "https://www.engadget.com/rss.xml",           "source": "Engadget",            "category": "Tech",         "lang": "en"},
    {"feed_url": "https://venturebeat.com/category/ai/feed/",  "source": "VentureBeat AI",      "category": "AI",           "lang": "en"},
]

HEADERS = {"User-Agent": "Mozilla/5.0 (NewsAgent/1.0)"}

# HTTP 세션 설정
try:
    if ENABLE_HTTP_CACHE:
        from requests_cache import CachedSession
        SESSION = CachedSession('http_cache', expire_after=HTTP_CACHE_EXPIRE)
    else:
        SESSION = requests.Session()
except Exception:
    SESSION = requests.Session()

ADAPTER = requests.adapters.HTTPAdapter(pool_connections=10, pool_maxsize=20, max_retries=1)
SESSION.mount("http://", ADAPTER)
SESSION.mount("https://", ADAPTER)

# 불용어 및 기술 키워드 정의
STOP_EXACT: Set[str] = set(map(str.lower, """
있 수 김 길 가 말 d 얼 b 백 보 위 년 명 바꾸 만 것 jtbc x 하기 작 더 는 은 이 가 를 에 와 과 도 으로 로 부터 에서 까지 에게 한 와/과 에게서 하 하다 입니다 기자 사진 제공 영상 기사 입력 전 날 주 월 년 오늘 내일 어제
""".split()))

STOP_WORDS = set([
    "기자","뉴스","특파원","오늘","매우","기사","사진","영상","제공","입력",
    "것","수","등","및","그리고","그러나","하지만","지난","이번","관련","대한","통해","대해","위해",
    "입니다","한다","했다","하였다","에서는","에서","대한","이날","라며","다고","였다","했다가","하며",
]) | STOP_EXACT

TECH_ALLOW_TERMS = set(map(str.lower, """
ai 인공지능 머신러닝 딥러닝 생성형 챗gpt 로보틱스 로봇 자동화 협동로봇
반도체 메모리 dram nand ddr sram hbm 시스템 반도체 파운드리 웨이퍼 소자 공정 노광 euv 장비 소재
npu tpu gpu cpu dsp isp fpga asic 칩셋 칩 설계 리소그래피 패키징 하이브리드 본딩
이차전지 배터리 ess 양극재 음극재 전해질 분리막 고체전지 전고체 전기차 ev hev phev bms
자율주행 라이다 레이더 센서 카메라 제어기 ecu v2x
통신 네트워크 5g 6g lte nr 위성 mmwave 백홀 fronthaul 스몰셀
ict 클라우드 엣지컴퓨팅 엣지 컴퓨팅 서버 데이터센터 쿠버네티스 컨테이너 devops cicd 오브젝트스토리지 객체저장
소프트웨어 플랫폼 saas paas iaas 보안 암호 인증 키관리 키체인 취약점 제로트러스트
핀테크 블록체인 분산원장 defi nft
모델 학습 파인튜닝 튜닝 프롬프트 추론 인퍼런스 토큰 임베딩 경량화 양자화 distillation 지식증류
사물인터넷 iot 산업용iot iiot plc scada mes erp
디스플레이 oled qd 마이크로 led lcd microled micro-led
바이오 바이오센서 유전자치료제 세포치료제 의료기기 헬스케어 디지털 헬스 웨어러블 원격진료
""".split()))

# Import database module
try:
    from database import db, get_db_connection, init_db
    DB_MODULE_AVAILABLE = True
except ImportError:
    DB_MODULE_AVAILABLE = False
    # Fallback to sqlite for development
    DB_PATH = getenv_str("DB_PATH", "news.db")
    
    def init_db():
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("""
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
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS favorites (
            article_id INTEGER UNIQUE,
            created_at TEXT DEFAULT (datetime('now'))
        );
        """)
        conn.commit()
        conn.close()
        
    def get_db_connection():
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

def canonicalize_link(url: str) -> str:
    try:
        u = urlparse(url)
        scheme = (u.scheme or "https").lower()
        netloc = (u.netloc or "").lower()
        path = (u.path or "").rstrip("/")
        drop = {"utm_source","utm_medium","utm_campaign","utm_term","utm_content","utm_id","utm_name",
                "gclid","fbclid","igshid","spm","ref","ref_src","cmpid"}
        qs = [(k, v) for k, v in parse_qsl(u.query, keep_blank_values=True) if k.lower() not in drop]
        query = urlencode(qs, doseq=True)
        return urlunparse((scheme, netloc, path, u.params, query, ""))
    except Exception:
        return url

def extract_main_text(url: str) -> str:
    try:
        r = SESSION.get(url, headers=HEADERS, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT))
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        art = soup.find("article")
        if art and art.get_text(strip=True):
            return art.get_text("\n", strip=True)
        candidates = soup.select(
            "div[id*='content'], div[class*='content'], "
            "div[id*='article'], div[class*='article'], "
            "section[id*='content'], section[class*='content'], "
            "div[id*='news'], div[class*='news']"
        )
        best = max((c for c in candidates), key=lambda c: len(c.get_text(strip=True)), default=None)
        if best and len(best.get_text(strip=True)) > 200:
            return best.get_text("\n", strip=True)
        md = soup.find("meta", attrs={"name":"description"}) or soup.find("meta", attrs={"property":"og:description"})
        if md and md.get("content"):
            return md["content"]
    except Exception:
        pass
    return ""

def parse_feed(feed_url: str):
    try:
        feed = feedparser.parse(feed_url)
        if not hasattr(feed, "entries"): return None
        return feed
    except Exception:
        return None

def expand_paged_feed_urls(feed_url: str, pages: int) -> List[str]:
    """WordPress 계열 /feed/ 인 경우 ?paged=2..N 로 확장해 과거 기사도 수집"""
    urls = [feed_url]
    if re.search(r"/feed/?$", feed_url, re.IGNORECASE):
        for i in range(2, max(2, pages+1)):
            sep = "&" if "?" in feed_url else "?"
            urls.append(f"{feed_url}{sep}paged={i}")
    return urls

def is_meaningless_token(w: str) -> bool:
    if not w: return True
    s = w.strip()
    if not s: return True
    sl = s.lower()
    if len(sl) == 1: return True
    if re.fullmatch(r"[\W_]+", sl): return True
    if re.fullmatch(r"\d+", sl): return True
    if re.fullmatch(r"[\u1100-\u11FF\u3130-\u318F]", s): return True
    if sl in STOP_EXACT: return True
    return False

def is_tech_term(w: str) -> bool:
    if not w: return False
    s = w.strip()
    sl = s.lower()
    if sl in TECH_ALLOW_TERMS: return True
    if "반도체" in s or "자율주행" in s or "클라우드" in s or "모델" in s or "알고리즘" in s:
        return True
    return False

def sanitize_summary(s: Optional[str]) -> str:
    if not s: return ""
    t = str(s).strip()
    t = re.sub(r"^\s*\[[^\]]*\]\s*", "", t)
    t = re.sub(r"(^|\s)제목\s*:\s*", r"\1", t)
    t = re.sub(r"(^|\s)첫\s*문장\s*:\s*", r"\1", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t

def _clean_sentences(txt: str, limit_chars: int = 700) -> str:
    t = (txt or "").strip()
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"(기자|사진|영상)\s*=", "", t)
    return t[:limit_chars]

def summarize_kor(title: str, source: str, published: str, text: str) -> str:
    """간단한 요약 생성 (OpenAI 없이)"""
    base = _clean_sentences(text or "", 1200)
    if not base or len(base) < 20:
        return sanitize_summary(f"{title}".strip())
    sents = re.split(r"(?<=[.?!。])\s+", base)
    head = " ".join(sents[:3]) if sents else base
    return sanitize_summary(head)

def extract_keywords_simple(text: str, top_k: int = 30):
    """간단한 키워드 추출 (형태소 분석 없이)"""
    if not text: return []
    
    # 한글, 영문, 숫자만 추출
    tokens = re.findall(r'[가-힣]+|[A-Za-z]+|\d+', text.lower())
    
    # 불용어 제거
    tokens = [t for t in tokens if t not in STOP_WORDS and not is_meaningless_token(t)]
    
    # 기술 용어 필터링 (STRICT_TECH_KEYWORDS가 True일 때)
    if STRICT_TECH_KEYWORDS:
        tokens = [t for t in tokens if is_tech_term(t)]
    
    # 빈도 계산
    counts = Counter(tokens)
    
    return [w for w, _ in counts.most_common(top_k)]

def is_tech_doc(title: str, body: str, keywords: Iterable[str]) -> bool:
    text = f"{title or ''} {body or ''} {' '.join(keywords or [])}"
    for k in (keywords or []):
        if is_tech_term(k): return True
    for term in TECH_ALLOW_TERMS:
        if term in text.lower(): return True
    if re.search(r"(연예|스타|예능|헬스|건강|라이프|맛집|여행|뷰티|운세|게임쇼|e스포츠)", text):
        return False
    return False

def link_exists(link: str) -> bool:
    if DB_MODULE_AVAILABLE:
        results = db.execute_query("SELECT 1 FROM articles WHERE link=? LIMIT 1", (link,))
        return len(results) > 0
    else:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM articles WHERE link=? LIMIT 1", (link,))
        result = cursor.fetchone() is not None
        conn.close()
        return result

def upsert_article(title, link, published, source, raw_text, summary, keywords):
    link = canonicalize_link(link)
    summary = sanitize_summary(summary)
    keywords_json = json.dumps(keywords, ensure_ascii=False)
    
    if DB_MODULE_AVAILABLE:
        try:
            # Try insert first
            db.execute_update("""
                INSERT INTO articles (title, link, published, source, raw_text, summary, keywords, category)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (title, link, published, source, raw_text, summary, keywords_json, None))
            return "insert"
        except:
            # If insert fails, try update
            db.execute_update("""
                UPDATE articles
                   SET title=?, published=?, source=?,
                       raw_text=?, summary=?, keywords=?
                 WHERE link=?
            """, (title, published, source, raw_text, summary, keywords_json, link))
            return "update"
    else:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO articles (title, link, published, source, raw_text, summary, keywords, category)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (title, link, published, source, raw_text, summary, keywords_json, None))
            conn.commit()
            result = "insert"
        except sqlite3.IntegrityError:
            cursor.execute("""
                UPDATE articles
                   SET title=?, published=?, source=?,
                       raw_text=?, summary=?, keywords=?
                 WHERE link=?
            """, (title, published, source, raw_text, summary, keywords_json, link))
            conn.commit()
            result = "update"
        finally:
            conn.close()
        return result

def _process_entry(entry, idx, total, source):
    title = getattr(entry, "title", "").strip()
    link  = canonicalize_link(getattr(entry, "link", "").strip())
    if not (title and link):
        return "skip", idx

    if SKIP_UPDATE_IF_EXISTS and link_exists(link):
        return "skip", idx

    published = getattr(entry, "published", "") or getattr(entry, "updated", "") or datetime.utcnow().strftime("%Y-%m-%d")
    raw_text  = extract_main_text(link) or getattr(entry, "summary", "") or ""
    summary   = summarize_kor(title, source, published, raw_text or title)
    keywords  = extract_keywords_simple(raw_text or summary, top_k=30)

    if SKIP_NON_TECH and not is_tech_doc(title, raw_text, keywords):
        return "skip_nontech", idx

    res = upsert_article(title, link, published, source, raw_text, summary, keywords)

    if PER_ARTICLE_SLEEP > 0:
        time.sleep(PER_ARTICLE_SLEEP)
    return res, idx

def fetch_and_store_news(feed_url: str, source: str, max_total=None):
    if max_total is None:
        max_total = MAX_TOTAL_PER_SOURCE

    if not feed_url:
        print(f"- {source}: feed_url 없음 → 건너뜀")
        return

    urls = expand_paged_feed_urls(feed_url, RSS_BACKFILL_PAGES)
    print(f"**▷ {source}** 피드 읽는 중… (확장 {len(urls)}개)")

    entries_all = []
    for i, u in enumerate(urls, 1):
        feed = parse_feed(u)
        if feed is None:
            print(f"  - RSS 파싱 실패/비호환: {u} → 건너뜀")
            continue
        entries = feed.entries or []
        if MAX_RESULTS:
            entries = entries[:MAX_RESULTS]
        entries_all.extend(entries)
        print(f"  - {i}/{len(urls)}: 항목 {len(entries)}건")

        if len(entries_all) >= max_total:
            break

    if not entries_all:
        print(f"◼ {source}: 수집된 항목 없음")
        return

    # 중복 제거 (링크 기준)
    seen = set()
    uniq_entries = []
    for e in entries_all:
        link = canonicalize_link(getattr(e, "link", ""))
        if not link or link in seen:
            continue
        seen.add(link)
        uniq_entries.append(e)

    print(f"- 총 처리 대상: {len(uniq_entries)}건 (중복 제거 후)")

    inserted, updated, skipped, skipped_nontech = 0, 0, 0, 0

    if not ENABLE_SUMMARY and len(uniq_entries) > 0:
        workers = max(1, PARALLEL_MAX_WORKERS)
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = [ex.submit(_process_entry, e, i, len(uniq_entries), source)
                    for i, e in enumerate(uniq_entries, 1)]
            for fut in as_completed(futs):
                res, idx = fut.result()
                if   res == "insert": inserted += 1; print(f"[{idx}/{len(uniq_entries)}] ✅ 신규 저장")
                elif res == "update": updated  += 1; print(f"[{idx}/{len(uniq_entries)}] 🔄 업데이트")
                elif res == "skip_nontech":    skipped_nontech += 1
                else:                           skipped += 1
    else:
        for idx, entry in enumerate(uniq_entries, 1):
            res, _ = _process_entry(entry, idx, len(uniq_entries), source)
            if   res == "insert": inserted += 1; print(f"[{idx}/{len(uniq_entries)}] ✅ 신규 저장")
            elif res == "update": updated  += 1; print(f"[{idx}/{len(uniq_entries)}] 🔄 업데이트")
            elif res == "skip_nontech":    skipped_nontech += 1
            else:                           skipped += 1

    print(f"◼ {source}: 신규 {inserted} · 업데이트 {updated} · 스킵 {skipped} · 비기술스킵 {skipped_nontech}")

def collect_all_news():
    """모든 뉴스 소스 수집"""
    print("⏳ 뉴스 수집/요약/키워드 시작")
    for f in FEEDS:
        fetch_and_store_news(f.get("feed_url"), f.get("source","(unknown)"))
    print("✅ 모든 소스 처리 완료")

if __name__ == "__main__":
    init_db()
    collect_all_news()
# archive_last_year.py
# ─────────────────────────────────────────────────────────────
# 지난 1년(기본) 치 뉴스 데이터를 RSS 기반으로 백필 수집하여
# JSONL/JSON/CSV 로 저장합니다. (프로그램에서 재활용 가능)
#
# ▷ .env(선택) — 스크립트와 같은 폴더에 두면 자동 로드
# DAYS=365
# MAX_PAGES=10
# MAX_RESULTS=50
# PARALLEL=6
# CONNECT_TIMEOUT=6
# READ_TIMEOUT=10
# HTTP_CACHE=1
# HTTP_CACHE_EXPIRE=3600
# FETCH_BODY=0
# OUT_PATH=archive_last_year.jsonl
#
# 실행:
#   python archive_last_year.py
#   python archive_last_year.py --days 365 --max-pages 12 --out my_archive.jsonl
# ─────────────────────────────────────────────────────────────

from __future__ import annotations
import os, json, argparse, re, time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Optional, Iterable, Tuple, Set
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

import feedparser
import requests
from bs4 import BeautifulSoup
from dateutil import parser as dtparser

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = lambda *args, **kwargs: None

# ─────────────────────────────────────────────────────────────
# 1) 설정 로드
# ─────────────────────────────────────────────────────────────
load_dotenv(dotenv_path=Path(__file__).with_name(".env"))

DEFAULT_DAYS         = int(os.getenv("DAYS", "365"))
DEFAULT_MAX_PAGES    = int(os.getenv("MAX_PAGES", "8"))     # /feed/?paged=N 순회 최대 페이지
DEFAULT_MAX_RESULTS  = int(os.getenv("MAX_RESULTS", "50"))  # 페이지 당 항목 최대
DEFAULT_PARALLEL     = int(os.getenv("PARALLEL", "6"))
CONNECT_TIMEOUT      = float(os.getenv("CONNECT_TIMEOUT", "6"))
READ_TIMEOUT         = float(os.getenv("READ_TIMEOUT", "10"))
HTTP_CACHE           = os.getenv("HTTP_CACHE", "1") == "1"
HTTP_CACHE_EXPIRE    = int(os.getenv("HTTP_CACHE_EXPIRE", "3600"))
FETCH_BODY           = os.getenv("FETCH_BODY", "0") == "1"
DEFAULT_OUT_PATH     = os.getenv("OUT_PATH", "archive_last_year.jsonl")

HEADERS = {"User-Agent": "Mozilla/5.0 (NewsArchiveBot/1.0)"}

# HTTP 세션(+캐시 옵션)
try:
    if HTTP_CACHE:
        from requests_cache import CachedSession
        SESSION = CachedSession("http_cache_archive", expire_after=HTTP_CACHE_EXPIRE)
    else:
        SESSION = requests.Session()
except Exception:
    SESSION = requests.Session()

ADAPTER = requests.adapters.HTTPAdapter(pool_connections=20, pool_maxsize=40, max_retries=1)
SESSION.mount("http://", ADAPTER)
SESSION.mount("https://", ADAPTER)

# ─────────────────────────────────────────────────────────────
# 2) 수집 대상 RSS (확장 가능)
#   - WordPress 기반은 /feed/?paged=N 으로 과거 페이지 백필
#   - 기타 RSS는 최신 범위만(피드 제공 범위) 수집
# ─────────────────────────────────────────────────────────────
FEEDS: List[Dict[str, str]] = [
    # --- Korea (ko) ---
    {"feed_url": "https://it.donga.com/feeds/rss/",            "source": "IT동아",              "lang": "ko"},
    {"feed_url": "https://rss.etnews.com/Section902.xml",      "source": "전자신문_속보",         "lang": "ko"},
    {"feed_url": "https://rss.etnews.com/Section901.xml",      "source": "전자신문_오늘의뉴스",     "lang": "ko"},
    {"feed_url": "https://zdnet.co.kr/news/news_xml.asp",      "source": "ZDNet Korea",         "lang": "ko"},
    {"feed_url": "https://www.itworld.co.kr/rss/all.xml",      "source": "ITWorld Korea",       "lang": "ko"},
    {"feed_url": "https://www.ciokorea.com/rss/all.xml",       "source": "CIO Korea",           "lang": "ko"},
    {"feed_url": "https://www.bloter.net/feed",                "source": "Bloter",              "lang": "ko"},
    {"feed_url": "https://byline.network/feed/",               "source": "Byline Network",      "lang": "ko"},
    {"feed_url": "https://platum.kr/feed",                     "source": "Platum",              "lang": "ko"},
    {"feed_url": "https://www.boannews.com/media/news_rss.xml","source": "보안뉴스",             "lang": "ko"},
    {"feed_url": "https://it.chosun.com/rss.xml",              "source": "IT조선",              "lang": "ko"},
    {"feed_url": "https://www.ddaily.co.kr/news_rss.php",      "source": "디지털데일리",           "lang": "ko"},
    {"feed_url": "https://www.kbench.com/rss.xml",             "source": "KBench",              "lang": "ko"},
    {"feed_url": "https://www.sedaily.com/rss/IT.xml",         "source": "서울경제 IT",           "lang": "ko"},
    {"feed_url": "https://www.hankyung.com/feed/it",           "source": "한국경제 IT",            "lang": "ko"},

    # --- Global (en) ---
    {"feed_url": "https://techcrunch.com/feed/",               "source": "TechCrunch",          "lang": "en"},
    {"feed_url": "https://www.eetimes.com/feed/",              "source": "EE Times",            "lang": "en"},
    {"feed_url": "https://spectrum.ieee.org/rss/fulltext",     "source": "IEEE Spectrum",       "lang": "en"},
    {"feed_url": "http://export.arxiv.org/rss/cs",             "source": "arXiv CS",            "lang": "en"},
    {"feed_url": "https://www.nature.com/nel/atom.xml",        "source": "Nature Electronics",  "lang": "en"},
    {"feed_url": "https://www.technologyreview.com/feed/",     "source": "MIT Tech Review",     "lang": "en"},
    {"feed_url": "https://www.theverge.com/rss/index.xml",     "source": "The Verge",           "lang": "en"},
    {"feed_url": "https://www.wired.com/feed/rss",             "source": "WIRED",               "lang": "en"},
    {"feed_url": "https://www.engadget.com/rss.xml",           "source": "Engadget",            "lang": "en"},
    {"feed_url": "https://venturebeat.com/category/ai/feed/",  "source": "VentureBeat AI",      "lang": "en"},
]

# ─────────────────────────────────────────────────────────────
# 3) 유틸
# ─────────────────────────────────────────────────────────────
def canonicalize_link(url: str) -> str:
    try:
        u = urlparse(url)
        scheme = (u.scheme or "https").lower()
        netloc = (u.netloc or "").lower()
        path = (u.path or "").rstrip("/")
        drop = {
            "utm_source","utm_medium","utm_campaign","utm_term","utm_content",
            "utm_id","utm_name","gclid","fbclid","igshid","spm","ref","cmpid","ref_src"
        }
        qs = [(k, v) for k, v in parse_qsl(u.query, keep_blank_values=True) if k.lower() not in drop]
        query = urlencode(qs, doseq=True)
        return urlunparse((scheme, netloc, path, u.params, query, ""))
    except Exception:
        return url

def parse_entry_dt(entry) -> Optional[datetime]:
    # 1) 표준 필드
    for key in ("published", "updated", "pubDate", "date"):
        v = getattr(entry, key, None) or entry.get(key) if isinstance(entry, dict) else None
        if v:
            try:
                dt = dtparser.parse(v)
                if not dt.tzinfo:
                    dt = dt.replace(tzinfo=timezone.utc)  # 가정
                return dt
            except Exception:
                pass
    # 2) parsed struct
    for key in ("published_parsed", "updated_parsed"):
        v = getattr(entry, key, None)
        if v:
            try:
                dt = datetime(*v[:6], tzinfo=timezone.utc)
                return dt
            except Exception:
                pass
    # 3) 실패
    return None

def is_wordpress_feed(url: str) -> bool:
    return re.search(r"/feed/?$", url) is not None

def expand_paged_urls(base_feed: str, max_pages: int) -> List[str]:
    if is_wordpress_feed(base_feed):
        urls = [base_feed]
        for i in range(2, max_pages+1):
            sep = "&" if "?" in base_feed else "?"
            urls.append(f"{base_feed}{sep}paged={i}")
        return urls
    return [base_feed]  # 비워드프레스: 페이지 확장 불가

def parse_feed(url: str):
    try:
        return feedparser.parse(url)
    except Exception:
        return None

def fetch_html(url: str) -> Optional[str]:
    try:
        r = SESSION.get(url, headers=HEADERS, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT))
        r.raise_for_status()
        return r.text
    except Exception:
        return None

def extract_main_text(html: str) -> str:
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
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
    if best and len(best.get_text(strip=True)) > 150:
        return best.get_text("\n", strip=True)
    md = soup.find("meta", attrs={"name":"description"}) or soup.find("meta", attrs={"property":"og:description"})
    if md and md.get("content"):
        return md["content"]
    return ""

def sanitize_text(s: Optional[str]) -> str:
    if not s:
        return ""
    t = re.sub(r"\s+", " ", str(s)).strip()
    return t

# 간단 요약(본문 없으면 제목 기반)
def heuristic_summary(title: str, source: str, body: str) -> str:
    title = sanitize_text(title)
    body = sanitize_text(body)
    if body and len(body) > 80 and title.lower() not in body.lower():
        # 본문 앞문장 2~3개
        parts = re.split(r"(?<=[.?!。])\s+", body)
        return sanitize_text(" ".join(parts[:3]))
    # 제목 기반 2문장
    base = f"{source} 보도. '{title}' 관련 핵심 동향을 간단 정리합니다. 관련 업계/기술 흐름과 시장 경쟁 구도에 주목할 필요가 있습니다."
    return base

# 키워드(기술 토큰 위주, 매우 경량)
STOP = set("""
있 수 것 등 및 그리고 그러나 하지만 지난 이번 관련 대한 통해 위해 입니다 한다 했다 하였다 에서 으로 로 는 은 이 가 를 와 과 도
""".split())
TECH_HINTS = set(map(str.lower, """
ai 인공지능 머신러닝 딥러닝 생성형 챗gpt 로보틱스 로봇 자동화 반도체 메모리 ddr hbm 파운드리 노광 euv 웨이퍼 공정 장비 소재
npu tpu gpu cpu fpga asic 칩 칩셋 모델 학습 추론 인퍼런스 토큰 임베딩 경량화 양자화 라이다 5g 6g 통신 네트워크 클라우드
데이터센터 서버 컨테이너 쿠버네티스 devops 보안 암호 인증 제로트러스트 핀테크 블록체인 iot iiot 디스플레이 oled microled
배터리 이차전지 전고체 자율주행
""".split()))

def extract_keywords(title: str, body: str, top_k: int = 20) -> List[str]:
    text = f"{title} {body}"
    # 단순 토큰화
    toks = re.split(r"[^\w가-힣A-Za-z\+\-]+", text)
    bag = {}
    for t in toks:
        t = t.strip()
        if not t or len(t) < 2:
            continue
        tl = t.lower()
        if tl in STOP:
            continue
        # 기술 힌트에 포함되거나 영문+숫자 혼합 토큰 허용
        if tl in TECH_HINTS or re.fullmatch(r"[a-z]{2,}\d{0,2}", tl):
            bag[tl] = bag.get(tl, 0) + 1
    # 상위 top_k
    out = sorted(bag.items(), key=lambda x: (-x[1], x[0]))[:top_k]
    return [k for k, _ in out]

# ─────────────────────────────────────────────────────────────
# 4) 수집 로직
# ─────────────────────────────────────────────────────────────
def collect_feed_last_year(
    feed_url: str,
    source: str,
    days: int,
    max_pages: int,
    max_results: int,
    fetch_body: bool,
) -> List[Dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    urls = expand_paged_urls(feed_url, max_pages=max_pages)

    items: List[Dict] = []
    seen_links: Set[str] = set()
    stop_due_old = False

    for i, u in enumerate(urls, 1):
        if stop_due_old:
            break
        feed = parse_feed(u)
        if not feed or not getattr(feed, "entries", None):
            continue

        entries = feed.entries
        if max_results and len(entries) > max_results:
            entries = entries[:max_results]

        for e in entries:
            title = sanitize_text(getattr(e, "title", "") or e.get("title") if isinstance(e, dict) else "")
            link = canonicalize_link(getattr(e, "link", "") or e.get("link") if isinstance(e, dict) else "")
            if not title or not link:
                continue
            if link in seen_links:
                continue

            dt = parse_entry_dt(e)
            if dt is None:
                # 날짜가 없으면 보류(본문에서 추정 시도 가능)
                dt = datetime.now(timezone.utc)

            if dt < cutoff:
                # 이 페이지 이후는 대부분 더 과거 → 다음 페이지들 계속 보되,
                # 워드프레스 feed에서는 페이지가 커질수록 과거이므로 계속 순회
                stop_due_old = False  # 워드프레스는 계속 진행
                # 단, 워드프레스가 아닌 경우 대부분 최신만 제공 → 스킵하고 다음 엔트리
                # 여기서는 단순히 continue
                continue

            body = ""
            # 우선 RSS summary 사용
            rss_summary = sanitize_text(getattr(e, "summary", "") or e.get("summary") if isinstance(e, dict) else "")
            if fetch_body:
                html = fetch_html(link)
                if html:
                    body = extract_main_text(html)
            if not body:
                body = rss_summary

            summary = heuristic_summary(title, source, body)
            keywords = extract_keywords(title, body, top_k=20)

            items.append({
                "title": title,
                "link": link,
                "published": dt.astimezone(timezone.utc).isoformat(),
                "source": source,
                "summary": summary,
                "keywords": keywords,
            })
            seen_links.add(link)

        # 예의상 잠깐 쉬기(서버 부담↓)
        time.sleep(0.1)

    return items

# ─────────────────────────────────────────────────────────────
# 5) 저장 유틸
# ─────────────────────────────────────────────────────────────
def save_jsonl(path: str, rows: List[Dict]):
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

def save_json(path: str, rows: List[Dict]):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

def save_csv(path: str, rows: List[Dict]):
    import csv
    if not rows:
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            csv.writer(f).writerow(["title","link","published","source","summary","keywords"])
        return
    keys = ["title","link","published","source","summary","keywords"]
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows:
            row = r.copy()
            if isinstance(row.get("keywords"), list):
                row["keywords"] = ", ".join(row["keywords"])
            w.writerow({k: row.get(k, "") for k in keys})

# ─────────────────────────────────────────────────────────────
# 6) 메인
# ─────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="지난 1년 뉴스 아카이브 수집기 (RSS 백필)")
    ap.add_argument("--days", type=int, default=DEFAULT_DAYS, help="수집 기간 일수 (기본 365)")
    ap.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES, help="워드프레스 /feed/?paged=N 최대 페이지")
    ap.add_argument("--max-results", type=int, default=DEFAULT_MAX_RESULTS, help="페이지당 최대 항목")
    ap.add_argument("--parallel", type=int, default=DEFAULT_PARALLEL, help="피드 병렬 처리 수")
    ap.add_argument("--fetch-body", type=int, default=1 if FETCH_BODY else 0, help="본문까지 긁기(느려짐) 1/0")
    ap.add_argument("--out", type=str, default=DEFAULT_OUT_PATH, help="출력 파일(.jsonl 권장)")
    ap.add_argument("--out-json", type=str, default="", help="JSON 배열 파일도 저장하고 싶을 때 경로")
    ap.add_argument("--out-csv", type=str, default="", help="CSV 파일도 저장하고 싶을 때 경로")
    args = ap.parse_args()

    from concurrent.futures import ThreadPoolExecutor, as_completed

    all_rows: List[Dict] = []
    print(f"[i] 대상 피드: {len(FEEDS)}개, 기간: 최근 {args.days}일, 본문수집={bool(args.fetch_body)}")
    with ThreadPoolExecutor(max_workers=max(1, args.parallel)) as ex:
        futs = []
        for f in FEEDS:
            futs.append(ex.submit(
                collect_feed_last_year,
                f["feed_url"], f["source"],
                args.days, args.max_pages, args.max_results, bool(args.fetch_body)
            ))
        for fut in as_completed(futs):
            rows = fut.result()
            print(f"  └ 수집 {len(rows)}건")
            all_rows.extend(rows)

    # 중복 제거(링크 기준)
    dedup: Dict[str, Dict] = {}
    for r in all_rows:
        dedup[r["link"]] = r
    rows = list(dedup.values())

    # 날짜로 정렬(최신 → 과거)
    rows.sort(key=lambda x: x.get("published",""), reverse=True)

    # 저장
    out_path = args.out
    save_jsonl(out_path, rows)
    print(f"[✓] JSONL 저장: {out_path} ({len(rows)}건)")

    if args.out_json:
        save_json(args.out_json, rows)
        print(f"[✓] JSON 저장: {args.out_json}")

    if args.out_csv:
        save_csv(args.out_csv, rows)
        print(f"[✓] CSV 저장: {args.out_csv}")

    print("[done]")

if __name__ == "__main__":
    main()

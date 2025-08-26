# app.1.py — 수집(크롤링/요약/키워드) + 시각화 + 즐겨찾기 + 잇슈픽
# 실행 예: streamlit run "C:\Users\User\Desktop\app (2)\app\app.1.py"
#

## (최초 1회) 스크립트 실행 정책 허용
#Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

# 실행
#powershell -ExecutionPolicy Bypass -File "C:\Users\권민서\OneDrive\바탕 화면\app\update_data.ps1"

# ──────────────────────────────────────────────────────────────────────────────
# .env 예시(앱 파일과 같은 폴더에 .env 생성)
# MAX_RESULTS=10
# MAX_TOTAL_PER_SOURCE=200          # 소스당 총 최대 처리 기사 수(백필 포함)
# RSS_BACKFILL_PAGES=3              # WordPress 계열 피드: ?paged=2..N 으로 과거 수집
# ENABLE_SUMMARY=0
# ENABLE_HTTP_CACHE=1
# HTTP_CACHE_EXPIRE=3600
# PARALLEL_MAX_WORKERS=8
# SKIP_UPDATE_IF_EXISTS=1
# UI_LOAD_LIMIT=2000
# CONNECT_TIMEOUT=6
# READ_TIMEOUT=10
# OPENAI_TIMEOUT=20
# NLP_BACKEND=kiwi
# PER_ARTICLE_SLEEP=0
# OPENAI_API_KEY=sk-...          # ENABLE_SUMMARY=1일 때만 필요
# ENABLE_GITHUB=0
# GITHUB_TOKEN=ghp_...
# GITHUB_REPO=사용자/리포
# GITHUB_PATH=news_data.json
# STRICT_TECH_KEYWORDS=1         # 공학·기술 키워드만 허용
# SKIP_NON_TECH=0                # 비기술 기사 스킵
# HIDE_NON_TECH_AT_UI=0          # UI에서 비기술 기사 숨김
# DB_PATH="C:/Users/권민서/OneDrive/바탕 화면/app/news.db"
# ──────────────────────────────────────────────────────────────────────────────

from __future__ import annotations
import os, sys, json, sqlite3, time
from typing import List, Dict, Tuple, Optional, Iterable, Set
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
import re
from translate_util import translate_rows_if_needed

import numpy as np
import pandas as pd
import requests
import feedparser
from bs4 import BeautifulSoup
from dotenv import load_dotenv

import streamlit as st
import streamlit.components.v1 as components

import matplotlib.pyplot as plt
from wordcloud import WordCloud, STOPWORDS
from pyvis.network import Network

from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

st.set_page_config(page_title="뉴스있슈~(News IT's Issue)", layout="wide")

# ============================================================
# 0) 환경설정/토글 로드
# ============================================================
env_path = Path(__file__).resolve().with_name(".env")
load_dotenv(dotenv_path=env_path)

# ===== 안전 파서 유틸 (주석/따옴표/공백 허용) =====
import re

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

# ===== 여기부터 교체 =====
MAX_RESULTS            = getenv_int("MAX_RESULTS", 10)
MAX_TOTAL_PER_SOURCE   = getenv_int("MAX_TOTAL_PER_SOURCE", 200)
RSS_BACKFILL_PAGES     = getenv_int("RSS_BACKFILL_PAGES", 3)

CONNECT_TIMEOUT        = getenv_float("CONNECT_TIMEOUT", 6.0)
READ_TIMEOUT           = getenv_float("READ_TIMEOUT", 10.0)
OPENAI_TIMEOUT         = getenv_float("OPENAI_TIMEOUT", 20.0)

ENABLE_SUMMARY         = getenv_bool("ENABLE_SUMMARY", False)
ENABLE_GITHUB          = getenv_bool("ENABLE_GITHUB", False)
ENABLE_HTTP_CACHE      = getenv_bool("ENABLE_HTTP_CACHE", True)
HTTP_CACHE_EXPIRE      = getenv_int("HTTP_CACHE_EXPIRE", 3600)
PARALLEL_MAX_WORKERS   = getenv_int("PARALLEL_MAX_WORKERS", 8)
SKIP_UPDATE_IF_EXISTS  = getenv_bool("SKIP_UPDATE_IF_EXISTS", True)

UI_LOAD_LIMIT          = getenv_int("UI_LOAD_LIMIT", 2000)

NLP_BACKEND            = getenv_str("NLP_BACKEND", "kiwi").lower()
PER_ARTICLE_SLEEP      = getenv_float("PER_ARTICLE_SLEEP", 0.0)

STRICT_TECH_KEYWORDS   = getenv_bool("STRICT_TECH_KEYWORDS", True)
SKIP_NON_TECH          = getenv_bool("SKIP_NON_TECH", False)
HIDE_NON_TECH_AT_UI    = getenv_bool("HIDE_NON_TECH_AT_UI", False)

OPENAI_API_KEY         = getenv_str("OPENAI_API_KEY", "ssu1")
GITHUB_TOKEN           = getenv_str("GITHUB_TOKEN",   "ssu2")
GITHUB_REPO            = getenv_str("GITHUB_REPO",    "ssu3")
GITHUB_PATH            = getenv_str("GITHUB_PATH",    "news_data.json")
DB_PATH                = getenv_str("DB_PATH", "news.db")
# ===== 교체 끝 =====


def _require(name, value, placeholder):
    if value is None or value.strip() == "" or value.strip() == placeholder:
        raise RuntimeError(f"{name}가 비어있습니다. .env에서 {name} 값을 설정하세요.")

_openai_client = None
_github_client = None
def _get_openai():
    global _openai_client
    if _openai_client is None and ENABLE_SUMMARY:
        from openai import OpenAI
        _require("OPENAI_API_KEY", OPENAI_API_KEY, "ssu1")
        _openai_client = OpenAI(api_key=OPENAI_API_KEY, timeout=OPENAI_TIMEOUT)
    return _openai_client
def _get_github():
    global _github_client
    if _github_client is None and ENABLE_GITHUB:
        from github import Github
        _require("GITHUB_TOKEN", GITHUB_TOKEN, "ssu2")
        _require("GITHUB_REPO",  GITHUB_REPO,  "ssu3")
        _require("GITHUB_PATH",  GITHUB_PATH,  "ssu4")
        _github_client = Github(GITHUB_TOKEN)
    return _github_client

# ============================================================
# 1) DB 준비 (+ 즐겨찾기)
# ============================================================
# ============================================================
# 1) DB 준비 (+ 즐겨찾기)
# ============================================================
# 기존: DB_PATH = os.getenv("DB_PATH", "news.db")가 위쪽에 이미 정의되어 있음
# 경로 정리 + 폴더 자동 생성 (따옴표/혼합 슬래시 이슈 예방)
DB_PATH = os.path.expanduser(DB_PATH).strip().strip('"').strip("'")
DB_PATH = DB_PATH.replace("\\", "/")
db_dir = os.path.dirname(DB_PATH) or "."
os.makedirs(db_dir, exist_ok=True)

try:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
except sqlite3.OperationalError as e:
    st.error(f"DB 열기 실패\n경로: {DB_PATH}\n에러: {e}")
    st.stop()

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

# ============================================================
# 2) RSS 소스 (확장)
# ============================================================
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
try:
    if os.getenv("ENABLE_HTTP_CACHE", "1") == "1":
        from requests_cache import CachedSession
        SESSION = CachedSession('http_cache', expire_after=int(os.getenv("HTTP_CACHE_EXPIRE","3600")))
    else:
        SESSION = requests.Session()
except Exception:
    SESSION = requests.Session()
ADAPTER = requests.adapters.HTTPAdapter(pool_connections=10, pool_maxsize=20, max_retries=1)
SESSION.mount("http://", ADAPTER)
SESSION.mount("https://", ADAPTER)

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

# ============================================================
# 3) 키워드 필터/요약/형태소 (요약 정화 + 실패 휴리스틱)
# ============================================================
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
TECH_ALLOW_PATTERNS = [
    r"^llm$", r"^rlhf$", r"^rag$", r"^ssl$", r"^tls$", r"^ssh$", r"^api$", r"^sdk$",
    r"^[cg]pu$", r"^cpu$", r"^npu$", r"^tpu$", r"^fpga$", r"^asic$",
    r"^(5g|6g|4g|lte|nr)$",
    r"^dr?am$", r"^nand$", r"^hbm$",
    r"^(ai|ml|dl|nlp|cv)$",
    r"^ar|^vr|^xr$",
    r"^[a-z]+net$",
    r".*net$",
    r".*transformer.*",
    r".*diffusion.*",
    r".*foundation model.*",
]
TECH_ALLOW_REGEX = [re.compile(p, re.IGNORECASE) for p in TECH_ALLOW_PATTERNS]

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
    s = w.strip(); sl = s.lower()
    if sl in TECH_ALLOW_TERMS: return True
    for rx in TECH_ALLOW_REGEX:
        if rx.search(s): return True
    if re.fullmatch(r"[a-z]{2,}\d{1,2}", sl): return True
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

# ---- 요약 실패 시 제목 기반 휴리스틱 요약 ----
def generate_heuristic_summary(title: str, source: str, published: str,
                               categories_map: Optional[Dict[str, Dict[str, List[str]]]] = None) -> str:
    title_str = (title or "").strip()
    pm, ps = "IT/공학", "핵심 이슈"
    if categories_map:
        # 제목에 포함된 키워드로 대강 분류
        for main, subcats in categories_map.items():
            for sub, kws in subcats.items():
                for kw in kws:
                    if kw and str(kw) in title_str:
                        pm, ps = main, sub
                        break
    # 간단한 설명 2~3문장 + 해시태그
    base = f"{source} 보도. '{title_str}' 주제의 {pm} - {ps} 관련 이슈입니다. " \
           f"해당 분야는 최근 기술·제품·투자 동향이 활발하며 산업 전반의 경쟁이 이어지고 있습니다. " \
           f"기업/연구기관의 발표와 표준화, 생태계 확장이 동시에 진행되는 흐름을 참고하세요."
    # 해시태그(제목에서 뽑기)
    tags = []
    for token in re.split(r"[^\w가-힣A-Za-z\+\-]+", title_str):
        if not token: continue
        if is_meaningless_token(token): continue
        if is_tech_term(token):
            tags.append(token)
    tags = list(dict.fromkeys(tags))[:4]
    if tags:
        base += "  #" + " #".join(tags)
    return sanitize_summary(base)

def summarize_kor(title: str, source: str, published: str, text: str) -> str:
    def _fallback():
        base = _clean_sentences(text or "", 1200)
        if not base or len(base) < 20:
            return sanitize_summary(f"{title}".strip())
        sents = re.split(r"(?<=[.?!。])\s+", base)
        head = " ".join(sents[:3]) if sents else base
        return sanitize_summary(head)

    if not ENABLE_SUMMARY:
        # 모델을 쓰지 않는 모드에서는 휴리스틱 보강
        out = _fallback()
        if not out or out.strip().lower() == (title or "").strip().lower() or len(out) < 60:
            try:
                cm = globals().get("CATEGORIES", None)
                return generate_heuristic_summary(title, source, published, categories_map=cm)
            except Exception:
                return out or (title or "")
        return out

    try:
        client = _get_openai()
        snippet = _clean_sentences(text or "", 6000)
        prompt = f"""
다음 기사를 사실 위주로 4~6문장 한국어 요약하세요. 과장/의견 없이 핵심만.
- 제목: {title}
- 매체: {source}
- 게시일: {published}
- 본문(발췌): {snippet}
요구사항:
1) 핵심 기술/제품/조치/수치/일정
2) 산업적 함의 1줄
3) 마지막에 #키워드 3~5개 (쉼표 구분, 기술 관련)
"""
        chat = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role":"system","content":"너는 공학·IT 뉴스 한국어 에디터다. 사실만 간결히."},
                {"role":"user","content":prompt}
            ],
            temperature=0.3, max_tokens=420, timeout=OPENAI_TIMEOUT,
        )
        out = (chat.choices[0].message.content or "").strip()
        out = sanitize_summary(out)
        if not out or out.strip().lower() == (title or "").strip().lower() or len(out) < 60:
            cm = globals().get("CATEGORIES", None)
            return generate_heuristic_summary(title, source, published, categories_map=cm)
        return out
    except Exception:
        # OpenAI 실패 시 휴리스틱
        cm = globals().get("CATEGORIES", None)
        return generate_heuristic_summary(title, source, published, categories_map=cm)

# 형태소
pos_tags = None
token_filter = None
def _init_nlp():
    global pos_tags, token_filter
    if pos_tags is not None: return
    try:
        if NLP_BACKEND in ("auto", "okt"):
            from konlpy.tag import Okt
            _okt = Okt()
            def _pos(txt): return _okt.pos(txt or "", norm=True, stem=True)
            def _filter(w,p): return p in {"Noun","Verb","Adjective","Alpha"}
            pos_tags, token_filter = _pos, _filter
            return
        raise RuntimeError("Okt 미사용 강제")
    except Exception:
        if NLP_BACKEND == "okt":
            raise
        from kiwipiepy import Kiwi
        _kiwi = Kiwi()
        def _pos(txt):
            txt = txt or ""
            try: toks = _kiwi.tokenize(txt)
            except Exception:
                res = _kiwi.analyze(txt) or []
                r = res[0] if res else None
                toks = getattr(r, "tokens", None)
                if toks is None and isinstance(r, (tuple, list)) and len(r) >= 2:
                    toks = r[1]
                toks = toks or []
            pairs = []
            for t in toks:
                if hasattr(t, "form"): form, tag = t.form, str(t.tag)
                elif isinstance(t, (tuple, list)) and len(t) >= 2: form, tag = t[0], str(t[1])
                else: continue
                if   tag.startswith("NN"): mapped = "Noun"
                elif tag.startswith("VV"): mapped = "Verb"
                elif tag.startswith("VA"): mapped = "Adjective"
                elif tag == "SL":         mapped = "Alpha"
                else:                     mapped = tag
                pairs.append((form, mapped))
            return pairs
        def _filter(w,p): return p in {"Noun","Verb","Adjective","Alpha"}
        pos_tags, token_filter = _pos, _filter
_init_nlp()

def extract_keywords(text: str, top_k: int = 30):
    _init_nlp()
    if not text: return []
    toks = []
    for w, p in pos_tags(text):
        if p not in {"Noun","Verb","Adjective","Alpha"}: continue
        wl = str(w).strip()
        if not wl: continue
        if wl.lower() in STOP_WORDS: continue
        if is_meaningless_token(wl): continue
        toks.append(wl)
    if STRICT_TECH_KEYWORDS:
        toks = [t for t in toks if is_tech_term(t)]
    counts = Counter(toks)
    if not counts:
        for w,p in pos_tags(text):
            if p != "Noun": continue
            w2 = str(w).strip()
            if len(w2) >= 2 and not is_meaningless_token(w2):
                counts[w2] += 1
    return [w for w,_ in counts.most_common(top_k)]

def is_tech_doc(title: str, body: str, keywords: Iterable[str]) -> bool:
    text = f"{title or ''} {body or ''} {' '.join(keywords or [])}"
    for k in (keywords or []):
        if is_tech_term(k): return True
    for term in TECH_ALLOW_TERMS:
        if term in text.lower(): return True
    for rx in TECH_ALLOW_REGEX:
        if rx.search(text): return True
    if re.search(r"(연예|스타|예능|헬스|건강|라이프|맛집|여행|뷰티|운세|게임쇼|e스포츠)", text):
        return False
    return False

# ============================================================
# 4) 업서트/수집 (백필 포함)
# ============================================================
def link_exists(link: str) -> bool:
    try:
        cursor.execute("SELECT 1 FROM articles WHERE link=? LIMIT 1", (link,))
        return cursor.fetchone() is not None
    except Exception:
        return False

def upsert_article(title, link, published, source, raw_text, summary, keywords):
    link = canonicalize_link(link)
    summary = sanitize_summary(summary)
    try:
        cursor.execute("""
            INSERT INTO articles (title, link, published, source, raw_text, summary, keywords, category)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (title, link, published, source, raw_text, summary,
              json.dumps(keywords, ensure_ascii=False), None))
        conn.commit()
        return "insert"
    except sqlite3.IntegrityError:
        cursor.execute("""
            UPDATE articles
               SET title=?, published=?, source=?,
                   raw_text=?, summary=?, keywords=?
             WHERE link=?
        """, (title, published, source, raw_text, summary,
              json.dumps(keywords, ensure_ascii=False), link))
        conn.commit()
        return "update"

def _process_entry(entry, idx, total, source, log):
    title = getattr(entry, "title", "").strip()
    link  = canonicalize_link(getattr(entry, "link", "").strip())
    if not (title and link):
        return "skip", idx

    if SKIP_UPDATE_IF_EXISTS and link_exists(link):
        return "skip", idx

    published = getattr(entry, "published", "") or getattr(entry, "updated", "") or datetime.utcnow().strftime("%Y-%m-%d")
    raw_text  = extract_main_text(link) or getattr(entry, "summary", "") or ""
    summary   = summarize_kor(title, source, published, raw_text or title)
    keywords  = extract_keywords(raw_text or summary, top_k=30)

    if SKIP_NON_TECH and not is_tech_doc(title, raw_text, keywords):
        return "skip_nontech", idx

    res = upsert_article(title, link, published, source, raw_text, summary, keywords)

    if PER_ARTICLE_SLEEP > 0:
        time.sleep(PER_ARTICLE_SLEEP)
    return res, idx

def fetch_and_store_news(feed_url: str, source: str, max_total=None, log=None):
    if max_total is None:
        max_total = MAX_TOTAL_PER_SOURCE
    if log is None:
        log = st.write

    if not feed_url:
        log(f"- {source}: feed_url 없음 → 건너뜀")
        return

    urls = expand_paged_feed_urls(feed_url, RSS_BACKFILL_PAGES)
    log(f"**▷ {source}** 피드 읽는 중… (확장 {len(urls)}개)")

    entries_all = []
    for i, u in enumerate(urls, 1):
        feed = parse_feed(u)
        if feed is None:
            log(f"  - RSS 파싱 실패/비호환: {u} → 건너뜀")
            continue
        entries = feed.entries or []
        if MAX_RESULTS:
            entries = entries[:MAX_RESULTS]
        entries_all.extend(entries)
        log(f"  - {i}/{len(urls)}: 항목 {len(entries)}건")

        if len(entries_all) >= max_total:
            break

    if not entries_all:
        log(f"◼ {source}: 수집된 항목 없음")
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

    log(f"- 총 처리 대상: {len(uniq_entries)}건 (중복 제거 후)")

    inserted, updated, skipped, skipped_nontech = 0, 0, 0, 0

    if not ENABLE_SUMMARY and len(uniq_entries) > 0:
        workers = max(1, PARALLEL_MAX_WORKERS)
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = [ex.submit(_process_entry, e, i, len(uniq_entries), source, log)
                    for i, e in enumerate(uniq_entries, 1)]
            for fut in as_completed(futs):
                res, idx = fut.result()
                if   res == "insert": inserted += 1; log(f"[{idx}/{len(uniq_entries)}] ✅ 신규 저장")
                elif res == "update": updated  += 1; log(f"[{idx}/{len(uniq_entries)}] 🔄 업데이트")
                elif res == "skip_nontech":    skipped_nontech += 1
                else:                           skipped += 1
    else:
        for idx, entry in enumerate(uniq_entries, 1):
            res, _ = _process_entry(entry, idx, len(uniq_entries), source, log)
            if   res == "insert": inserted += 1; log(f"[{idx}/{len(uniq_entries)}] ✅ 신규 저장")
            elif res == "update": updated  += 1; log(f"[{idx}/{len(uniq_entries)}] 🔄 업데이트")
            elif res == "skip_nontech":    skipped_nontech += 1
            else:                           skipped += 1

    log(f"◼ {source}: 신규 {inserted} · 업데이트 {updated} · 스킵 {skipped} · 비기술스킵 {skipped_nontech}")

def ingest_all(log=None):
    if log is None:
        log = st.write
    log("⏳ 뉴스 수집/요약/키워드 시작")
    for f in FEEDS:
        fetch_and_store_news(f.get("feed_url"), f.get("source","(unknown)"), log=log)
    log("✅ 모든 소스 처리 완료")

def export_json(path="news_data.json", limit=500, log=None):
    if log is None:
        log = st.write
    df = pd.read_sql("""
        SELECT title, link, published, source, summary, keywords
        FROM articles
        ORDER BY id DESC LIMIT ?
    """, conn, params=(limit,))
    df["summary"] = df["summary"].apply(sanitize_summary)
    records = df.to_dict(orient="records")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    log(f"💾 JSON 저장: {path} ({len(records)}건)")
    return path

def upload_to_github(local_path: str, repo_fullname: str, dest_path: str, log=None):
    if log is None:
        log = st.write
    if not ENABLE_GITHUB:
        log("↪︎ 깃허브 업로드 비활성화(ENABLE_GITHUB=0) — 건너뜀")
        return
    gh = _get_github()
    repo = gh.get_repo(repo_fullname)
    with open(local_path, "r", encoding="utf-8") as f:
        content = f.read()
    try:
        existing = repo.get_contents(dest_path)
        repo.update_file(dest_path, f"Update news ({datetime.now().strftime('%Y-%m-%d %H:%M')})", content, existing.sha)
        log(f"⬆️ GitHub 업데이트 완료: {repo_fullname}/{dest_path}")
    except Exception:
        repo.create_file(dest_path, f"Add news ({datetime.now().strftime('%Y-%m-%d %H:%M')})", content)
        log(f"⬆️ GitHub 신규 업로드 완료: {repo_fullname}/{dest_path}")

# ============================================================
# 5) 로딩/타임존/즐겨찾기
# ============================================================
@st.cache_data(show_spinner=False)
def load_df_from_db(limit: Optional[int] = UI_LOAD_LIMIT) -> pd.DataFrame:
    sql = """SELECT id, title, summary, keywords, source,
                    published AS published_at
             FROM articles
             ORDER BY id DESC"""
    if limit:
        sql += f" LIMIT {int(limit)}"
    df = pd.read_sql(sql, conn)

    def _to_list(x):
        if isinstance(x, list): return x
        if isinstance(x, str):
            try: return json.loads(x)
            except Exception: return [t.strip() for t in re.split(r"[,\s]+", x) if t.strip()]
        return []
    df["keywords"] = df["keywords"].apply(_to_list)

    df["summary"] = df["summary"].apply(sanitize_summary)

    df["published_at"] = (
        pd.to_datetime(df["published_at"], errors="coerce", utc=True)
          .dt.tz_convert("Asia/Seoul")
          .dt.tz_localize(None)
    )
    df["title"] = df["title"].astype(str)
    df["summary"] = df["summary"].astype(str)
    df["source"] = df["source"].astype(str)

    if HIDE_NON_TECH_AT_UI:
        mask = []
        for _, r in df.iterrows():
            mask.append(is_tech_doc(r["title"], r["summary"], r["keywords"]))
        df = df[pd.Series(mask, index=df.index)]

    return df

@st.cache_data(show_spinner=False, ttl=2)
def get_favorite_ids() -> Set[int]:
    try:
        fav_df = pd.read_sql("SELECT article_id FROM favorites", conn)
        return set(fav_df["article_id"].astype(int).tolist())
    except Exception:
        return set()

def add_favorite(article_id: int):
    try:
        cursor.execute("INSERT OR IGNORE INTO favorites(article_id) VALUES (?)", (int(article_id),))
        conn.commit()
    except Exception:
        pass

def remove_favorite(article_id: int):
    try:
        cursor.execute("DELETE FROM favorites WHERE article_id=?", (int(article_id),))
        conn.commit()
    except Exception:
        pass

@st.cache_data(show_spinner=False, ttl=2)
def get_favorites_df() -> pd.DataFrame:
    sql = """
    SELECT a.id, a.title, a.summary, a.keywords, a.source, a.published AS published_at
      FROM favorites f
      JOIN articles a ON a.id = f.article_id
     ORDER BY a.id DESC
    """
    df = pd.read_sql(sql, conn)
    def _to_list(x):
        if isinstance(x, list): return x
        if isinstance(x, str):
            try: return json.loads(x)
            except Exception: return [t.strip() for t in re.split(r"[,\s]+", x) if t.strip()]
        return []
    df["keywords"] = df["keywords"].apply(_to_list)
    df["summary"]  = df["summary"].apply(sanitize_summary)
    df["published_at"] = (
        pd.to_datetime(df["published_at"], errors="coerce", utc=True)
          .dt.tz_convert("Asia/Seoul")
          .dt.tz_localize(None)
    )
    return df

# ============================================================
# 6) 시각화/분류 (UI 유지 + 하단 페이지 버튼 + 버튼 색상)
# ============================================================
def _rerun():
    try: st.rerun()
    except AttributeError: st.experimental_rerun()

def _inject_global_css():
    st.markdown("""
    <style>
    ._metric-card{border:1px solid rgba(49,51,63,.16);border-radius:14px;padding:14px 16px;background:var(--bg);}
    ._card{border:1px solid rgba(49,51,63,.12);border-radius:14px;padding:14px 16px;margin-bottom:12px;background:var(--bg);}
    :root{--bg:rgba(255,255,255,.65);--chip-bg:rgba(0,0,0,.06);--chip-fg:#111;--muted:rgba(0,0,0,.55);--link:#4e7df2;}
    @media (prefers-color-scheme: dark){
      :root{--bg:rgba(255,255,255,.04);--chip-bg:rgba(255,255,255,.08);--chip-fg:#fff;--muted:rgba(255,255,255,.7);--link:#a9c1ff;}
    }
    ._meta{color:var(--muted);font-size:.9rem;}
    ._title{font-weight:700;font-size:1.05rem;line-height:1.35;}
    mark{padding:0 .2em;border-radius:4px;}
    /* Download button color tuning */
    div[data-testid="stDownloadButton"] button[kind="primary"],
    div[data-testid="stDownloadButton"] button[data-testid="baseButton-primary"]{
      background-color:#2563eb !important;border-color:#2563eb !important;color:#fff !important;
    }
    div[data-testid="stDownloadButton"] button[kind="secondary"],
    div[data-testid="stDownloadButton"] button[data-testid="baseButton-secondary"]{
      background-color:#64748b !important;border-color:#64748b !important;color:#fff !important;
    }
    </style>""", unsafe_allow_html=True)

def _highlight(text: str, q: Optional[str]) -> str:
    if not q or not isinstance(text, str): return text if isinstance(text, str) else ""
    pat = re.compile(re.escape(q), re.IGNORECASE)
    return pat.sub(lambda m: f"<mark>{m.group(0)}</mark>", text)

CATEGORIES: Dict[str, Dict[str, List[str]]] = {
    "첨단 제조·기술 산업": {
        "반도체 분야": ["반도체", "메모리", "시스템 반도체", "파운드리", "소자", "웨이퍼", "노광", "EUV", "장비", "소재"],
        "자동차 분야": ["자동차", "내연기관", "전기차", "자율주행", "모빌리티", "현대차", "테슬라", "배터리카"],
        "이차전지 분야": ["이차전지", "배터리", "ESS", "양극재", "음극재", "전해질", "분리막"],
        "디스플레이 분야": ["디스플레이", "OLED", "QD", "마이크로 LED", "LCD"],
        "로봇·스마트팩토리 분야": ["로봇", "스마트팩토리", "산업자동화", "협동로봇"]
    },
    "에너지·환경 산업": {
        "에너지 분야": ["석유", "가스", "원자력", "태양광", "풍력", "수소", "신재생에너지"],
        "환경·탄소중립 분야": ["탄소중립", "폐기물", "친환경", "수처리", "CCUS", "재활용"]
    },
    "디지털·ICT 산업": {
        "AI 분야": ["AI", "인공지능", "머신러닝", "딥러닝", "생성형", "챗GPT", "로보틱스"],
        "ICT·통신 분야": ["5G", "6G", "통신", "네트워크", "인프라", "클라우드"],
        "소프트웨어·플랫폼": ["소프트웨어", "메타버스", "SaaS", "보안", "핀테크", "플랫폼"]
    },
    "바이오·헬스케어 산업": {
        "바이오·제약 분야": ["바이오", "제약", "신약", "바이오시밀러", "세포치료제", "유전자치료제"],
        "의료기기·헬스케어": ["의료기기", "헬스케어", "디지털 헬스", "웨어러블", "원격진료"]
    },
    "소재·화학 산업": {
        "첨단 소재": ["탄소소재", "나노소재", "고분자", "복합소재"],
        "정밀화학·석유화학": ["정밀화학", "석유화학", "케미컬", "특수가스", "반도체용 케미컬"]
    },
    "인프라·기반 산업": {
        "철강·조선·건설": ["철강", "조선", "건설", "스마트건설", "친환경 선박"],
        "물류·유통": ["물류", "유통", "전자상거래", "스마트 물류", "공급망"],
        "농업·식품": ["농업", "스마트팜", "대체식품", "식품"]
    }
}

def _norm(s: str) -> str: return (s or "").lower()

def _kw_in_text(kw: str, text: str, match_mode: str = "substring") -> bool:
    if not kw: return False
    kw_l = kw.lower(); t = _norm(text)
    if match_mode == "word" and re.fullmatch(r"[0-9a-zA-Z\-\+_/\.]+", kw):
        return re.search(rf"(?<!\w){re.escape(kw_l)}(?!\w)", t) is not None
    return kw_l in t

def _classify_multi(title: str, summary: str, categories_map: Dict[str, Dict[str, List[str]]],
                    keywords_cell: Optional[Iterable[str]] = None, match_mode: str = "substring"
) -> Tuple[List[str], List[str], List[Tuple[str, str, str]]]:
    kw_text = ""
    if isinstance(keywords_cell, (list, tuple, set)): kw_text = " ".join([str(k) for k in keywords_cell if k])
    elif isinstance(keywords_cell, str): kw_text = keywords_cell
    text = f"{title or ''} {summary or ''} {kw_text or ''}"
    mains, subs, matched = set(), set(), []
    for main_cat, subcats in categories_map.items():
        for sub_cat, keywords in subcats.items():
            for kw in keywords:
                if _kw_in_text(str(kw), text, match_mode=match_mode):
                    mains.add(main_cat); subs.add(sub_cat); matched.append((main_cat, sub_cat, kw)); break
    return sorted(mains) or ["분류불가"], sorted(subs) or ["기타"], matched

def _primary_labels(matched: List[Tuple[str, str, str]]) -> Tuple[str, str]:
    if not matched: return ("분류불가", "기타")
    main_counts = Counter([m for m, _, _ in matched]); main = main_counts.most_common(1)[0][0]
    sub_counts  = Counter([s for m, s, _ in matched if m == main]); sub  = sub_counts.most_common(1)[0][0]
    return (main, sub)

@st.cache_data(show_spinner=False)
def ensure_hierarchical_categories(df: pd.DataFrame, categories_map: Dict[str, Dict[str, List[str]]],
                                   match_mode: str = "substring") -> pd.DataFrame:
    df = df.copy()
    mains_all, subs_all, prim_main, prim_sub, matched_all = [], [], [], [], []
    for _, r in df.iterrows():
        mains, subs, matched = _classify_multi(str(r.get("title","")), str(r.get("summary","")),
                                               categories_map, r.get("keywords", None), match_mode=match_mode)
        pm, ps = _primary_labels(matched)
        mains_all.append(mains); subs_all.append(subs); prim_main.append(pm); prim_sub.append(ps); matched_all.append(matched)
    df["main_categories"] = mains_all
    df["sub_categories"] = subs_all
    df["primary_main"]   = prim_main
    df["primary_sub"]    = prim_sub
    df["matched_pairs"]  = matched_all
    return df

def _list_contains(lst: Iterable[str], targets: List[str], mode: str = "OR") -> bool:
    s = set([str(x) for x in (lst or [])]); t = set([str(x) for x in (targets or [])])
    if not t: return True
    return (len(s & t) > 0) if mode == "OR" else t.issubset(s)

@st.cache_data(show_spinner=False)
def filter_df(df: pd.DataFrame, start: Optional[datetime], end: Optional[datetime],
              sources: Optional[List[str]], q: Optional[str],
              main_cats: Optional[List[str]], sub_cats: Optional[List[str]],
              match_mode: str = "OR") -> pd.DataFrame:
    out = df.copy()
    try:
        out["published_at"] = (
            pd.to_datetime(out["published_at"], errors="coerce", utc=True)
              .dt.tz_convert("Asia/Seoul")
              .dt.tz_localize(None)
        )
    except Exception:
        pass

    if start is not None: out = out[out["published_at"] >= start]
    if end   is not None: out = out[out["published_at"] <= end]
    if sources: out = out[out["source"].isin(sources)]
    if main_cats: out = out[out["main_categories"].apply(lambda x: _list_contains(x, main_cats, mode=match_mode))]
    if sub_cats:  out = out[out["sub_categories"].apply(lambda x: _list_contains(x, sub_cats,  mode=match_mode))]
    if q:
        q_low = q.lower()
        out = out[out["title"].str.lower().str.contains(q_low, na=False) | out["summary"].str.lower().str.contains(q_low, na=False)]
    return out.sort_values("published_at", ascending=False)

@st.cache_data(show_spinner=False)
def aggregate_keywords(df: pd.DataFrame, topk: int = 50) -> List[Tuple[str, int]]:
    bag = Counter()
    for row in df["keywords"].dropna():
        seq=[]
        if isinstance(row, (list, tuple, set)): seq=list(row)
        elif isinstance(row, str): seq=[p.strip() for p in re.split(r"[,\s]+", row) if p.strip()]
        for k in seq:
            if is_meaningless_token(str(k)): continue
            if STRICT_TECH_KEYWORDS and not is_tech_term(str(k)): continue
            bag.update([str(k)])
    return bag.most_common(topk)

@st.cache_data(show_spinner=False)
def aggregate_time(df: pd.DataFrame, freq: str = "D") -> pd.DataFrame:
    if df.empty: return pd.DataFrame(columns=["period","count"])
    g = (df.set_index("published_at")
           .groupby(pd.Grouper(freq=freq))
           .size()
           .reset_index(name="count")
           .rename(columns={"published_at":"period"}))
    return g

def extract_insights(df: pd.DataFrame) -> Dict[str, str]:
    ins: Dict[str, str] = {}
    if df.empty: ins["note"]="선택한 조건에서 데이터가 없습니다."; return ins
    top_src = df["source"].value_counts().head(3)
    ins["top_sources"] = ", ".join([f"{k}({v})" for k,v in top_src.items()]) if not top_src.empty else "-"
    now = df["published_at"].max() if not df.empty else datetime.now()
    recent = df[df["published_at"] >= (now - pd.Timedelta(days=7))]
    prev   = df[(df["published_at"] < (now - pd.Timedelta(days=7))) & (df["published_at"] >= (now - pd.Timedelta(days=14)))]
    def _bag(x):
        c=Counter()
        for ks in x["keywords"].dropna():
            if isinstance(ks,(list,tuple,set)): seq=list(ks)
            elif isinstance(ks,str): seq=[p for p in re.split(r"[,\s]+", ks) if p]
            else: seq=[]
            for k in seq:
                if is_meaningless_token(str(k)): continue
                if STRICT_TECH_KEYWORDS and not is_tech_term(str(k)): continue
                c.update([str(k)])
        return c
    r_bag, p_bag = _bag(recent), _bag(prev)
    lift=[]
    for k,v in r_bag.items():
        base=p_bag.get(k,0)
        if base==0 and v>=2: lift.append((k, float("inf")))
        elif base>0: lift.append((k, v/base))
    lift_sorted = sorted(lift, key=lambda t: (np.isinf(t[1]), t[1]), reverse=True)[:5]
    ins["rising_keywords"] = ", ".join([f"{k}↑" for k,_ in lift_sorted]) if lift_sorted else "(없음)"
    return ins

_ALLOWED_TOKEN_RE = re.compile(r"^[\u1100-\u11FF\u3130-\u318F\uAC00-\uD7A3A-Za-z0-9\s\-\+\.\#_/·∙:()&%,]+$")
def _guess_korean_font_path(user_font_path: Optional[str] = None) -> Optional[str]:
    if user_font_path and os.path.exists(user_font_path): return user_font_path
    candidates = [
        r"C:\Windows\Fonts\malgun.ttf", r"C:\Windows\Fonts\malgunbd.ttf",
        r"C:\Windows\Fonts\NanumGothic.ttf", r"C:\Windows\Fonts\NanumBarunGothic.ttf",
        r"C:\Windows\Fonts\NotoSansKR-Regular.otf", r"C:\Windows\Fonts\NotoSansCJKkr-Regular.otf",
        "/System/Library/Fonts/AppleSDGothicNeo.ttc", "/Library/Fonts/AppleGothic.ttf",
        "/Library/Fonts/NanumGothic.otf", "/Library/Fonts/NanumGothic.ttf",
        "/Library/Fonts/NotoSansKR-Regular.otf",
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansKR-Regular.otf",
        "/usr/share/fonts/truetype/noto/NotoSansKR-Regular.ttf",
    ]
    for p in candidates:
        if os.path.exists(p): return p
    return None

def _filter_wc_tokens(keywords_freq: List[Tuple[str,int]], strict_filter: bool=True)->List[Tuple[str,int]]:
    if not keywords_freq: return []
    cleaned=[]
    for k,v in keywords_freq:
        ks=str(k).strip()
        if not ks: continue
        if _ALLOWED_TOKEN_RE.match(ks) is None: continue
        if is_meaningless_token(ks): continue
        if STRICT_TECH_KEYWORDS and not is_tech_term(ks): continue
        cleaned.append((ks,int(v)))
    return cleaned

def render_wordcloud_wc(keywords_freq: List[Tuple[str,int]], font_path: Optional[str]=None,
                        auto_korean_font: bool=True, filter_unrenderables: bool=True):
    if not keywords_freq:
        st.info("워드클라우드를 생성할 키워드가 없습니다."); return
    filtered = _filter_wc_tokens(keywords_freq, strict_filter=filter_unrenderables)
    if not filtered:
        st.warning("표시할 기술 키워드가 없습니다. 필터를 완화해 보세요."); return
    fp = _guess_korean_font_path(font_path) if auto_korean_font else font_path
    if auto_korean_font:
        st.caption(f"워드클라우드 폰트: `{fp or '기본(한글 미지원일 수 있음)'}`")
    wc = WordCloud(width=1000, height=500, background_color="white",
                   stopwords=STOPWORDS, collocations=False, font_path=fp)
    wc.generate_from_frequencies({k:int(v) for k,v in filtered})
    fig = plt.figure(figsize=(10,5)); plt.imshow(wc, interpolation="bilinear"); plt.axis("off"); st.pyplot(fig, use_container_width=True)

@st.cache_data(show_spinner=False)
def build_cooccurrence(df: pd.DataFrame, min_edge_weight: int = 2) -> Dict[str, Dict[str, int]]:
    edges: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for ks in df["keywords"].dropna():
        if isinstance(ks,(list,tuple,set)): seq=ks
        elif isinstance(ks,str): seq=[p for p in re.split(r"[,\s]+", ks) if p]
        else: seq=[]
        seq = [s for s in seq if not is_meaningless_token(str(s)) and (not STRICT_TECH_KEYWORDS or is_tech_term(str(s)))]
        uniq = sorted(set([k for k in seq if isinstance(k,str) and k]))
        for i in range(len(uniq)):
            for j in range(i+1,len(uniq)):
                a,b = uniq[i], uniq[j]; edges[a][b]+=1; edges[b][a]+=1
    filtered: Dict[str, Dict[str,int]] = defaultdict(dict)
    for a,nbrs in edges.items():
        for b,w in nbrs.items():
            if w>=min_edge_weight: filtered[a][b]=w
    return filtered

def render_keyword_network(co_graph: Dict[str, Dict[str,int]], height: str="650px"):
    if not co_graph: st.info("연결 네트워크를 그릴 데이터가 부족합니다."); return
    net = Network(height=height, width="100%", notebook=False, directed=False)
    try: net.barnes_hut(gravity=-10000, central_gravity=0.3, spring_length=150, spring_strength=0.02)
    except Exception: pass
    node_strength = {k: sum(nbrs.values()) for k,nbrs in co_graph.items()}
    max_s = max(node_strength.values()) if node_strength else 1
    for n,s in node_strength.items():
        size = 10 + (30*(s/max_s)); net.add_node(n, label=n, size=size)
    for a,nbrs in co_graph.items():
        for b,w in nbrs.items():
            if a<b: net.add_edge(a,b,value=w, title=f"공동출현: {w}")
    tmp_html = "_keyword_network.html"
    try: net.save_graph(tmp_html)
    except Exception:
        try: net.write_html(tmp_html)
        except Exception:
            try:
                html = net.generate_html()
                components.html(html, height=int(height.replace("px","")), scrolling=True); return
            except Exception as e:
                st.error(f"네트워크 렌더 중 오류: {e}"); return
    try:
        with open(tmp_html,"r",encoding="utf-8") as f: html=f.read()
        components.html(html, height=int(height.replace("px","")), scrolling=True)
    except Exception as e:
        st.error(f"네트워크 HTML 임베드 오류: {e}")

def _clamp_date_range(start_default, end_default, min_dt, max_dt):
    sd = pd.Timestamp(start_default).normalize(); ed = pd.Timestamp(end_default).normalize()
    mind = pd.Timestamp(min_dt).normalize(); maxd = pd.Timestamp(max_dt).normalize()
    sd = max(sd,mind); ed = min(ed,maxd)
    if sd>ed: sd=ed
    return sd.date(), ed.date()

def _all_subs_from_map(categories_map: Dict[str, Dict[str, List[str]]]) -> List[str]:
    return sorted({sub for subcats in categories_map.values() for sub in subcats.keys()})

def _subs_under_mains(categories_map: Dict[str, Dict[str, List[str]]], selected_mains: List[str]) -> List[str]:
    if not selected_mains: return _all_subs_from_map(categories_map)
    subs=set()
    for m in selected_mains: subs |= set(categories_map.get(m,{}).keys())
    return sorted(subs)

def _render_pagination_controls(current: int, total_pages: int, state_key: str):
    cols = st.columns([1,1,4,1,1])
    with cols[0]:
        if st.button("⏮ 첫 페이지", key=f"{state_key}_first") and current>1:
            st.session_state[state_key] = 1; _rerun()
    with cols[1]:
        if st.button("◀ 이전", key=f"{state_key}_prev") and current>1:
            st.session_state[state_key] = current-1; _rerun()
    with cols[3]:
        if st.button("다음 ▶", key=f"{state_key}_next") and current<total_pages:
            st.session_state[state_key] = current+1; _rerun()
    with cols[4]:
        if st.button("마지막 ⏭", key=f"{state_key}_last") and current<total_pages:
            st.session_state[state_key] = total_pages; _rerun()

# -------------------- 잇슈픽(논문 타이틀 수집/분석) --------------------
PAPER_FEEDS = [
    {"feed_url":"http://export.arxiv.org/rss/cs",        "source":"arXiv CS"},
    {"feed_url":"http://export.arxiv.org/rss/cs.AI",     "source":"arXiv cs.AI"},
    {"feed_url":"http://export.arxiv.org/rss/cs.LG",     "source":"arXiv cs.LG"},
    {"feed_url":"http://export.arxiv.org/rss/stat.ML",   "source":"arXiv stat.ML"},
    {"feed_url":"https://www.nature.com/nel/atom.xml",   "source":"Nature Electronics"},
]

@st.cache_data(show_spinner=False, ttl=3600)
def fetch_paper_titles(max_per_feed: int = 100) -> pd.DataFrame:
    rows=[]
    for f in PAPER_FEEDS:
        feed = parse_feed(f["feed_url"])
        if not feed or not getattr(feed, "entries", None): continue
        entries = feed.entries[:max_per_feed]
        for e in entries:
            title = getattr(e, "title", "").strip()
            pub = getattr(e, "published", "") or getattr(e, "updated","")
            rows.append({"title": title, "source": f["source"], "published_at": pub})
    df = pd.DataFrame(rows)
    if df.empty: return df
    df["published_at"] = pd.to_datetime(df["published_at"], errors="coerce")
    df = df.drop_duplicates(subset=["title"]).reset_index(drop=True)
    return df

def analyze_titles_keywords(papers_df: pd.DataFrame, topk: int = 50) -> List[Tuple[str,int]]:
    if papers_df.empty: return []
    bag=Counter()
    for t in papers_df["title"]:
        toks = extract_keywords(str(t), top_k=10)  # 제목에서 기술 토큰만
        for tk in toks:
            if is_meaningless_token(tk): continue
            if STRICT_TECH_KEYWORDS and not is_tech_term(tk): continue
            bag.update([tk])
    return bag.most_common(topk)

# -------------------- 메인 대시보드 --------------------
def render_dashboard(df: pd.DataFrame, categories_map: Dict[str, Dict[str, List[str]]], font_path: Optional[str]=None):
    _inject_global_css()
    st.title("뉴스있슈(News IT's Issue) 🤖🔥")

    # ===== 사이드바: 수집/내보내기 =====
    with st.sidebar.expander("데이터 수집/내보내기", expanded=False):
        st.caption("환경값은 .env로 제어됩니다.")
        col1, col2 = st.columns(2)
        with col1:
            run_ingest = st.button("▶ 수집 실행 (RSS → DB)")
        with col2:
            do_export = st.button("💾 JSON 내보내기")

        if run_ingest:
            with st.status("수집 중...", expanded=True) as status:
                try:
                    ingest_all(log=st.write)
                    status.update(label="수집 완료", state="complete", expanded=False)
                except Exception as e:
                    status.update(label=f"오류: {e}", state="error")
            st.cache_data.clear()

        if do_export:
            try:
                p = export_json(path=GITHUB_PATH, limit=500, log=st.write)
                if ENABLE_GITHUB:
                    upload_to_github(p, GITHUB_REPO, GITHUB_PATH, log=st.write)
            except Exception as e:
                st.error(f"내보내기/업로드 오류: {e}")

    # ===== 분류 생성 =====
    match_mode_for_classifier = st.sidebar.selectbox(
        "키워드 매칭 방식(분류용)", ["substring","word"], index=0,
        help="substring: 부분일치(한글 추천) / word: 영문·숫자 단어경계"
    )
    df = ensure_hierarchical_categories(df, categories_map, match_mode=match_mode_for_classifier)
    if df.empty:
        st.warning("데이터가 없습니다. 좌측에서 수집을 실행해 보세요.")
        return

    min_dt, max_dt = df["published_at"].min(), df["published_at"].max()

    # ===== 필터 =====
    st.sidebar.header("필터")
    st.sidebar.caption("빠른 기간 선택")
    quick = st.sidebar.segmented_control("기간 프리셋", options=["전체","오늘","7일","30일","올해"], default="전체")
    if quick == "오늘":
        start_default = pd.Timestamp(datetime.now().date()); end_default = pd.Timestamp(datetime.now().date())
    elif quick == "7일":
        end_default = pd.Timestamp(datetime.now()); start_default = end_default - pd.Timedelta(days=7)
    elif quick == "30일":
        end_default = pd.Timestamp(datetime.now()); start_default = end_default - pd.Timedelta(days=30)
    elif quick == "올해":
        end_default = pd.Timestamp(datetime.now()); start_default = pd.Timestamp(datetime(datetime.now().year,1,1))
    else:
        start_default, end_default = min_dt, max_dt
    start_val, end_val = _clamp_date_range(start_default, end_default, min_dt, max_dt)
    start_date, end_date = st.sidebar.date_input("기간(직접 지정)", value=(start_val, end_val),
                                                 min_value=min_dt.date(), max_value=max_dt.date())

    all_mains = sorted(list(categories_map.keys()))
    sel_mains = st.sidebar.multiselect("대분류", options=all_mains, default=st.session_state.get("_mains", []))
    st.session_state["_mains"] = sel_mains[:]
    allowed_sub_options = _subs_under_mains(categories_map, sel_mains)
    prev_subs = st.session_state.get("_subs", [])
    default_subs = [s for s in prev_subs if s in allowed_sub_options]
    if prev_subs != default_subs:
        st.session_state["_subs"] = default_subs
    sel_subs = st.sidebar.multiselect("소분류", options=allowed_sub_options, default=st.session_state.get("_subs", []))
    st.session_state["_subs"] = sel_subs[:]
    hier_mode = st.sidebar.radio("매칭 모드", options=["OR","AND"], horizontal=True)
    sel_sources = st.sidebar.multiselect("출처", options=sorted(df["source"].dropna().unique().tolist()))
    q = st.sidebar.text_input("검색어 (제목/요약)", value=st.session_state.get("_q",""))

    fav_only = st.sidebar.toggle("⭐ 즐겨찾기만 보기", value=False)

    st.sidebar.header("보기 옵션")
    view_mode = st.sidebar.radio("목록 보기", ["카드","표"], horizontal=True)
    per_page  = st.sidebar.slider("페이지 당 항목 수", 10, 100, 20, step=10)
    sort_by   = st.sidebar.selectbox("정렬 기준", ["published_at(최신)","title(가나다)"])
    show_exploded = st.sidebar.toggle("라벨별 분해 표 보기(분석용)", value=False)

    if st.sidebar.button("필터 초기화"):
        st.session_state.clear(); _rerun()

    # ===== 필터 적용 =====
    fdf = filter_df(
        df,
        start=pd.to_datetime(start_date) if start_date else None,
        end=(pd.to_datetime(end_date) + pd.Timedelta(hours=23, minutes=59, seconds=59)) if end_date else None,
        sources=sel_sources or None, q=q or None,
        main_cats=sel_mains or None, sub_cats=sel_subs or None, match_mode=hier_mode
    )
    if fav_only:
        fav_ids = get_favorite_ids()
        fdf = fdf[fdf["id"].isin(fav_ids)]
    if sort_by.startswith("title"): fdf = fdf.sort_values("title")
    else: fdf = fdf.sort_values("published_at", ascending=False)

    # ===== KPI =====
    total_cnt, shown_cnt = len(df), len(fdf)
    uniq_main = len({m for lst in fdf["main_categories"] for m in lst}) if not fdf.empty else 0
    kpiA,kpiB,kpiC,kpiD = st.columns(4)
    with kpiA: st.markdown(f"<div class='_metric-card'><b>표시 건수</b><h3>{shown_cnt:,}</h3></div>", unsafe_allow_html=True)
    with kpiB: st.markdown(f"<div class='_metric-card'><b>전체 건수</b><h3>{total_cnt:,}</h3></div>", unsafe_allow_html=True)
    with kpiC: st.markdown(f"<div class='_metric-card'><b>대분류 수</b><h3>{uniq_main}</h3></div>", unsafe_allow_html=True)
    with kpiD:
        dspan=f"{pd.to_datetime(start_date).strftime('%Y-%m-%d')} ~ {pd.to_datetime(end_date).strftime('%Y-%m-%d')}"
        st.markdown(f"<div class='_metric-card'><b>기간</b><h3>{dspan}</h3></div>", unsafe_allow_html=True)

    # ===== 탭 =====
    T1,T2,T3,T4,T5,T6 = st.tabs(["🔥 오늘의 핫잇슈","📅 기간별 인사이트","☁️ 워드클라우드","🕸️ 키워드 네트워크","⭐ 즐겨찾기","📈 공학기술 잇슈픽"])

    # ---------- T1: 오늘의 핫잇슈 ----------
    with T1:
        st.subheader("오늘의 핫잇슈")
        if fdf.empty:
            st.info("조건에 맞는 문서가 없습니다.")
        else:
            total_pages = int(np.ceil(len(fdf)/per_page))
            page = st.number_input("페이지", min_value=1, max_value=max(1,total_pages),
                                   value=min(st.session_state.get("_page",1), max(1,total_pages)))
            st.session_state["_page"]=page
            start_idx=(page-1)*per_page; end_idx=start_idx+per_page
            page_df=fdf.iloc[start_idx:end_idx].copy()

            current_favs = get_favorite_ids()

            if view_mode=="카드":
                for _,row in page_df.iterrows():
                    title_html=_highlight(row["title"], q); summary_html=_highlight(row["summary"], q)
                    date_str=pd.to_datetime(row["published_at"]).strftime("%Y-%m-%d %H:%M")
                    extra_subs=[s for s in row["sub_categories"] if s!=row["primary_sub"]]
                    extra_badge=(" · +" + str(len(extra_subs)) + " sub") if extra_subs else ""
                    meta=f"{row.get('primary_main','-')} > {row.get('primary_sub','-')}{extra_badge} · {row['source']} · {date_str}"
                    is_fav = int(row["id"]) in current_favs

                    with st.container():
                        st.markdown("<div class='_card'>", unsafe_allow_html=True)
                        top_cols = st.columns([10, 2])
                        with top_cols[0]:
                            st.markdown(f"<div class='_title'>{title_html}</div>", unsafe_allow_html=True)
                            st.markdown(f"<div class='_meta'>{meta}</div>", unsafe_allow_html=True)
                        with top_cols[1]:
                            if not is_fav:
                                if st.button("☆ 즐겨찾기", key=f"fav_add_{row['id']}"):
                                    add_favorite(int(row["id"])); _rerun()
                            else:
                                if st.button("★ 해제", key=f"fav_del_{row['id']}"):
                                    remove_favorite(int(row["id"])); _rerun()

                        st.markdown(f"<div style='margin-top:6px'>{summary_html}</div>", unsafe_allow_html=True)

                        kws=row.get("keywords",[])
                        if isinstance(kws,(list,tuple,set)) and kws:
                            cols=st.columns(min(5,len(kws)))
                            for i,kw in enumerate(kws):
                                kw_s=str(kw)
                                if is_meaningless_token(kw_s): continue
                                if STRICT_TECH_KEYWORDS and not is_tech_term(kw_s): continue
                                with cols[i % max(1,len(cols))]:
                                    if st.button(f"#{kw_s}", key=f"card_kw_{row['id']}_{i}", help="이 키워드로 검색"):
                                        st.session_state["_q"]=kw_s; _rerun()

                        subs=row.get("sub_categories",[])
                        if subs:
                            st.write("")
                            scols=st.columns(min(5,len(subs)))
                            for i,s in enumerate(subs):
                                with scols[i % max(1,len(scols))]:
                                    if st.button(f"{s}", key=f"card_sub_{row['id']}_{i}", help="소분류 필터에 추가"):
                                        st.session_state["_subs"]=list(sorted(set((st.session_state.get("_subs") or []) + [s]))); _rerun()
                        st.markdown("</div>", unsafe_allow_html=True)
            else:
                show_cols=["published_at","primary_main","primary_sub","title","summary","source","keywords"]
                page_df["published_at"]=page_df["published_at"].dt.strftime("%Y-%m-%d %H:%M")
                st.dataframe(page_df[show_cols], use_container_width=True, height=420)
                st.caption("표 모드에서는 카드에서 즐겨찾기를 추가/해제하세요.")

            # === 구분선 + 내보내기 버튼(색상 구분) ===
            st.divider()
            exp1,exp2=st.columns(2)
            with exp1:
                export_df=fdf.copy()
                export_df["main_categories"]=export_df["main_categories"].apply(lambda x:"|".join(x))
                export_df["sub_categories"]=export_df["sub_categories"].apply(lambda x:"|".join(x))
                st.download_button("💾 CSV로 내보내기 (필터 반영)",
                                   data=export_df.to_csv(index=False).encode("utf-8-sig"),
                                   file_name="filtered_articles.csv", mime="text/csv",
                                   type="primary")
            with exp2:
                json_str=fdf.to_json(orient="records", force_ascii=False, date_format="iso")
                st.download_button("🧾 JSON으로 내보내기 (필터 반영)",
                                   data=json_str.encode("utf-8"),
                                   file_name="filtered_articles.json", mime="application/json",
                                   type="secondary")

            st.caption(f"페이지 {page}/{total_pages} · 현재 {len(page_df)}건 표시")

            # ▶▶ 하단 페이지 네비게이터
            _render_pagination_controls(current=page, total_pages=total_pages, state_key="_page")

            if show_exploded:
                st.markdown("##### 라벨 분해 표 (문서×소분류)")
                rows=[]
                for _,r in fdf.iterrows():
                    for s in r["sub_categories"]:
                        rows.append({"id":r["id"],"published_at":r["published_at"],"primary_main":r["primary_main"],
                                     "sub":s,"title":r["title"],"source":r["source"]})
                xdf=pd.DataFrame(rows)
                if not xdf.empty:
                    xdf=xdf.sort_values("published_at", ascending=True)
                    xdf["published_at"]=xdf["published_at"].dt.strftime("%Y-%m-%d %H:%M")
                    st.dataframe(xdf, use_container_width=True, height=300)

    # ---------- T2: 기간별 인사이트 ----------
    with T2:
        st.subheader("기간별 인사이트")
        colA,colB,colC = st.columns(3)
        for label,freq,col in [("일별","D",colA),("주별","W",colB),("월별","M",colC)]:
            agg=aggregate_time(fdf, freq=freq)
            with col:
                st.markdown(f"**{label} 기사 수**")
                if agg.empty: st.write("-")
                else: st.bar_chart(agg.set_index("period")["count"])
        st.markdown("---")
        ins=extract_insights(fdf)
        left,right=st.columns([1.2,1])
        with left:
            top_main=Counter([pm for pm in fdf["primary_main"]]).most_common(3)
            top_subs=Counter([ps for ps in fdf["primary_sub"]]).most_common(5)
            top_main_txt=", ".join([f"{k}({v})" for k,v in top_main]) if top_main else "-"
            top_sub_txt =", ".join([f"{k}({v})" for k,v in top_subs]) if top_subs else "-"
            st.markdown("**Top 대분류**: "+top_main_txt)
            st.markdown("**Top 소분류**: "+top_sub_txt)
            st.markdown("**Top 출처**: "+ins.get("top_sources","-"))
            st.markdown("**급상승 키워드(최근7일)**: "+ins.get("rising_keywords","-"))
        with right:
            st.info("Tip: 대분류를 먼저 좁히고 소분류를 선택하면 탐색이 쉬워집니다!")

    # ---------- T3: 워드클라우드 ----------
    with T3:
        st.subheader("워드클라우드")
        topk=st.slider("최대 키워드 수", 20, 200, 100, step=10)
        auto_font=st.toggle("한글 폰트 자동 적용", value=True)
        filter_bad=st.toggle("이모지/비지원 문자 토큰 제외", value=True)
        kw_freq=aggregate_keywords(fdf, topk=topk)
        render_wordcloud_wc(kw_freq, font_path=None, auto_korean_font=auto_font, filter_unrenderables=filter_bad)
        if kw_freq:
            st.markdown("**키워드 상위표**")
            st.dataframe(pd.DataFrame(kw_freq, columns=["keyword","freq"]), use_container_width=True, height=380)

    # ---------- T4: 키워드 네트워크 ----------
    with T4:
        st.subheader("키워드 연결 네트워크")
        min_w=st.slider("엣지 최소 가중치", 1, 10, 2)
        with st.spinner("네트워크 생성 중..."):
            co_graph=build_cooccurrence(fdf, min_edge_weight=min_w)
        render_keyword_network(co_graph, height="700px")

    # ---------- T5: 즐겨찾기 ----------
    with T5:
        st.subheader("⭐ 즐겨찾기")
        fav_df = get_favorites_df()
        if fav_df.empty:
            st.info("아직 즐겨찾기한 문서가 없습니다. 카드에서 **☆ 즐겨찾기**를 눌러보세요!")
        else:
            view_mode_fav = st.radio("보기", ["카드","표"], horizontal=True, key="fav_view_mode")
            per_page_fav  = st.slider("페이지 당 항목 수(즐겨찾기)", 10, 100, 20, step=10, key="fav_per_page")
            total_pages_f = int(np.ceil(len(fav_df)/per_page_fav))
            page_f = st.number_input("페이지(즐겨찾기)", min_value=1, max_value=max(1,total_pages_f),
                                   value=min(st.session_state.get("_page_fav",1), max(1,total_pages_f)), key="fav_page_num")
            st.session_state["_page_fav"]=page_f
            sidx=(page_f-1)*per_page_fav; eidx=sidx+per_page_fav
            page_fdf = fav_df.iloc[sidx:eidx].copy()

            current_favs = get_favorite_ids()

            if view_mode_fav=="카드":
                for _,row in page_fdf.iterrows():
                    title_html=_highlight(row["title"], None); summary_html=_highlight(row["summary"], None)
                    date_str=pd.to_datetime(row["published_at"]).strftime("%Y-%m-%d %H:%M")
                    meta=f"{row.get('source','-')} · {date_str}"
                    with st.container():
                        st.markdown("<div class='_card'>", unsafe_allow_html=True)
                        top_cols = st.columns([10, 2])
                        with top_cols[0]:
                            st.markdown(f"<div class='_title'>{title_html}</div>", unsafe_allow_html=True)
                            st.markdown(f"<div class='_meta'>{meta}</div>", unsafe_allow_html=True)
                        with top_cols[1]:
                            if int(row["id"]) in current_favs:
                                if st.button("★ 해제", key=f"fav_del_T5_{row['id']}"):
                                    remove_favorite(int(row["id"])); _rerun()
                            else:
                                if st.button("☆ 즐겨찾기", key=f"fav_add_T5_{row['id']}"):
                                    add_favorite(int(row["id"])); _rerun()
                        st.markdown(f"<div style='margin-top:6px'>{summary_html}</div>", unsafe_allow_html=True)
                        st.markdown("</div>", unsafe_allow_html=True)
            else:
                show_cols=["published_at","title","summary","source","keywords"]
                page_fdf["published_at"]=page_fdf["published_at"].dt.strftime("%Y-%m-%d %H:%M")
                st.dataframe(page_fdf[show_cols], use_container_width=True, height=420)
                st.caption("표 모드에서는 카드에서 즐겨찾기를 해제할 수 있습니다.")

            # === 구분선 + 내보내기 버튼(색상 구분) ===
            st.divider()
            exp1,exp2=st.columns(2)
            with exp1:
                st.download_button("💾 CSV로 내보내기 (즐겨찾기)",
                                   data=fav_df.to_csv(index=False).encode("utf-8-sig"),
                                   file_name="favorites.csv", mime="text/csv",
                                   type="primary")
            with exp2:
                fav_json = fav_df.to_json(orient="records", force_ascii=False, date_format="iso")
                st.download_button("🧾 JSON으로 내보내기 (즐겨찾기)",
                                   data=fav_json.encode("utf-8"),
                                   file_name="favorites.json", mime="application/json",
                                   type="secondary")

            # ▶▶ 하단 페이지 네비게이터
            _render_pagination_controls(current=page_f, total_pages=total_pages_f, state_key="_page_fav")

    # ---------- T6: 공학기술 잇슈픽 ----------
    with T6:
        st.subheader("📈 공학기술 잇슈픽 (최신 논문 제목 기반)")
        max_per_feed = st.slider("피드별 최대 논문 수", 20, 200, 80, step=20)
        papers_df = fetch_paper_titles(max_per_feed=max_per_feed)
        st.caption(f"수집된 논문 제목: {len(papers_df)}건 / 피드 {len(PAPER_FEEDS)}개")

        if papers_df.empty:
            st.info("논문 제목을 가져오지 못했습니다. 잠시 후 다시 시도해 주세요.")
        else:
            # 키워드 분석
            freq = analyze_titles_keywords(papers_df, topk=50)

            # TOP 3 CSV 표시 및 다운로드
            top3 = pd.DataFrame(freq[:3], columns=["keyword","mentions"])
            st.markdown("**잇슈픽 TOP 3 (CSV)**")
            st.dataframe(top3, use_container_width=True, height=120)
            st.download_button("💾 잇슈픽 TOP3 내려받기 (CSV)",
                               data=top3.to_csv(index=False).encode("utf-8-sig"),
                               file_name="issue_pick_top3.csv", mime="text/csv",
                               type="primary")

            # 아래 워드클라우드
            st.markdown("---")
            st.markdown("**논문 제목 기반 워드클라우드**")
            render_wordcloud_wc(freq, font_path=None, auto_korean_font=True, filter_unrenderables=True)

            # (선택) TOP 20 표
            if freq:
                st.markdown("**논문 키워드 상위표**")
                st.dataframe(pd.DataFrame(freq[:20], columns=["keyword","freq"]), use_container_width=True, height=300)

    st.markdown("---")
    st.caption(f"표시 중: {len(fdf)} 건 / 전체: {len(df)} 건")

# ============================================================
# 7) 엔트리포인트
# ============================================================
with st.sidebar:
    st.markdown("### 파이프라인")
    st.caption("RSS(다양한 출처·백필) → 본문추출 → 요약(모델 옵션) → 키워드(무의미/비기술 토큰 제거) → **SQLite(news.db)** 저장 → 시각화 → **잇슈픽(논문 제목 분석)**")

df_loaded = load_df_from_db(limit=UI_LOAD_LIMIT)
render_dashboard(df_loaded, categories_map=CATEGORIES, font_path=None)

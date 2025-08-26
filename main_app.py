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
        sql += f" LIMIT {limit}"
    df = pd.read_sql(sql, conn)
    if df.empty:
        return df
    
    # keywords JSON 파싱
    def parse_kw(kw_json):
        if not kw_json:
            return []
        try:
            return json.loads(kw_json)
        except (json.JSONDecodeError, TypeError):
            return []
    
    df["keywords"] = df["keywords"].apply(parse_kw)
    
    # published_at을 datetime 변환
    def safe_parse_date(date_str):
        if pd.isna(date_str) or not str(date_str).strip():
            return pd.NaT
        try:
            return pd.to_datetime(str(date_str).strip())
        except:
            return pd.NaT
    
    df["published_at"] = df["published_at"].apply(safe_parse_date)
    return df

def is_favorite(article_id: int) -> bool:
    cursor.execute("SELECT 1 FROM favorites WHERE article_id=? LIMIT 1", (article_id,))
    return cursor.fetchone() is not None

def toggle_favorite(article_id: int) -> bool:
    if is_favorite(article_id):
        cursor.execute("DELETE FROM favorites WHERE article_id=?", (article_id,))
        conn.commit()
        return False
    else:
        cursor.execute("INSERT OR IGNORE INTO favorites (article_id) VALUES (?)", (article_id,))
        conn.commit()
        return True

@st.cache_data(show_spinner=False)
def get_all_sources() -> List[str]:
    cursor.execute("SELECT DISTINCT source FROM articles ORDER BY source")
    return [r[0] for r in cursor.fetchall()]

# ============================================================
# 6) 키워드 시각화 (네트워크 그래프)
# ============================================================
def generate_keyword_network_graph(df: pd.DataFrame, top_n: int = 30) -> str:
    """키워드 네트워크 그래프 HTML 생성"""
    if df.empty:
        return "<p>데이터가 없습니다.</p>"
    
    # 키워드 빈도 계산
    all_keywords = []
    keyword_cooccurrence = defaultdict(int)
    
    for keywords_list in df["keywords"]:
        if keywords_list:
            keywords = [kw for kw in keywords_list if kw.strip()]
            all_keywords.extend(keywords)
            
            # 동시 출현 빈도 계산
            for i, kw1 in enumerate(keywords):
                for kw2 in keywords[i+1:]:
                    pair = tuple(sorted([kw1, kw2]))
                    keyword_cooccurrence[pair] += 1
    
    # 상위 키워드 선택
    keyword_counts = Counter(all_keywords)
    top_keywords = [kw for kw, _ in keyword_counts.most_common(top_n)]
    
    if not top_keywords:
        return "<p>키워드가 없습니다.</p>"
    
    # 네트워크 그래프 생성
    net = Network(height="400px", width="100%", bgcolor="#ffffff", font_color="black")
    
    # 노드 추가
    for kw in top_keywords:
        size = min(50, max(10, keyword_counts[kw] * 2))
        net.add_node(kw, label=kw, size=size)
    
    # 엣지 추가 (동시 출현 빈도가 높은 것만)
    for (kw1, kw2), weight in keyword_cooccurrence.items():
        if kw1 in top_keywords and kw2 in top_keywords and weight > 1:
            net.add_edge(kw1, kw2, weight=weight)
    
    # HTML 반환
    try:
        return net.generate_html()
    except:
        return "<p>네트워크 생성 실패</p>"

def create_wordcloud(df: pd.DataFrame) -> plt.Figure:
    """워드클라우드 생성"""
    if df.empty:
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5, "데이터가 없습니다", ha='center', va='center', fontsize=20)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        return fig
    
    # 모든 키워드 수집
    all_keywords = []
    for keywords_list in df["keywords"]:
        if keywords_list:
            all_keywords.extend([kw for kw in keywords_list if kw.strip()])
    
    if not all_keywords:
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5, "키워드가 없습니다", ha='center', va='center', fontsize=20)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        return fig
    
    # 키워드 빈도 계산
    keyword_freq = Counter(all_keywords)
    
    # 워드클라우드 생성
    try:
        from matplotlib import font_manager
        # 한글 폰트 설정 (시스템에 따라 다를 수 있음)
        font_path = None
        for font_name in ["NanumGothic", "Malgun Gothic", "AppleGothic"]:
            fonts = font_manager.findSystemFonts(fontpaths=None, fontext='ttf')
            for font in fonts:
                if font_name.lower() in font.lower():
                    font_path = font
                    break
            if font_path:
                break
        
        wordcloud = WordCloud(
            font_path=font_path,
            width=800, height=400,
            background_color='white',
            colormap='viridis',
            max_words=100,
            relative_scaling=0.5,
            stopwords=STOPWORDS
        ).generate_from_frequencies(keyword_freq)
        
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.imshow(wordcloud, interpolation='bilinear')
        ax.axis('off')
        return fig
        
    except Exception as e:
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5, f"워드클라우드 생성 실패: {str(e)}", ha='center', va='center', fontsize=16)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        return fig

# ============================================================
# 7) 메인 UI
# ============================================================
def main():
    # 사이드바: 필터링 옵션
    with st.sidebar:
        st.header("🔧 필터링")
        
        # 소스 필터
        available_sources = get_all_sources()
        selected_sources = st.multiselect(
            "뉴스 소스",
            options=available_sources,
            default=available_sources[:5] if len(available_sources) > 5 else available_sources
        )
        
        # 키워드 검색
        search_keyword = st.text_input("키워드 검색", placeholder="예: AI, 반도체, 5G")
        
        # 기간 필터
        col1, col2 = st.columns(2)
        with col1:
            date_from = st.date_input("시작일", value=datetime.now() - timedelta(days=7))
        with col2:
            date_to = st.date_input("종료일", value=datetime.now())
        
        # 즐겨찾기만 보기
        favorites_only = st.checkbox("즐겨찾기만 보기")
        
        st.divider()
        
        # 데이터 관리
        st.header("📊 데이터 관리")
        
        # 뉴스 수집 버튼
        if st.button("🔄 뉴스 수집", type="primary"):
            with st.spinner("뉴스 수집 중..."):
                ingest_all()
            st.success("뉴스 수집 완료!")
            st.rerun()
        
        # JSON 내보내기
        if st.button("💾 JSON 내보내기"):
            export_path = export_json()
            st.success(f"JSON 파일 저장: {export_path}")
            
            # GitHub 업로드 (설정된 경우)
            if ENABLE_GITHUB:
                try:
                    upload_to_github(export_path, GITHUB_REPO, GITHUB_PATH)
                    st.success("GitHub 업로드 완료!")
                except Exception as e:
                    st.error(f"GitHub 업로드 실패: {e}")
    
    # 메인 컨텐츠
    st.title("🗞️ 뉴스있슈~(News IT's Issue)")
    st.markdown("**IT/공학 뉴스 수집, 분석, 시각화 대시보드**")
    
    # 탭 구성
    tab1, tab2, tab3, tab4 = st.tabs(["📰 뉴스 목록", "📊 키워드 분석", "☁️ 워드클라우드", "⭐ 즐겨찾기"])
    
    # 데이터 로드
    df = load_df_from_db()
    
    if df.empty:
        st.info("데이터가 없습니다. 사이드바에서 '뉴스 수집' 버튼을 클릭하여 데이터를 수집하세요.")
        return
    
    # 필터링 적용
    filtered_df = df.copy()
    
    # 소스 필터
    if selected_sources:
        filtered_df = filtered_df[filtered_df["source"].isin(selected_sources)]
    
    # 키워드 검색
    if search_keyword:
        keyword_mask = filtered_df["keywords"].apply(
            lambda kws: any(search_keyword.lower() in str(kw).lower() for kw in (kws or []))
        ) | filtered_df["title"].str.contains(search_keyword, case=False, na=False) | \
        filtered_df["summary"].str.contains(search_keyword, case=False, na=False)
        filtered_df = filtered_df[keyword_mask]
    
    # 기간 필터
    if date_from and date_to and not filtered_df.empty:
        # published_at이 datetime이 아닐 수 있으므로 변환
        if filtered_df["published_at"].dtype == 'object':
            filtered_df["published_at"] = pd.to_datetime(filtered_df["published_at"], errors='coerce')
        
        # NaT 값이 아닌 것만 필터링
        valid_dates = ~filtered_df["published_at"].isna()
        if valid_dates.any():
            date_mask = valid_dates & \
                       (filtered_df["published_at"].dt.date >= date_from) & \
                       (filtered_df["published_at"].dt.date <= date_to)
            filtered_df = filtered_df[date_mask]
    
    # 즐겨찾기 필터
    if favorites_only:
        favorite_ids = []
        cursor.execute("SELECT article_id FROM favorites")
        favorite_ids = [row[0] for row in cursor.fetchall()]
        if favorite_ids:
            filtered_df = filtered_df[filtered_df["id"].isin(favorite_ids)]
        else:
            filtered_df = pd.DataFrame()  # 즐겨찾기가 없으면 빈 DataFrame
    
    # 비기술 기사 숨김
    if HIDE_NON_TECH_AT_UI:
        tech_mask = filtered_df.apply(
            lambda row: is_tech_doc(row["title"], "", row["keywords"]), axis=1
        )
        filtered_df = filtered_df[tech_mask]
    
    with tab1:
        st.header("📰 뉴스 목록")
        st.markdown(f"**총 {len(filtered_df)}건의 뉴스**")
        
        if filtered_df.empty:
            st.info("필터 조건에 맞는 뉴스가 없습니다.")
        else:
            # 페이지네이션
            items_per_page = 10
            total_pages = max(1, (len(filtered_df) + items_per_page - 1) // items_per_page)
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                page = st.selectbox("페이지", range(1, total_pages + 1)) - 1
            
            start_idx = page * items_per_page
            end_idx = min(start_idx + items_per_page, len(filtered_df))
            page_df = filtered_df.iloc[start_idx:end_idx]
            
            # 뉴스 카드 표시
            for idx, row in page_df.iterrows():
                with st.container():
                    col1, col2 = st.columns([10, 1])
                    
                    with col1:
                        # 제목과 기본 정보
                        st.markdown(f"### [{row['title']}]({row.get('link', '#')})")
                        
                        # 메타데이터
                        meta_col1, meta_col2, meta_col3 = st.columns(3)
                        with meta_col1:
                            st.markdown(f"**📰 {row['source']}**")
                        with meta_col2:
                            if pd.notna(row['published_at']):
                                try:
                                    if isinstance(row['published_at'], str):
                                        pub_date = pd.to_datetime(row['published_at'])
                                    else:
                                        pub_date = row['published_at']
                                    st.markdown(f"**📅 {pub_date.strftime('%Y-%m-%d %H:%M')}**")
                                except:
                                    st.markdown(f"**📅 {row['published_at']}**")
                        with meta_col3:
                            st.markdown(f"**🔗 ID: {row['id']}**")
                        
                        # 요약
                        if row["summary"]:
                            st.markdown(row["summary"])
                        
                        # 키워드
                        if row["keywords"]:
                            keywords_str = " · ".join([f"`{kw}`" for kw in row["keywords"][:10]])
                            st.markdown(f"**🏷️ 키워드:** {keywords_str}")
                    
                    with col2:
                        # 즐겨찾기 버튼
                        is_fav = is_favorite(row["id"])
                        fav_label = "⭐" if is_fav else "☆"
                        if st.button(fav_label, key=f"fav_{row['id']}"):
                            toggle_favorite(row["id"])
                            st.rerun()
                    
                    st.divider()
    
    with tab2:
        st.header("📊 키워드 네트워크 분석")
        
        if filtered_df.empty:
            st.info("분석할 데이터가 없습니다.")
        else:
            # 키워드 통계
            all_keywords = []
            for keywords_list in filtered_df["keywords"]:
                if keywords_list:
                    all_keywords.extend([kw for kw in keywords_list if kw.strip()])
            
            if all_keywords:
                keyword_counts = Counter(all_keywords)
                
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    st.subheader("🔥 인기 키워드 TOP 20")
                    top_keywords = keyword_counts.most_common(20)
                    for i, (kw, count) in enumerate(top_keywords, 1):
                        st.markdown(f"{i}. **{kw}** ({count}회)")
                
                with col2:
                    st.subheader("📈 키워드 분포")
                    top_kw_df = pd.DataFrame(top_keywords, columns=["키워드", "빈도"])
                    st.bar_chart(top_kw_df.set_index("키워드"))
                
                # 네트워크 그래프
                st.subheader("🕸️ 키워드 관계 네트워크")
                network_html = generate_keyword_network_graph(filtered_df)
                components.html(network_html, height=450)
            else:
                st.info("키워드 데이터가 없습니다.")
    
    with tab3:
        st.header("☁️ 워드클라우드")
        
        if filtered_df.empty:
            st.info("워드클라우드를 생성할 데이터가 없습니다.")
        else:
            wordcloud_fig = create_wordcloud(filtered_df)
            st.pyplot(wordcloud_fig)
    
    with tab4:
        st.header("⭐ 즐겨찾기")
        
        # 즐겨찾기 목록 가져오기
        favorite_sql = """
        SELECT a.id, a.title, a.summary, a.keywords, a.source, a.published as published_at
        FROM articles a
        INNER JOIN favorites f ON a.id = f.article_id
        ORDER BY f.created_at DESC
        """
        favorite_df = pd.read_sql(favorite_sql, conn)
        
        if favorite_df.empty:
            st.info("즐겨찾기한 뉴스가 없습니다.")
        else:
            # keywords JSON 파싱
            def parse_kw(kw_json):
                if not kw_json:
                    return []
                try:
                    return json.loads(kw_json)
                except (json.JSONDecodeError, TypeError):
                    return []
            
            favorite_df["keywords"] = favorite_df["keywords"].apply(parse_kw)
            
            st.markdown(f"**총 {len(favorite_df)}건의 즐겨찾기**")
            
            # 즐겨찾기 뉴스 표시
            for idx, row in favorite_df.iterrows():
                with st.container():
                    col1, col2 = st.columns([10, 1])
                    
                    with col1:
                        st.markdown(f"### {row['title']}")
                        
                        # 메타데이터
                        meta_col1, meta_col2 = st.columns(2)
                        with meta_col1:
                            st.markdown(f"**📰 {row['source']}**")
                        with meta_col2:
                            st.markdown(f"**📅 {row['published_at']}**")
                        
                        # 요약
                        if row["summary"]:
                            st.markdown(row["summary"])
                        
                        # 키워드
                        if row["keywords"]:
                            keywords_str = " · ".join([f"`{kw}`" for kw in row["keywords"][:10]])
                            st.markdown(f"**🏷️ 키워드:** {keywords_str}")
                    
                    with col2:
                        # 즐겨찾기 제거 버튼
                        if st.button("🗑️", key=f"remove_fav_{row['id']}"):
                            toggle_favorite(row["id"])
                            st.rerun()
                    
                    st.divider()

if __name__ == "__main__":
    main()
# -*- coding: utf-8 -*-
"""
테마별 컬렉션(재생목록) 기능 v2
- 규칙 기반 자동 수집(키워드/카테고리/기간/출처)
- 수동 추가/삭제
- 컬렉션별 조회/요약/내보내기
- pandas DataFrame 연계
- 개선 사항:
  1) 날짜 컬럼 타임존 정규화(Asia/Seoul 기준으로 tz-naive로 통일)
  2) 포함 키워드 OR 매칭 시 누적 시리즈 초기값 명시(pd.Series(False, ...))
  3) 문자열 매칭은 기본적으로 regex=False로 안전한 부분문자열 검색
  4) 컬렉션 규칙/ID 간단 직렬화(save/load) 지원
"""

from __future__ import annotations

import json
from typing import Dict, List, Optional, Any, Tuple

import pandas as pd
import pandas.api.types as ptypes


# =========================================
# 1) 카테고리 사전 (대분류 → 중분류 → 키워드)
# =========================================
CATEGORIES: Dict[str, Dict[str, List[str]]] = {
    "첨단 제조·기술 산업": {
        "반도체": ["반도체", "메모리", "시스템 반도체", "파운드리", "웨이퍼", "EUV", "노광", "장비", "소재", "HBM"],
        "자동차": ["자동차", "전기차", "자율주행", "모빌리티", "내연기관", "충전소", "배터리카"],
        "이차전지": ["이차전지", "배터리", "ESS", "양극재", "음극재", "전해질", "분리막"],
        "디스플레이": ["디스플레이", "OLED", "QD", "마이크로 LED", "LCD"],
        "로봇·스마트팩토리": ["로봇", "스마트팩토리", "산업자동화", "협동로봇"]
    },
    "디지털·ICT 산업": {
        "AI": ["AI", "인공지능", "머신러닝", "딥러닝", "생성형", "챗GPT", "멀티모달", "에이전트"],
        "ICT·통신": ["5G", "6G", "네트워크", "통신", "클라우드", "데이터센터", "엣지"],
        "소프트웨어·플랫폼": ["메타버스", "SaaS", "보안", "핀테크", "플랫폼"]
    },
    "에너지·환경 산업": {
        "에너지": ["석유", "가스", "원자력", "신재생", "풍력", "태양광", "수소"],
        "환경·탄소중립": ["탄소중립", "폐기물", "재활용", "친환경", "수처리", "CCUS"]
    },
    "바이오·헬스케어 산업": {
        "바이오·제약": ["바이오", "제약", "신약", "바이오시밀러", "세포치료제", "유전자치료"],
        "의료기기·헬스케어": ["헬스케어", "의료기기", "원격진료", "디지털 헬스", "웨어러블"]
    },
    "소재·화학 산업": {
        "첨단 소재": ["탄소소재", "그래핀", "나노소재", "고분자", "복합소재"],
        "정밀화학·석유화학": ["케미컬", "석유화학", "특수가스", "반도체용 케미컬"]
    },
    "인프라·기반 산업": {
        "철강·조선·건설": ["철강", "조선", "건설", "스마트 건설", "친환경 선박"],
        "물류·유통": ["스마트 물류", "전자상거래", "유통", "공급망"],
        "농업·식품": ["스마트팜", "농업", "대체식품", "식품"]
    }
}


# =========================================
# 2) 분류(카테고리) 유틸
# =========================================
def _pick_best_category(title: str, content: str) -> Tuple[str, str, List[str]]:
    """
    제목/본문에서 가장 잘 매칭되는 (대분류, 중분류)와 매칭 키워드 목록을 고른다.
    - 단순 '포함' 매칭(대소문자 구분 X)
    - 가장 많은 키워드가 걸린 중분류를 대표로 선택
    """
    text = (title or "") + " " + (content or "")
    text_low = text.lower()

    best: Tuple[str, str, List[str]] = ("기타", "기타", [])
    best_hits = 0

    for main_cat, subcats in CATEGORIES.items():
        for sub_cat, keywords in subcats.items():
            hits = [kw for kw in keywords if kw.lower() in text_low]
            if len(hits) > best_hits:
                best = (main_cat, sub_cat, hits)
                best_hits = len(hits)

    return best


def classify_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    DataFrame에 (대분류/중분류/매칭키워드) 컬럼을 채운다.
    - 필요한 컬럼: ["title", "content"]
    """
    out = df.copy()
    results = out.apply(
        lambda r: _pick_best_category(r.get("title", ""), r.get("content", "")),
        axis=1
    )
    out[["대분류", "중분류", "매칭키워드"]] = pd.DataFrame(results.tolist(), index=out.index)
    return out


# =========================================
# 3) 테마별 컬렉션 매니저
# =========================================
class ThemeCollections:
    """
    테마별 컬렉션(=재생목록) 관리
    - 규칙 기반 자동 수집 + 수동 추가/삭제
    - 규칙: 포함키워드, 제외키워드, 대분류, 중분류, 출처, 기간
    - 저장 구조:
        self.collections[name] = {
            "rules": {...},
            "ids": set([...])   # 뉴스 id 집합
        }
    """

    def __init__(self, news_df: pd.DataFrame, id_col: str = "id"):
        """
        :param news_df: 전체 뉴스 DataFrame (필수 컬럼: id, date, title, content, source)
        :param id_col:  고유 식별자 컬럼명
        """
        self.id_col = id_col
        self.news_df = self._prep_df(news_df)
        self.collections: Dict[str, Dict[str, Any]] = {}

    @staticmethod
    def _normalize_dates(out: pd.DataFrame) -> pd.DataFrame:
        """date 컬럼을 tz-aware/naive 혼합 → Asia/Seoul 기준 tz-naive(datetime64[ns])로 통일"""
        if "date" not in out.columns:
            return out
        # to_datetime (errors='coerce'로 잘못된 형식은 NaT)
        out["date"] = pd.to_datetime(out["date"], errors="coerce")
        if ptypes.is_datetime64tz_dtype(out["date"]):
            # tz-aware -> Asia/Seoul로 변환 후 tz 제거
            out["date"] = out["date"].dt.tz_convert("Asia/Seoul").dt.tz_localize(None)
        # 이미 naive이면 그대로
        return out

    @classmethod
    def _prep_df(cls, df: pd.DataFrame) -> pd.DataFrame:
        """date를 datetime으로, 결측치 기본값 처리, 분류 컬럼 생성, 타임존 정규화"""
        out = df.copy()
        out = cls._normalize_dates(out)
        # 결측 기본값
        for col in ["title", "content", "source"]:
            if col in out.columns:
                out[col] = out[col].fillna("")
        # 분류 컬럼 채우기
        out = classify_dataframe(out)
        return out

    def refresh_news(self, news_df: pd.DataFrame):
        """뉴스 원본 갱신 후, 분류 재계산"""
        self.news_df = self._prep_df(news_df)

    # ---------- 컬렉션 CRUD ----------
    def create(self, name: str, rules: Optional[Dict[str, Any]] = None):
        """새 컬렉션 생성 (동명이 존재하면 예외)"""
        if name in self.collections:
            raise ValueError(f"컬렉션 '{name}' 이(가) 이미 존재합니다.")
        self.collections[name] = {"rules": rules or {}, "ids": set()}

    def update_rules(self, name: str, rules: Dict[str, Any]):
        """컬렉션 규칙 갱신"""
        self._ensure_exists(name)
        self.collections[name]["rules"] = rules or {}

    def delete(self, name: str):
        """컬렉션 삭제"""
        self._ensure_exists(name)
        del self.collections[name]

    def list_collections(self) -> pd.DataFrame:
        """컬렉션 목록/규칙 요약"""
        rows = []
        for nm, obj in self.collections.items():
            r = obj.get("rules", {})
            rows.append({
                "name": nm,
                "규칙_포함키워드": ", ".join(r.get("include_keywords", []) or []),
                "규칙_제외키워드": ", ".join(r.get("exclude_keywords", []) or []),
                "규칙_대분류": ", ".join(r.get("include_main", []) or []),
                "규칙_중분류": ", ".join(r.get("include_sub", []) or []),
                "규칙_출처": ", ".join(r.get("include_sources", []) or []),
                "규칙_기간_from": r.get("date_from") or "",
                "규칙_기간_to": r.get("date_to") or "",
                "아이템수": len(obj.get("ids", []))
            })
        return pd.DataFrame(rows)

    # ---------- 규칙 기반 자동 수집 ----------
    def autofill(self, name: str, append: bool = True) -> int:
        """
        규칙에 따라 자동 수집하여 컬렉션에 담는다.
        :param append: True면 기존과 합치고, False면 컬렉션을 이 규칙 결과로 재설정
        :return: 추가된 아이템 수
        """
        self._ensure_exists(name)
        rules = self.collections[name].get("rules", {}) or {}

        df = self.news_df.copy()
        if df.empty:
            if not append:
                self.collections[name]["ids"] = set()
            return 0

        mask = pd.Series(True, index=df.index)

        # 1) 기간 필터 (df["date"]는 tz-naive로 통일됨)
        date_from = rules.get("date_from")  # "YYYY-MM-DD" or None
        date_to = rules.get("date_to")
        if date_from:
            mask &= (df["date"] >= pd.to_datetime(date_from))
        if date_to:
            mask &= (df["date"] <= pd.to_datetime(date_to))

        # 제목+본문 결합 열 (대소문자 구분 없이 검색), NaN 방지
        text = (df["title"].fillna("") + " " + df["content"].fillna("")).str.lower()

        # 2) 포함 키워드(AND/OR 옵션) - 기본 OR
        include_keywords: List[str] = [k.lower() for k in rules.get("include_keywords", []) if k]
        match_mode = (rules.get("match_mode") or "OR").upper()  # "OR" | "AND"
        if include_keywords:
            if match_mode == "AND":
                for kw in include_keywords:
                    mask &= text.str.contains(kw, regex=False, na=False)
            else:  # OR
                m = pd.Series(False, index=df.index)
                for kw in include_keywords:
                    m = m | text.str.contains(kw, regex=False, na=False)
                mask &= m

        # 3) 제외 키워드
        exclude_keywords: List[str] = [k.lower() for k in rules.get("exclude_keywords", []) if k]
        for kw in exclude_keywords:
            mask &= ~text.str.contains(kw, regex=False, na=False)

        # 4) 대분류/중분류 필터
        include_main = rules.get("include_main", [])  # 대분류 리스트
        if include_main:
            mask &= df["대분류"].isin(include_main)

        include_sub = rules.get("include_sub", [])  # 중분류 리스트
        if include_sub:
            mask &= df["중분류"].isin(include_sub)

        # 5) 출처 필터
        include_sources = rules.get("include_sources", [])
        if include_sources and "source" in df.columns:
            mask &= df["source"].isin(include_sources)

        # 최종 후보
        candidates = set(df.loc[mask, self.id_col].dropna().tolist())

        # 컬렉션에 반영
        if append:
            before = len(self.collections[name]["ids"])
            self.collections[name]["ids"].update(candidates)
            added = len(self.collections[name]["ids"]) - before
        else:
            before_set = self.collections[name]["ids"]
            self.collections[name]["ids"] = candidates
            added = len(candidates - before_set)

        return added

    # ---------- 수동 추가/삭제 ----------
    def add_items(self, name: str, ids: List[Any]):
        """뉴스 ID 수동 추가"""
        self._ensure_exists(name)
        self.collections[name]["ids"].update(ids)

    def remove_items(self, name: str, ids: List[Any]):
        """뉴스 ID 수동 삭제"""
        self._ensure_exists(name)
        self.collections[name]["ids"].difference_update(ids)

    # ---------- 조회/요약/내보내기 ----------
    def get_dataframe(self, name: str, columns: Optional[List[str]] = None) -> pd.DataFrame:
        """컬렉션을 DataFrame으로 반환"""
        self._ensure_exists(name)
        ids = list(self.collections[name]["ids"])
        if not ids:
            return pd.DataFrame(columns=columns or self.news_df.columns.tolist())
        base = self.news_df[self.news_df[self.id_col].isin(ids)].copy()
        if columns:
            keep = [c for c in columns if c in base.columns]
            return base[keep]
        return base

    def summarize(self, name: str, by: str = "대분류") -> pd.DataFrame:
        """
        컬렉션 내부 요약(기본: 대분류별 기사수)
        옵션: '중분류', 'source' 등 컬럼명으로 변경 가능
        """
        df = self.get_dataframe(name)
        if df.empty:
            return pd.DataFrame(columns=[by, "count", "ratio(%)"])
        grp = df.groupby(by, dropna=False).size().reset_index(name="count").sort_values("count", ascending=False)
        grp["ratio(%)"] = (grp["count"] / grp["count"].sum() * 100).round(1)
        return grp

    def export_csv(self, name: str, path: str):
        """컬렉션 CSV 저장"""
        df = self.get_dataframe(name)
        df.to_csv(path, index=False, encoding="utf-8-sig")

    # ---------- 직렬화(선택) ----------
    def save_collections(self, path: str):
        """컬렉션 규칙/ID를 JSON으로 저장 (뉴스 본문은 저장하지 않음)"""
        obj = {}
        for nm, data in self.collections.items():
            obj[nm] = {
                "rules": data.get("rules", {}),
                "ids": sorted(list(data.get("ids", set())))
            }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)

    def load_collections(self, path: str, replace: bool = False):
        """JSON에서 컬렉션 규칙/ID 로드 (뉴스 본문은 별도 refresh 필요)"""
        with open(path, "r", encoding="utf-8") as f:
            obj = json.load(f)
        if replace:
            self.collections = {}
        for nm, data in obj.items():
            self.collections[nm] = {
                "rules": data.get("rules", {}) or {},
                "ids": set(data.get("ids", []))
            }

    # ---------- 내부 유틸 ----------
    def _ensure_exists(self, name: str):
        if name not in self.collections:
            raise ValueError(f"컬렉션 '{name}' 이(가) 존재하지 않습니다.")


# =========================================
# 4) 샘플 데이터 & 실행 예시
# =========================================
if __name__ == "__main__":
    # 샘플 뉴스 데이터 (id, date, source, title, content)
    news = [
        {"id": 1, "date": "2025-08-20", "source": "연합뉴스",
         "title": "삼성, 차세대 HBM 반도체 투자 확대", "content": "EUV 노광 장비와 파운드리 라인 증설 계획 발표"},
        {"id": 2, "date": "2025-08-21", "source": "머니투데이",
         "title": "현대차, 전기차 자율주행 소프트웨어 업데이트", "content": "OTA로 자율주행 성능 향상"},
        {"id": 3, "date": "2025-08-21", "source": "ZDNet",
         "title": "생성형 AI 에이전트, 데이터센터 고도화 가속", "content": "클라우드와 엣지 인프라가 핵심"},
        {"id": 4, "date": "2025-08-22", "source": "조선비즈",
         "title": "태양광·풍력 신재생 확대 로드맵 공개", "content": "탄소중립 위해 수소 인프라도 병행"},
        {"id": 5, "date": "2025-08-22", "source": "헤럴드경제",
         "title": "바이오 신약 임상 3상 진입", "content": "유전자치료제와 디지털 헬스 연계"},
        {"id": 6, "date": "2025-08-23", "source": "블로터",
         "title": "반도체 장비 국산화, 협동로봇 라인 도입", "content": "스마트팩토리 전환 가속"},
        {"id": 7, "date": "2025-08-23", "source": "매일경제",
         "title": "데이터센터 수요 폭증, 6G 준비 본격화", "content": "클라우드 네트워크 인프라 투자 확대"},
    ]
    df_all = pd.DataFrame(news)

    # 매니저 생성
    tm = ThemeCollections(df_all)

    # ----- ① 컬렉션 생성: '반도체 동향' (키워드+대분류+기간+출처) -----
    tm.create("반도체 동향", rules={
        "include_keywords": ["반도체", "HBM", "파운드리", "EUV", "장비"],
        "exclude_keywords": ["루머"],                 # 제외할 키워드 예시
        "match_mode": "OR",                           # OR(기본) 또는 AND
        "include_main": ["첨단 제조·기술 산업"],       # 대분류 필터
        "include_sub": ["반도체"],                     # 중분류 필터
        "include_sources": ["연합뉴스", "블로터"],       # 출처 제한
        "date_from": "2025-08-20",
        "date_to": "2025-08-31"
    })
    added1 = tm.autofill("반도체 동향")
    print(f"[반도체 동향] 자동 수집 추가 건수: {added1}")

    # 수동으로 특정 기사도 추가 가능(예: 관련성 있지만 규칙에 안걸린 기사)
    tm.add_items("반도체 동향", [6])

    # ----- ② 컬렉션 생성: 'AI/데이터센터' (키워드 + 디지털·ICT 대분류) -----
    tm.create("AI/데이터센터", rules={
        "include_keywords": ["AI", "생성형", "데이터센터", "클라우드", "엣지", "6G"],
        "match_mode": "OR",
        "include_main": ["디지털·ICT 산업"],          # 대분류
        # 중분류는 생략(전체 허용)
        "date_from": "2025-08-20"
    })
    added2 = tm.autofill("AI/데이터센터")
    print(f"[AI/데이터센터] 자동 수집 추가 건수: {added2}")

    # ----- ③ 컬렉션 목록/규칙 요약 -----
    print("\n[컬렉션 목록]")
    print(tm.list_collections())

    # ----- ④ 컬렉션 조회 -----
    print("\n[반도체 동향 - 상세 목록]")
    print(tm.get_dataframe("반도체 동향", columns=["id", "date", "source", "대분류", "중분류", "title"]))

    print("\n[AI/데이터센터 - 상세 목록]")
    print(tm.get_dataframe("AI/데이터센터", columns=["id", "date", "source", "대분류", "중분류", "title"]))

    # ----- ⑤ 컬렉션 요약(대분류/중분류/출처 단위 자유) -----
    print("\n[반도체 동향 - 중분류 요약]")
    print(tm.summarize("반도체 동향", by="중분류"))

    print("\n[AI/데이터센터 - 출처 요약]")
    print(tm.summarize("AI/데이터센터", by="source"))

    # ----- ⑥ CSV 내보내기 -----
    tm.export_csv("반도체 동향", "semiconductor_playlist.csv")
    tm.export_csv("AI/데이터센터", "ai_dc_playlist.csv")
    print("\n[저장 완료] semiconductor_playlist.csv, ai_dc_playlist.csv")

    # ----- ⑦ 컬렉션 저장/로드 예시 -----
    tm.save_collections("collections_snapshot.json")
    print("[저장 완료] collections_snapshot.json")
    # 필요시:
    # tm.load_collections("collections_snapshot.json", replace=True)

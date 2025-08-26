# 뉴스있슈~ (News IT's Issue)

IT/공학 뉴스 수집, 분석, 시각화 플랫폼

## 📁 프로젝트 구조

```
streamlit_04/
├── backend/               # FastAPI 백엔드 서버
│   ├── main.py           # API 엔드포인트
│   ├── news_collector.py # 뉴스 수집 모듈  
│   ├── news.db           # SQLite 데이터베이스
│   └── requirements.txt  # Python 의존성
│
├── frontend/             # React 프론트엔드
│   └── news-app/
│       ├── src/          # React 소스코드
│       ├── dist/         # 빌드된 정적 파일
│       └── package.json  # Node.js 의존성
│
├── streamlit/            # Streamlit 원본 앱 (보관용)
│   ├── main_app.py       # Streamlit 메인 앱
│   ├── keyword_maker.py  # 키워드 추출
│   └── translate_util.py # 번역 유틸
│
└── render.yaml           # Render.com 배포 설정
```

## 🚀 로컬 실행

### Backend 실행
```bash
cd backend
pip install -r requirements.txt
python -c "from news_collector import init_db, collect_all_news; init_db(); collect_all_news()"
uvicorn main:app --reload
```

### Frontend 실행
```bash
cd frontend/news-app
npm install
npm run dev
```

## 🌐 배포 (Render.com)

1. GitHub 리포지토리를 Render에 연결
2. `render.yaml` 설정 자동 적용
3. 환경변수 설정:
   - `DB_PATH`: backend/news.db
   - `COLLECT_ON_STARTUP`: 1 (초기 뉴스 수집)

## 📊 주요 기능

- **뉴스 수집**: 30개 RSS 피드 소스 (한국 15개, 글로벌 15개)
- **키워드 분석**: 형태소 분석 기반 키워드 추출
- **시각화**: 워드클라우드, 키워드 네트워크
- **즐겨찾기**: 중요 뉴스 저장
- **반응형 UI**: Material-UI 기반 모던 디자인
- **다크모드**: 눈 피로도 감소

## 🔧 환경 설정 (.env)

```env
MAX_RESULTS=10
MAX_TOTAL_PER_SOURCE=200  
RSS_BACKFILL_PAGES=3
DB_PATH=backend/news.db
ENABLE_SUMMARY=0           # OpenAI 요약 비활성화
ENABLE_HTTP_CACHE=1
PARALLEL_MAX_WORKERS=8
```

## 📝 API 엔드포인트

- `GET /api/articles` - 뉴스 목록
- `GET /api/sources` - 뉴스 소스 목록
- `GET /api/keywords/stats` - 키워드 통계
- `GET /api/keywords/network` - 키워드 네트워크
- `POST /api/collect-news` - 뉴스 수집 트리거
- `GET /api/favorites` - 즐겨찾기 목록
- `POST /api/favorites/add` - 즐겨찾기 추가
- `DELETE /api/favorites/{id}` - 즐겨찾기 제거

## 🛠️ 기술 스택

- **Backend**: FastAPI, SQLite, BeautifulSoup4, Feedparser
- **Frontend**: React, Material-UI, TypeScript, Vite
- **배포**: Render.com
- **NLP**: Kiwi (한국어 형태소 분석)
# 기술 아키텍처

## 🏗️ 전체 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Layer                             │
├─────────────────────────────────────────────────────────────────┤
│  React App (TypeScript)  │  Material-UI  │  Axios HTTP Client  │
│  - Component State       │  - Theming     │  - API Communication│  
│  - Local Storage        │  - Icons       │  - Error Handling   │
│  - Browser Routing      │  - Layout      │  - Request/Response │
└─────────────────────────────────────────────────────────────────┘
                                   │
                              HTTPS/REST API
                                   │
┌─────────────────────────────────────────────────────────────────┐
│                      Application Layer                          │
├─────────────────────────────────────────────────────────────────┤
│  FastAPI Server (Python)  │  Pydantic Models │  CORS Middleware│
│  - Async Request Handling │  - Data Validation│  - Cross-Origin │
│  - Route Management      │  - Serialization  │  - Request Auth │
│  - Business Logic       │  - Type Safety    │  - Headers      │
└─────────────────────────────────────────────────────────────────┘
                                   │
                            SQLite Connection
                                   │
┌─────────────────────────────────────────────────────────────────┐
│                        Data Layer                               │
├─────────────────────────────────────────────────────────────────┤
│  SQLite Database          │  File System     │  External APIs   │
│  - Articles Table        │  - Static Assets  │  - News Sources  │
│  - Favorites Table       │  - Logs          │  - OpenAI API    │
│  - Indexes & Relations   │  - Cache Files    │  - RSS Feeds     │
└─────────────────────────────────────────────────────────────────┘
```

## 🎨 프론트엔드 아키텍처

### React 컴포넌트 구조

```
src/
├── components/              # 재사용 가능한 UI 컴포넌트
│   ├── ArticleCard.tsx     # 개별 기사 카드 컴포넌트
│   ├── KeywordCloud.tsx    # 키워드 클라우드 시각화
│   ├── KeywordNetwork.tsx  # 네트워크 그래프 시각화  
│   └── StatsChart.tsx      # 통계 차트 컴포넌트
├── api/                    # API 통신 레이어
│   └── newsApi.ts          # HTTP 클라이언트 및 타입 정의
├── assets/                 # 정적 자원
├── App.tsx                 # 메인 애플리케이션 컴포넌트
├── config.ts              # 환경 설정
└── main.tsx               # 애플리케이션 진입점
```

### 상태 관리 패턴

```typescript
// 컴포넌트별 로컬 상태 관리
const [articles, setArticles] = useState<Article[]>([]);
const [loading, setLoading] = useState(false);
const [error, setError] = useState<string | null>(null);

// API 호출 패턴
const loadArticles = async () => {
  setLoading(true);
  setError(null);
  try {
    const data = await newsApi.getArticles(params);
    setArticles(data);
  } catch (err) {
    setError('데이터 로드에 실패했습니다.');
  } finally {
    setLoading(false);
  }
};
```

### 컴포넌트 생명주기

```typescript
// 초기 데이터 로드
useEffect(() => {
  loadArticles();
  loadSources();
  loadKeywords();
  loadStats();
}, []);

// 검색 조건 변경 시 데이터 재로드
useEffect(() => {
  if (searchTerm || selectedSource) {
    loadArticles();
  }
}, [searchTerm, selectedSource]);
```

## ⚙️ 백엔드 아키텍처

### FastAPI 애플리케이션 구조

```python
backend/
├── main.py              # FastAPI 애플리케이션 진입점
├── init_db.py          # 데이터베이스 초기화 스크립트
├── requirements.txt    # Python 의존성 목록
├── start.sh           # 프로덕션 시작 스크립트
└── render.yaml        # Render.com 배포 설정
```

### API 라우팅 구조

```python
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우트 정의
@app.get("/api/articles")
async def get_articles(limit: int = 100, search: str = None): ...

@app.post("/api/favorites/add")
async def add_favorite(request: FavoriteRequest): ...
```

### 데이터 모델 (Pydantic)

```python
from pydantic import BaseModel
from typing import Optional

class Article(BaseModel):
    id: int
    title: str
    link: str
    published: str
    source: str
    summary: Optional[str] = None
    keywords: Optional[str] = None
    is_favorite: bool = False

class KeywordStats(BaseModel):
    keyword: str
    count: int
```

## 🗄️ 데이터베이스 설계

### ERD (Entity Relationship Diagram)

```sql
┌─────────────────┐     ┌─────────────────┐
│    articles     │     │   favorites     │
├─────────────────┤     ├─────────────────┤
│ id (PK)         │◄────┤ article_id (FK) │
│ title           │     │ id (PK)         │
│ link (UNIQUE)   │     │ created_at      │
│ published       │     └─────────────────┘
│ source          │
│ raw_text        │
│ summary         │
│ keywords        │
│ created_at      │
└─────────────────┘
```

### 테이블 스키마

```sql
-- 기사 정보 테이블
CREATE TABLE articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    link TEXT UNIQUE NOT NULL,
    published TEXT NOT NULL,
    source TEXT NOT NULL,
    raw_text TEXT,
    summary TEXT,
    keywords TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 즐겨찾기 테이블
CREATE TABLE favorites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (article_id) REFERENCES articles(id),
    UNIQUE(article_id)
);

-- 성능 최적화 인덱스
CREATE INDEX idx_articles_published ON articles(published DESC);
CREATE INDEX idx_articles_source ON articles(source);
CREATE INDEX idx_favorites_article_id ON favorites(article_id);
```

## 🌐 네트워크 아키텍처

### HTTP 통신 플로우

```
┌─────────────┐    HTTPS     ┌─────────────┐    SQLite    ┌─────────────┐
│   Browser   │──────────────▶│  FastAPI    │─────────────▶│  Database   │
│  (React)    │◄──────────────│  (Python)   │◄─────────────│  (SQLite)   │
└─────────────┘    JSON      └─────────────┘    Query     └─────────────┘
```

### API 요청/응답 예시

```typescript
// GET 요청
const response = await axios.get('/api/articles', {
  params: {
    limit: 100,
    search: '인공지능',
    source: 'TechCrunch'
  }
});

// POST 요청  
const response = await axios.post('/api/favorites/add', {
  article_id: 123
});
```

## 🔧 빌드 및 배포 아키텍처

### 개발 환경

```bash
# 프론트엔드 개발 서버
npm run dev          # → http://localhost:5173

# 백엔드 개발 서버  
uvicorn main:app --reload  # → http://localhost:8000
```

### 프로덕션 환경

```
┌─────────────────┐    CDN     ┌─────────────────┐
│  GitHub Pages   │◄───────────│   Static Assets │
│  (Frontend)     │            │   (CSS, JS)     │
└─────────────────┘            └─────────────────┘
         │
    API Calls
         │
         ▼
┌─────────────────┐    Docker  ┌─────────────────┐
│   Render.com    │◄───────────│  FastAPI Server │
│   (Backend)     │            │  (Python 3.11)  │
└─────────────────┘            └─────────────────┘
```

### CI/CD 파이프라인

```yaml
# .github/workflows/deploy.yml
name: Deploy to GitHub Pages

on:
  push:
    branches: [ main ]

jobs:
  build:
    - uses: actions/checkout@v4
    - uses: actions/setup-node@v4
    - run: npm ci --legacy-peer-deps
    - run: npm run build
    - uses: actions/upload-pages-artifact@v3
  
  deploy:
    - uses: actions/deploy-pages@v4
```

## 🚀 성능 최적화 전략

### 프론트엔드 최적화

1. **코드 스플리팅**
   ```typescript
   const LazyComponent = React.lazy(() => import('./Component'));
   ```

2. **메모이제이션**
   ```typescript
   const MemoizedComponent = React.memo(Component);
   const memoizedValue = useMemo(() => expensiveCalculation(), [deps]);
   ```

3. **번들 최적화**
   ```javascript
   // vite.config.ts
   export default defineConfig({
     build: {
       rollupOptions: {
         output: {
           manualChunks: {
             vendor: ['react', 'react-dom'],
             ui: ['@mui/material', '@mui/icons-material']
           }
         }
       }
     }
   });
   ```

### 백엔드 최적화

1. **비동기 처리**
   ```python
   @app.get("/api/articles")
   async def get_articles():
       async with get_db_connection() as conn:
           return await fetch_articles(conn)
   ```

2. **데이터베이스 최적화**
   ```python
   # 인덱스 활용 쿼리
   cursor.execute("""
       SELECT * FROM articles 
       WHERE published >= ? 
       ORDER BY published DESC 
       LIMIT ?
   """, (date_filter, limit))
   ```

3. **캐싱 전략**
   ```python
   from functools import lru_cache
   
   @lru_cache(maxsize=128)
   def get_keyword_stats(limit: int):
       # 캐시된 키워드 통계 반환
   ```

## 🔒 보안 아키텍처

### 데이터 보호

1. **SQL 인젝션 방지**
   ```python
   # 안전한 매개변수 바인딩
   cursor.execute("SELECT * FROM articles WHERE id = ?", (article_id,))
   ```

2. **CORS 정책**
   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["https://aebonlee.github.io"],
       allow_methods=["GET", "POST", "DELETE"],
       allow_headers=["*"]
   )
   ```

3. **환경 변수 관리**
   ```python
   import os
   from dotenv import load_dotenv
   
   load_dotenv()
   API_KEY = os.getenv("OPENAI_API_KEY")
   ```

### 클라이언트 보안

1. **XSS 방지**
   ```typescript
   // React의 자동 이스케이핑 활용
   <div dangerouslySetInnerHTML={{__html: sanitizedHTML}} />
   ```

2. **HTTPS 전용 통신**
   ```typescript
   const api = axios.create({
     baseURL: 'https://streamlit-04.onrender.com',
     timeout: 10000
   });
   ```

## 📊 모니터링 및 로깅

### 에러 처리

```typescript
// 프론트엔드 에러 바운더리
class ErrorBoundary extends React.Component {
  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('React Error:', error, errorInfo);
  }
}

// 백엔드 예외 처리
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )
```

### 성능 메트릭스

```python
import time
from functools import wraps

def measure_time(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.time()
        result = await func(*args, **kwargs)
        end = time.time()
        logger.info(f"{func.__name__} took {end - start:.2f}s")
        return result
    return wrapper
```

---

**다음**: [API 문서](./api/API_DOCUMENTATION.md)
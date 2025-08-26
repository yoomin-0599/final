# API 문서

## 📚 API 개요

뉴스있슈 백엔드는 RESTful API를 제공하며, JSON 형식으로 데이터를 교환합니다.

**기본 URL**: `https://streamlit-04.onrender.com`

## 🔑 인증

현재 버전에서는 인증이 필요하지 않습니다. 모든 엔드포인트는 공개적으로 접근 가능합니다.

## 📋 엔드포인트 목록

### 기사 관리

#### `GET /api/articles`
기사 목록을 조회합니다.

**매개변수:**
```typescript
interface ArticleParams {
  limit?: number;        // 기본값: 100, 최대: 2000
  offset?: number;       // 기본값: 0
  source?: string;       // 소스 필터 (선택사항)
  search?: string;       // 검색어 (제목, 요약, 키워드)
  favorites_only?: boolean; // 즐겨찾기만 조회
}
```

**응답:**
```typescript
interface Article {
  id: number;
  title: string;
  link: string;
  published: string;
  source: string;
  summary: string | null;
  keywords: string | null;
  created_at: string;
  is_favorite: boolean;
}

type ArticlesResponse = Article[];
```

**예시 요청:**
```bash
GET /api/articles?limit=10&search=인공지능&source=TechCrunch
```

**예시 응답:**
```json
[
  {
    "id": 1,
    "title": "AI 혁신의 새로운 전환점",
    "link": "https://example.com/article/1",
    "published": "2025-08-26T10:00:00Z",
    "source": "TechCrunch",
    "summary": "인공지능 기술의 최신 동향...",
    "keywords": "AI, 인공지능, 머신러닝",
    "created_at": "2025-08-26T10:05:00Z",
    "is_favorite": false
  }
]
```

#### `GET /api/sources`
사용 가능한 뉴스 소스 목록을 조회합니다.

**응답:**
```typescript
type SourcesResponse = string[];
```

**예시 응답:**
```json
["TechCrunch", "Wired", "The Verge", "MIT Technology Review"]
```

### 키워드 분석

#### `GET /api/keywords/stats`
키워드별 통계를 조회합니다.

**매개변수:**
- `limit`: 반환할 키워드 수 (기본값: 50, 최대: 200)

**응답:**
```typescript
interface KeywordStats {
  keyword: string;
  count: number;
}

type KeywordStatsResponse = KeywordStats[];
```

**예시 응답:**
```json
[
  {"keyword": "AI", "count": 45},
  {"keyword": "머신러닝", "count": 32},
  {"keyword": "딥러닝", "count": 28}
]
```

#### `GET /api/keywords/network`
키워드 네트워크 데이터를 조회합니다.

**매개변수:**
- `limit`: 분석할 상위 키워드 수 (기본값: 30, 최대: 100)

**응답:**
```typescript
interface NetworkNode {
  id: string;
  label: string;
  value: number;
}

interface NetworkEdge {
  from: string;
  to: string;
  value: number;
}

interface NetworkData {
  nodes: NetworkNode[];
  edges: NetworkEdge[];
}
```

**예시 응답:**
```json
{
  "nodes": [
    {"id": "AI", "label": "AI", "value": 45},
    {"id": "머신러닝", "label": "머신러닝", "value": 32}
  ],
  "edges": [
    {"from": "AI", "to": "머신러닝", "value": 15}
  ]
}
```

### 즐겨찾기 관리

#### `GET /api/favorites`
사용자의 즐겨찾기 목록을 조회합니다.

**응답:**
```typescript
type FavoritesResponse = Article[];
```

#### `POST /api/favorites/add`
기사를 즐겨찾기에 추가합니다.

**요청 본문:**
```typescript
interface FavoriteRequest {
  article_id: number;
}
```

**예시 요청:**
```bash
POST /api/favorites/add
Content-Type: application/json

{
  "article_id": 123
}
```

**응답:**
```json
{
  "success": true,
  "message": "Favorite added"
}
```

#### `DELETE /api/favorites/{article_id}`
즐겨찾기에서 기사를 제거합니다.

**매개변수:**
- `article_id`: 제거할 기사 ID

**예시 요청:**
```bash
DELETE /api/favorites/123
```

**응답:**
```json
{
  "success": true,
  "message": "Favorite removed"
}
```

### 통계 정보

#### `GET /api/stats`
애플리케이션 전체 통계를 조회합니다.

**응답:**
```typescript
interface DailyCount {
  date: string;
  count: number;
}

interface Stats {
  total_articles: number;
  total_sources: number;
  total_favorites: number;
  daily_counts: DailyCount[];
}
```

**예시 응답:**
```json
{
  "total_articles": 1547,
  "total_sources": 12,
  "total_favorites": 45,
  "daily_counts": [
    {"date": "2025-08-20", "count": 23},
    {"date": "2025-08-21", "count": 31},
    {"date": "2025-08-22", "count": 28}
  ]
}
```

## ⚠️ 에러 응답

모든 API 에러는 다음 형식으로 반환됩니다:

```typescript
interface ErrorResponse {
  detail: string;
}
```

**일반적인 HTTP 상태 코드:**

- `200 OK`: 요청 성공
- `400 Bad Request`: 잘못된 요청 매개변수
- `404 Not Found`: 리소스를 찾을 수 없음
- `500 Internal Server Error`: 서버 내부 오류

**예시 에러 응답:**
```json
{
  "detail": "Article not found"
}
```

## 🚀 사용 예시

### JavaScript/TypeScript

```typescript
import axios from 'axios';

const api = axios.create({
  baseURL: 'https://streamlit-04.onrender.com',
  headers: {
    'Content-Type': 'application/json',
  },
});

// 기사 목록 조회
const articles = await api.get('/api/articles', {
  params: { limit: 10, search: 'AI' }
});

// 즐겨찾기 추가
await api.post('/api/favorites/add', {
  article_id: 123
});

// 키워드 통계 조회  
const keywordStats = await api.get('/api/keywords/stats', {
  params: { limit: 20 }
});
```

### Python

```python
import requests

base_url = "https://streamlit-04.onrender.com"

# 기사 목록 조회
response = requests.get(f"{base_url}/api/articles", params={
    "limit": 10,
    "search": "AI"
})
articles = response.json()

# 즐겨찾기 추가
response = requests.post(f"{base_url}/api/favorites/add", json={
    "article_id": 123
})

# 통계 정보 조회
response = requests.get(f"{base_url}/api/stats")
stats = response.json()
```

### cURL

```bash
# 기사 목록 조회
curl -X GET "https://streamlit-04.onrender.com/api/articles?limit=10&search=AI"

# 즐겨찾기 추가
curl -X POST "https://streamlit-04.onrender.com/api/favorites/add" \
  -H "Content-Type: application/json" \
  -d '{"article_id": 123}'

# 즐겨찾기 제거
curl -X DELETE "https://streamlit-04.onrender.com/api/favorites/123"
```

## 🔄 API 버전 관리

현재 API는 v1 버전입니다. 향후 호환성을 위해 다음과 같은 버전 관리 전략을 사용할 예정입니다:

- URL 기반 버전 관리: `/api/v1/articles`
- 헤더 기반 버전 관리: `API-Version: 1.0`
- 하위 호환성 유지를 위한 점진적 업그레이드

## 📊 API 사용량 제한

현재는 사용량 제한이 없지만, 향후 다음과 같은 제한을 적용할 예정입니다:

- **일반 요청**: 분당 100회
- **대량 데이터 요청**: 분당 10회
- **검색 요청**: 분당 50회

## 🔍 API 테스팅

OpenAPI (Swagger) 문서는 다음 URL에서 확인할 수 있습니다:
- **Swagger UI**: `https://streamlit-04.onrender.com/docs`
- **ReDoc**: `https://streamlit-04.onrender.com/redoc`

---

**다음**: [배포 가이드](../deployment/DEPLOYMENT_GUIDE.md)
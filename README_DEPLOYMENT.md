# News IT's Issue - React & FastAPI 배포 가이드

## 프로젝트 구조

```
streamlit_04/
├── backend/          # FastAPI 백엔드
│   ├── main.py
│   ├── requirements.txt
│   └── render.yaml
├── frontend/         # React 프론트엔드
│   └── news-app/
│       ├── src/
│       ├── package.json
│       └── vite.config.ts
└── news.db          # SQLite 데이터베이스
```

## 백엔드 배포 (Render.com)

### 1. GitHub 리포지토리 연결
1. Render.com 로그인
2. New > Web Service 선택
3. GitHub 리포지토리 연결

### 2. 백엔드 설정
- **Name**: news-api-backend
- **Root Directory**: backend
- **Environment**: Python 3
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

### 3. 환경 변수 설정
```
DB_PATH=/opt/render/project/src/news.db
PYTHON_VERSION=3.11.0
OPENAI_API_KEY=sk-your-api-key-here  # Render Dashboard에서 설정
```

### 4. 데이터베이스 파일 업로드
- news.db 파일을 백엔드 디렉토리에 포함
- 또는 Render의 Persistent Disk 사용

## 프론트엔드 배포

### 옵션 1: Vercel
```bash
cd frontend/news-app
npm run build
npx vercel --prod
```

### 옵션 2: Netlify
```bash
cd frontend/news-app
npm run build
# dist 폴더를 Netlify에 드래그 앤 드롭
```

### 옵션 3: Render Static Site
1. New > Static Site
2. Root Directory: `frontend/news-app`
3. Build Command: `npm install && npm run build`
4. Publish Directory: `dist`

## 로컬 개발 환경

### 백엔드 실행
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 프론트엔드 실행
```bash
cd frontend/news-app
npm install
npm run dev
```

## API 엔드포인트

- `GET /api/articles` - 기사 목록 조회
- `GET /api/sources` - 소스 목록 조회
- `GET /api/keywords/stats` - 키워드 통계
- `GET /api/keywords/network` - 키워드 네트워크
- `GET /api/favorites` - 즐겨찾기 목록
- `POST /api/favorites/add` - 즐겨찾기 추가
- `DELETE /api/favorites/{id}` - 즐겨찾기 삭제
- `GET /api/stats` - 통계 정보

## 주의사항

1. **CORS 설정**: 백엔드에서 프론트엔드 도메인 허용 필요
2. **환경 변수**: 프로덕션 환경에서는 `.env.production` 사용
3. **데이터베이스**: SQLite 파일 경로 확인 필요
4. **API URL**: 프론트엔드 config.ts에서 백엔드 URL 설정

## 문제 해결

### CORS 에러
백엔드 main.py의 CORS 미들웨어 설정 확인:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend-domain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 데이터베이스 연결 실패
- DB_PATH 환경 변수 확인
- news.db 파일 존재 여부 확인
- 파일 권한 확인

### API 연결 실패
- 백엔드 서비스 실행 상태 확인
- API URL 설정 확인 (frontend/news-app/src/config.ts)
- 네트워크 방화벽 설정 확인
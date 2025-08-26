# 배포 가이드

이 문서는 뉴스있슈 프로젝트의 배포 과정을 상세히 설명합니다.

## 🏗️ 배포 아키텍처

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  GitHub Pages   │    │   Render.com    │    │  GitHub Repo    │
│   (Frontend)    │◄───│   (Backend)     │◄───│   (Source)      │
│                 │    │                 │    │                 │
│  React SPA      │    │  FastAPI + DB   │    │  CI/CD Actions  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📦 백엔드 배포 (Render.com)

### 1. Render.com 계정 설정

1. [Render.com](https://render.com)에서 계정 생성
2. GitHub 계정과 연동
3. 저장소 접근 권한 승인

### 2. Web Service 생성

**기본 설정:**
- **Service Type**: Web Service
- **Repository**: `aebonlee/streamlit_04`
- **Branch**: `main`
- **Root Directory**: `backend`
- **Runtime**: Python 3

**빌드 설정:**
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

### 3. 환경 변수 설정

Render 대시보드에서 다음 환경 변수를 설정:

```bash
DB_PATH=/opt/render/project/src/news.db
OPENAI_API_KEY=sk-your-api-key-here
PYTHON_VERSION=3.11.0
```

### 4. 데이터베이스 초기화

첫 배포 시 데이터베이스가 자동으로 초기화됩니다:

```python
# backend/start.sh
if [ ! -f "news.db" ]; then
    echo "Initializing database..."
    python init_db.py
fi
```

### 5. 도메인 설정

배포 완료 후 제공되는 URL:
- **백엔드 API**: `https://streamlit-04.onrender.com`
- **API 문서**: `https://streamlit-04.onrender.com/docs`

## 🌐 프론트엔드 배포 (GitHub Pages)

### 1. GitHub Actions 워크플로우

프로젝트에는 자동 배포를 위한 워크플로우가 설정되어 있습니다:

```yaml
# .github/workflows/deploy.yml
name: Deploy to GitHub Pages

on:
  push:
    branches: [ main ]
  workflow_dispatch:

jobs:
  build:
    - uses: actions/setup-node@v4
      with:
        node-version: '18'
    - run: npm ci --legacy-peer-deps
    - run: npm run build
    
  deploy:
    - uses: actions/deploy-pages@v4
```

### 2. 빌드 설정

**Vite 설정 (vite.config.ts):**
```typescript
export default defineConfig({
  base: './',  // 상대 경로 사용
  build: {
    outDir: 'dist',
    sourcemap: true,
  }
});
```

**환경 변수 (.env.production):**
```bash
VITE_API_URL=https://streamlit-04.onrender.com
```

### 3. 배포 프로세스

1. **코드 푸시**: `main` 브랜치에 커밋 푸시
2. **자동 빌드**: GitHub Actions가 React 앱 빌드
3. **Pages 배포**: 빌드된 파일을 GitHub Pages에 배포
4. **URL 접근**: `https://aebonlee.github.io/streamlit_04/`

### 4. 수동 배포

필요시 수동으로 배포할 수 있습니다:

```bash
# 로컬 빌드
cd frontend/news-app
npm run build

# GitHub Pages 배포
npm install -g gh-pages
npx gh-pages -d dist
```

## 🔄 CI/CD 파이프라인

### 자동화된 배포 플로우

1. **코드 변경사항 커밋**
   ```bash
   git add .
   git commit -m "feat: new feature"
   git push origin main
   ```

2. **백엔드 자동 배포**
   - Render.com이 자동으로 감지
   - Docker 컨테이너 빌드
   - 무중단 배포 실행

3. **프론트엔드 자동 배포**
   - GitHub Actions 트리거
   - Node.js 18 환경에서 빌드
   - GitHub Pages에 정적 파일 배포

### 배포 모니터링

**백엔드 모니터링:**
- **로그**: Render 대시보드 > Logs 탭
- **메트릭스**: CPU, Memory, Response Time 모니터링
- **상태**: Health Check 엔드포인트 `/health`

**프론트엔드 모니터링:**
- **Actions**: GitHub 저장소 > Actions 탭
- **Pages**: Settings > Pages 설정에서 빌드 상태 확인

## 🚀 대안 배포 방법

### Option 1: Vercel (프론트엔드)

```bash
cd frontend/news-app
npm install -g vercel
vercel --prod
```

**vercel.json 설정:**
```json
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "env": {
    "VITE_API_URL": "https://streamlit-04.onrender.com"
  }
}
```

### Option 2: Netlify (프론트엔드)

```bash
cd frontend/news-app
npm run build
# dist 폴더를 Netlify에 드래그 앤 드롭
```

**netlify.toml 설정:**
```toml
[build]
  command = "npm run build"
  publish = "dist"

[build.environment]
  VITE_API_URL = "https://streamlit-04.onrender.com"
```

### Option 3: Docker (백엔드)

**Dockerfile:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**배포 명령:**
```bash
docker build -t news-api .
docker run -p 8000:8000 -e OPENAI_API_KEY=sk-xxx news-api
```

## 🐛 트러블슈팅

### 일반적인 배포 문제

**1. 빌드 실패**
```bash
# 의존성 충돌 해결
npm install --legacy-peer-deps

# Node.js 버전 확인
node --version  # 18.x 권장
```

**2. CORS 에러**
```python
# backend/main.py에서 CORS 설정 확인
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://aebonlee.github.io"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**3. 환경 변수 누락**
```bash
# Render.com 대시보드에서 확인
OPENAI_API_KEY=sk-...
VITE_API_URL=https://streamlit-04.onrender.com
```

**4. 데이터베이스 문제**
```python
# 데이터베이스 재초기화
python backend/init_db.py
```

### 성능 최적화

**프론트엔드 최적화:**
```typescript
// 코드 스플리팅
const LazyComponent = React.lazy(() => import('./Component'));

// 번들 크기 최적화
// vite.config.ts
build: {
  rollupOptions: {
    output: {
      manualChunks: {
        vendor: ['react', 'react-dom'],
        ui: ['@mui/material']
      }
    }
  }
}
```

**백엔드 최적화:**
```python
# 데이터베이스 연결 풀링
import sqlite3
from contextlib import contextmanager

@contextmanager
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()
```

## 📊 배포 후 체크리스트

### 기능 검증

- [ ] **프론트엔드 접속**: https://aebonlee.github.io/streamlit_04/
- [ ] **백엔드 API**: https://streamlit-04.onrender.com/docs
- [ ] **기사 목록 로딩** 정상 작동
- [ ] **검색 및 필터링** 기능 테스트
- [ ] **즐겨찾기 추가/제거** 기능 확인
- [ ] **키워드 분석** 시각화 표시
- [ ] **통계 차트** 렌더링 확인

### 성능 검증

- [ ] **페이지 로드 시간** < 3초
- [ ] **API 응답 시간** < 1초
- [ ] **모바일 반응형** 디자인 확인
- [ ] **브라우저 호환성** 테스트

### 보안 검증

- [ ] **HTTPS 통신** 확인
- [ ] **API 키** 노출 여부 점검
- [ ] **CORS 설정** 적절성 확인
- [ ] **입력 값 검증** 작동 확인

---

**다음**: [개발 워크플로우](../development/DEVELOPMENT_WORKFLOW.md)
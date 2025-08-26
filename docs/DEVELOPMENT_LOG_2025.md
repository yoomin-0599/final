# 개발 일지 - 뉴스있슈~ 프로젝트 리팩토링

## 📅 2025년 8월 26일

### 🎯 프로젝트 목표
Streamlit 기반 뉴스 수집 애플리케이션을 FastAPI + React 구조로 전환하고 Render.com 배포 문제를 해결

### 🔍 초기 문제 진단

#### 발견된 문제점들:
1. **Render 배포 실패**: https://streamlit-04.onrender.com 접속 불가 (타임아웃)
2. **뉴스 수집 기능 부재**: Backend에 실제 수집 로직이 없음
3. **아키텍처 불일치**: Streamlit 독립앱 vs FastAPI+React 분리형 구조
4. **DB 경로 문제**: `news.db` vs `backend/news.db` 불일치

### 📝 작업 내역

#### 1. **프로젝트 구조 재정리** 
```
변경 전:
- 루트에 Streamlit 파일들 혼재
- Backend와 Frontend 분리 불완전
- 중복 파일 존재

변경 후:
streamlit_04/
├── backend/       # FastAPI 서버
├── frontend/      # React 앱
├── streamlit/     # 원본 Streamlit (보관용)
└── docs/          # 문서화
```

#### 2. **Backend 개선사항**

##### `backend/news_collector.py` 신규 생성
- Streamlit `main_app.py`의 수집 로직을 백엔드용으로 포팅
- 주요 기능:
  - RSS 피드 파싱 (30개 소스)
  - 본문 텍스트 추출
  - 간단한 키워드 추출 (형태소 분석 없이)
  - SQLite DB 저장
  - 병렬 처리 지원

##### `backend/main.py` 수정
- 정적 파일 서빙 추가 (React 빌드 파일)
- DB 초기화 로직 추가
- 뉴스 수집 API 연동
- 루트 경로에서 React 앱 서빙

#### 3. **배포 설정 개선**

##### `render.yaml` 수정
```yaml
buildCommand: |
  # Backend 의존성 설치
  cd backend
  pip install -r requirements.txt
  
  # Frontend 빌드
  cd ../frontend/news-app
  npm install
  npm run build

startCommand: |
  # DB 초기화
  python -c "from news_collector import init_db; init_db()"
  # 서버 시작
  uvicorn main:app --host 0.0.0.0 --port $PORT
```

##### 환경변수 설정
- `DB_PATH`: backend/news.db (통일)
- `ENABLE_SUMMARY`: 0 (OpenAI 비활성화)
- `MAX_RESULTS`: 10
- `PARALLEL_MAX_WORKERS`: 4

#### 4. **파일 정리**
- Streamlit 관련 파일들을 `streamlit/` 폴더로 이동
- 루트 디렉토리 정리
- README.md 작성

### 🛠️ 기술적 해결책

#### 문제 1: 뉴스 수집 기능 없음
**해결**: `news_collector.py` 모듈 생성하여 백엔드에서 직접 수집

#### 문제 2: 정적 파일 서빙 안됨  
**해결**: FastAPI에 StaticFiles 미들웨어 추가
```python
app.mount("/assets", StaticFiles(directory="frontend/news-app/dist/assets"))
```

#### 문제 3: DB 경로 불일치
**해결**: 모든 설정을 `backend/news.db`로 통일

#### 문제 4: 형태소 분석 의존성
**해결**: 간단한 정규표현식 기반 토크나이저로 대체 (Kiwi 없이도 동작)

### 📊 성과

✅ **완료된 작업**:
- [x] Streamlit 파일 정리 및 보관
- [x] Backend 뉴스 수집 모듈 구현
- [x] 정적 파일 서빙 설정
- [x] DB 경로 통일
- [x] Render 배포 설정 수정
- [x] 문서화

### 🚀 배포 준비 상태

#### 로컬 테스트 명령어:
```bash
# Backend
cd backend
python -c "from news_collector import init_db, collect_all_news; init_db(); collect_all_news()"
uvicorn main:app --reload

# Frontend
cd frontend/news-app
npm install && npm run build
```

#### Render.com 배포:
- GitHub push 시 자동 배포
- 초기 DB 생성 및 뉴스 수집 자동화
- Frontend 빌드 자동화

### 📈 개선 가능 영역

1. **성능 최적화**:
   - Redis 캐싱 도입
   - 뉴스 수집 스케줄링 (cron)
   - DB 인덱싱 최적화

2. **기능 확장**:
   - OpenAI 요약 기능 활성화 (API 키 설정 시)
   - 실시간 업데이트 (WebSocket)
   - 사용자 인증 시스템

3. **모니터링**:
   - 로깅 시스템 구축
   - 에러 트래킹 (Sentry)
   - 성능 메트릭 수집

### 💡 배운 점

1. **모놀리식 → 마이크로서비스 전환의 복잡성**
   - 단순 파일 분리가 아닌 로직 재구성 필요
   - 의존성 관리의 중요성

2. **배포 환경 고려사항**
   - 로컬과 프로덕션 환경 차이
   - 환경변수 관리의 중요성
   - 빌드 프로세스 자동화 필요

3. **문서화의 중요성**
   - 코드 변경사항 추적
   - 배포 절차 명확화
   - 트러블슈팅 가이드 필요

### 🔗 관련 파일

- Backend: `backend/news_collector.py`, `backend/main.py`
- Config: `render.yaml`, `.env`, `backend/start.sh`
- Docs: `README.md`, 본 문서

---

*작성자: Claude Code Assistant*  
*날짜: 2025년 8월 26일*
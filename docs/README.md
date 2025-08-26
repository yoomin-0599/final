# 뉴스있슈~ (News IT's Issue) - 프로젝트 문서

## 📋 목차

- [프로젝트 개요](./PROJECT_OVERVIEW.md)
- [기술 아키텍처](./TECHNICAL_ARCHITECTURE.md)  
- [API 문서](./api/API_DOCUMENTATION.md)
- [배포 가이드](./deployment/DEPLOYMENT_GUIDE.md)
- [개발 워크플로우](./development/DEVELOPMENT_WORKFLOW.md)
- [변경 이력](./CHANGELOG.md)

## 🚀 빠른 시작

### 라이브 데모
- **웹사이트**: [https://aebonlee.github.io/streamlit_04/](https://aebonlee.github.io/streamlit_04/)
- **백엔드 API**: [https://streamlit-04.onrender.com](https://streamlit-04.onrender.com)

### 로컬 개발 환경 설정

#### 백엔드 (FastAPI)
```bash
cd backend
pip install -r requirements.txt
python init_db.py
uvicorn main:app --reload
```

#### 프론트엔드 (React)
```bash
cd frontend/news-app
npm install --legacy-peer-deps
npm run dev
```

## 📊 프로젝트 통계

- **개발 기간**: 2025년 8월
- **커밋 수**: 6개 주요 커밋
- **코드 라인**: 6,500+ 라인
- **파일 수**: 35개
- **기술 스택**: React 19 + TypeScript + FastAPI + SQLite

## 🛠️ 주요 기능

1. **뉴스 기사 관리**
   - 실시간 뉴스 수집 및 저장
   - 검색 및 필터링 기능
   - 소스별 분류

2. **즐겨찾기 시스템**
   - 기사 즐겨찾기 추가/제거
   - 개인화된 뉴스 큐레이션

3. **키워드 분석**
   - 동적 키워드 클라우드
   - 키워드 네트워크 시각화
   - 트렌드 분석

4. **통계 대시보드**
   - 일별 기사 수 차트
   - 소스별 통계
   - 실시간 메트릭스

## 🏗️ 아키텍처

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React Web App │───▶│   FastAPI API   │───▶│  SQLite Database│
│   (Frontend)    │    │   (Backend)     │    │   (Storage)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                        │                        │
         │                        │                        │
    GitHub Pages            Render.com                Local/Cloud
```

## 📝 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 🤝 기여

이 프로젝트는 Claude Code를 사용하여 개발되었습니다.

---

**Generated with [Claude Code](https://claude.ai/code)**
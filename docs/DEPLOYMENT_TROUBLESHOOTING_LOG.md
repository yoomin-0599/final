# 배포 문제 해결 로그

## 문제 상황
2025년 8월 27일, 프론트엔드에서 뉴스 데이터가 표시되지 않는 문제 발생

## 문제 진단 과정

### 1. 초기 증상 확인
**증상**: 
- 프론트엔드 페이지에서 뉴스 목록이 비어있음
- API 호출은 성공하지만 빈 배열 반환
- 로컬에서는 데이터베이스에 1493개 기사 존재 확인

**사용자 피드백**:
> "깃 페이지에서 정상적으로 동작되길 바래"
> "PostgresDB 사용해서 해결해주면 안되니?"

### 2. 문제 원인 분석

#### 2.1 데이터베이스 연결 문제
```bash
sqlite3.OperationalError: unable to open database file
```

**원인**:
- 로컬 환경과 배포 환경의 파일 경로 차이
- SQLite 파일의 절대/상대 경로 혼재
- 백엔드 서버 시작 시 DB 파일을 찾지 못함

#### 2.2 배포 환경 호환성 문제
```bash
pip._vendor.pyproject_hooks._impl.BackendUnavailable: Cannot import 'setuptools.build_meta'
```

**원인**:
- Python 3.13 환경에서 setuptools 버전 호환성 문제
- Render 환경의 Python 버전 불일치

#### 2.3 프로젝트 구조 혼재
**문제점**:
- 루트 디렉토리에 streamlit, backend 파일 혼재
- 중복 파일들로 인한 혼란
- 명확하지 않은 디렉토리 구조

## 해결 과정

### 단계 1: 즉시 조치
1. **에러 로그 분석**
   - 백엔드 서버 시작 실패 확인
   - SQLite 파일 경로 문제 식별

2. **Render 서버 상태 확인**
   ```bash
   curl -s https://streamlit-04.onrender.com/api/articles
   # 타임아웃 - 서버 응답 없음
   ```

### 단계 2: 근본 원인 해결
1. **데이터베이스 시스템 개선**
   - PostgreSQL 지원 추가
   - SQLite fallback 구현
   - 통합 데이터베이스 추상화 레이어 구축

2. **배포 설정 최적화**
   - Python 3.11 런타임 강제
   - setuptools 버전 업그레이드
   - Render 배포 설정 개선

3. **프로젝트 구조 정리**
   - streamlit 파일들을 `streamlit_app/` 디렉토리로 이동
   - 중복 파일 제거
   - 불필요한 임시 파일 정리

## 구현된 해결책

### 1. 데이터베이스 추상화 시스템
```python
class DatabaseConnection:
    def get_connection(self):
        """Get database connection based on configuration"""
        if self.database_url and POSTGRES_AVAILABLE:
            return self._get_postgres_connection()
        else:
            return self._get_sqlite_connection()
```

**장점**:
- 환경에 따른 자동 데이터베이스 선택
- 프로덕션에서 PostgreSQL, 개발에서 SQLite 사용
- 배포 환경 변경 시에도 안정적 동작

### 2. 배포 설정 강화
**render.yaml 최적화**:
```yaml
runtime: python-3.11
buildCommand: "pip install --upgrade pip setuptools wheel && pip install -r requirements.txt"
databases:
  - name: news-postgres
    databaseName: newsdb
    user: newsuser
```

**의존성 업데이트**:
- setuptools>=75.0.0 (Python 3.13 호환)
- psycopg2-binary==2.9.9 (PostgreSQL 지원)

### 3. 환경 변수 설정
```bash
DB_TYPE=postgres
DATABASE_URL=${DATABASE_URL}  # Render에서 자동 설정
SQLITE_PATH=/opt/render/project/src/news.db  # fallback용
```

## 테스트 및 검증

### 1. 로컬 테스트
- [x] SQLite 데이터베이스 연결 확인
- [x] 뉴스 수집 기능 (1493건 수집 성공)
- [x] API 엔드포인트 동작 확인

### 2. 배포 준비
- [x] PostgreSQL 설정 추가
- [x] 환경변수 구성
- [x] 빌드 명령 최적화

## 모니터링 및 예방 조치

### 1. 배포 후 체크리스트
- [ ] Render 서버 정상 시작 확인
- [ ] PostgreSQL 데이터베이스 연결 확인
- [ ] API 엔드포인트 응답 테스트
- [ ] 뉴스 수집 기능 동작 확인
- [ ] 프론트엔드 데이터 표시 확인

### 2. 모니터링 포인트
- 데이터베이스 연결 상태
- API 응답 시간
- 뉴스 수집 성공률
- 에러 로그 패턴

### 3. 예방 조치
- 정기적인 health check 엔드포인트
- 데이터베이스 백업 전략
- 로그 모니터링 시스템
- 자동화된 테스트 스위트

## 학습한 점

### 1. 환경 차이 관리의 중요성
- 로컬과 프로덕션 환경의 차이점을 사전에 고려해야 함
- 환경변수와 설정 파일을 통한 환경별 설정 관리 필요

### 2. 데이터베이스 선택의 전략적 접근
- 개발 환경에서는 SQLite의 간편함 활용
- 프로덕션에서는 PostgreSQL의 안정성과 성능 활용
- 추상화 레이어를 통한 유연한 전환 가능

### 3. 배포 자동화의 필요성
- 수동 배포 과정에서 발생할 수 있는 실수 최소화
- 일관된 배포 프로세스 확립
- 롤백 계획 사전 준비

## 향후 개선 계획

### 1. 단기 계획 (1-2주)
- Render 배포 후 안정성 모니터링
- PostgreSQL 데이터베이스 최적화
- API 응답 시간 개선

### 2. 중기 계획 (1-2개월)
- CI/CD 파이프라인 구축
- 자동화된 테스트 도입
- 모니터링 시스템 구축

### 3. 장기 계획 (3-6개월)
- 마이크로서비스 아키텍처 검토
- 컨테이너화 (Docker) 적용
- 스케일링 전략 수립

## 결론
이번 문제 해결 과정을 통해 시스템의 안정성과 확장성을 크게 개선했습니다. 
특히 사용자의 요구사항인 "깃 페이지에서의 정상 동작"을 위해 PostgreSQL 도입과 
배포 최적화를 통해 프로덕션 환경에서의 안정적인 서비스 제공 기반을 마련했습니다.
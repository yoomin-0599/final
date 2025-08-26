#!/bin/bash

# Backend 시작 스크립트
echo "🚀 Starting News Backend..."

# DB 초기화 (news_collector 모듈 사용)
echo "📊 Initializing database..."
python -c "from news_collector import init_db; init_db(); print('✅ Database initialized')"

# 초기 뉴스 수집 (선택적)
if [ "$COLLECT_ON_STARTUP" = "1" ]; then
    echo "📰 Collecting initial news..."
    python -c "from news_collector import collect_all_news; collect_all_news(); print('✅ Initial news collected')"
fi

# FastAPI 서버 시작
echo "🌐 Starting FastAPI server..."
exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
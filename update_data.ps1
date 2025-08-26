# update_data.ps1 — 지난 1년 수집 → DB 반입 (인코딩/한글 경로 안전 버전)
$ErrorActionPreference = "Stop"

# Python 경로: PATH에 python이 잡혀 있으면 그냥 "python"
# 특정 버전 고정이 필요하면 다음 라인을 주석 해제하고 사용:
# $PY = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'
$PY = "python"

# 바탕 화면\app 경로를 .NET에서 안전하게 얻기
$Desktop = [Environment]::GetFolderPath('Desktop')
$APPDIR  = Join-Path $Desktop 'app'
$JSONL   = Join-Path $APPDIR 'archive_last_year.jsonl'
$DB      = Join-Path $APPDIR 'news.db'

Write-Host "APPDIR:" $APPDIR
Write-Host "Python :" $PY

# 폴더 이동
Set-Location $APPDIR

Write-Host "▶ (1/2) 지난 1년 아카이브 수집 중..."
& $PY ".\archive_last_year.py" --days 365 --max-pages 12 --max-results 50 --out $JSONL

Write-Host "▶ (2/2) JSONL → DB 임포트 중..."
& $PY ".\import_jsonl_to_db.py" --jsonl $JSONL --db $DB

Write-Host "`n[완료] 데이터 갱신 끝! 이제 app.1.py만 실행하세요."

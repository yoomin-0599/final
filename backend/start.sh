#!/bin/bash

# Initialize database if it doesn't exist
if [ ! -f "news.db" ]; then
    echo "Initializing database..."
    python init_db.py
else
    echo "Database exists, skipping initialization..."
fi

# Start the FastAPI server
echo "Starting FastAPI server..."
exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
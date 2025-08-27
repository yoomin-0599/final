"""
WSGI module for your_application package
This provides the exact interface that Render expects: your_application.wsgi
"""

import sys
import os

# Add backend directory to Python path
backend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backend')
sys.path.insert(0, backend_path)

# Import FastAPI app from backend
from main import app

# WSGI application interface for gunicorn
application = app
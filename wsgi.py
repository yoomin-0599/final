"""
WSGI module - Alternative entry point for Render
This provides the WSGI interface that Render may look for.
"""

# Import the FastAPI app from backend
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from main import app

# WSGI application for gunicorn
application = app
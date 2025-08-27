"""
your_application module - Required by Render's auto-detection
This file provides the WSGI interface that Render expects.
"""

# Import the FastAPI app from backend
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from main import app

# WSGI application for gunicorn
application = app
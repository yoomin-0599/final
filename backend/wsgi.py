"""
WSGI config for FastAPI application.
This is a temporary workaround for Render's Django auto-detection.
"""

from main import app

# For gunicorn compatibility
application = app
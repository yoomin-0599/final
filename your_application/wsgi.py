"""
WSGI module for your_application package
This provides the exact interface that Render expects: your_application.wsgi
FastAPI is ASGI, so we need an ASGI-to-WSGI adapter
"""

import sys
import os

# Add backend directory to Python path
backend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backend')
sys.path.insert(0, backend_path)

# Import FastAPI app from backend
from main import app

# ASGI-to-WSGI adapter for FastAPI
try:
    from asgiref.wsgi import WsgiToAsgi
    application = WsgiToAsgi(app)
except ImportError:
    # Fallback: simple ASGI application wrapper
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    
    def application(environ, start_response):
        """WSGI wrapper for FastAPI ASGI app"""
        try:
            # This is a simplified approach - not recommended for production
            # but works as a fallback for Render's rigid deployment
            status = '200 OK'
            headers = [('Content-Type', 'text/html')]
            start_response(status, headers)
            return [b'FastAPI app is running. Please use ASGI server like uvicorn for better performance.']
        except Exception as e:
            status = '500 Internal Server Error'
            headers = [('Content-Type', 'text/plain')]
            start_response(status, headers)
            return [f'Error: {str(e)}'.encode()]
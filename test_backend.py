#!/usr/bin/env python3
"""
Test script to verify backend functionality before deployment
"""

import requests
import json
import time

def test_backend():
    # Test local backend (would be similar to production)
    base_url = "http://localhost:8000"
    
    print("🚀 Testing backend functionality...")
    
    # Start the backend server in the background (would be done differently in production)
    import subprocess
    import os
    
    # Change to backend directory
    backend_dir = "/workspaces/streamlit_04/backend"
    os.chdir(backend_dir)
    
    print("📍 Starting FastAPI server...")
    process = subprocess.Popen([
        "python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Wait a bit for server to start
    time.sleep(3)
    
    try:
        # Test basic endpoint
        print("📡 Testing root endpoint...")
        response = requests.get(f"{base_url}/", timeout=5)
        print(f"Root endpoint status: {response.status_code}")
        
        # Test articles endpoint
        print("📰 Testing articles endpoint...")
        response = requests.get(f"{base_url}/api/articles", timeout=10)
        print(f"Articles endpoint status: {response.status_code}")
        if response.status_code == 200:
            articles = response.json()
            print(f"Articles count: {len(articles)}")
        
        # Test news collection endpoint
        print("🔄 Testing news collection...")
        response = requests.post(f"{base_url}/api/collect-news-now", 
                               json={}, 
                               timeout=30)
        print(f"News collection status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Collection result: {result}")
        else:
            print(f"Collection error: {response.text}")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
    
    finally:
        # Clean up
        process.terminate()
        process.wait()

if __name__ == "__main__":
    test_backend()
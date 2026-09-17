# api/index.py
"""
Serverless entrypoint for Vercel deployment.
Exports the FastAPI app instance for serverless request routing.
"""
import os
import sys
from pathlib import Path

# Add workspace root to Python module search path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Ensure database directory exists in /tmp when running on Vercel serverless
if os.getenv("VERCEL"):
    os.environ["DB_PATH"] = "/tmp/job_hunter.db"

from src.server.app import app

"""Root entry point for the FastAPI CLI / FastAPI Cloud.

The application lives in ``backend/app/main.py``; FastAPI Cloud (like ``fastapi
run``) auto-detects an ``app`` object in a top-level ``main.py``, so this re-exports it.
"""

from backend.app.main import app

__all__ = ["app"]

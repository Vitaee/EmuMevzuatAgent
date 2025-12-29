"""
Mevzuat AI - FastAPI Application

This is a thin wrapper that imports the actual app from app.main.
Run with: uvicorn main:app --reload

Or directly: uvicorn app.main:app --reload
"""

from app.main import app

__all__ = ["app"]
import os
import sys

# Ensure the project root is importable so `app` package resolves on Vercel.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app  # noqa: E402

# Vercel's Python runtime serves this ASGI `app` object directly.

"""ASGI entry point. Run with ``uvicorn api.main:app --reload``."""

from api.app import create_app


app = create_app()

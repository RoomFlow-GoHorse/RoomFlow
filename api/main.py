"""ASGI entry point. Run with ``uvicorn api.main:app --reload``."""

from dotenv import load_dotenv

from api.app import create_app

load_dotenv()
app = create_app()

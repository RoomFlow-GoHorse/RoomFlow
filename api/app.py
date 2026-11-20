import os

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.errors import (
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from controllers.http.health import router as health_router
from controllers.http.spaces import router as spaces_router
from application.ports.space_repository import SpaceRepository
from infrastructure.repositories.in_memory_space_repository import (
    InMemorySpaceRepository,
)


def create_app(
    space_repository: SpaceRepository | None = None,
    environment: str | None = None,
) -> FastAPI:
    """Build the API; ``APP_ENV`` defaults to production and hides demo routes."""
    app = FastAPI(title="RoomFlow API", version="0.1.0")
    active_environment = (
        environment or os.getenv("APP_ENV", "production")
    ).strip().lower()
    app.state.space_repository = (
        space_repository
        if space_repository is not None
        else InMemorySpaceRepository()
    )
    app.state.environment = active_environment
    app.include_router(health_router)
    if active_environment in {"development", "test"}:
        app.include_router(spaces_router)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
    return app

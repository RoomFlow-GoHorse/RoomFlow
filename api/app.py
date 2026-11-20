from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.errors import (
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from api.routes.health import router as health_router
from api.routes.spaces import router as spaces_router
from application.ports.space_repository import SpaceRepository
from infrastructure.repositories.in_memory_space_repository import (
    InMemorySpaceRepository,
)


def create_app(space_repository: SpaceRepository | None = None) -> FastAPI:
    """Build the API and inject its repository implementation."""
    app = FastAPI(title="RoomFlow API", version="0.1.0")
    app.state.space_repository = (
        space_repository
        if space_repository is not None
        else InMemorySpaceRepository()
    )
    app.include_router(health_router)
    app.include_router(spaces_router)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
    return app

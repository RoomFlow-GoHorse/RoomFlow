import os

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.errors import (
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from application.services.authentication_service import AuthenticationService
from controllers.http.auth import router as auth_router
from controllers.http.admin_users import router as admin_users_router
from controllers.http.health import router as health_router
from controllers.http.institutions import router as institutions_router
from controllers.http.institution_invite_codes import router as invite_code_router
from controllers.http.enrollments import router as enrollments_router
from controllers.http.member_signup import router as member_signup_router
from controllers.http.spaces import router as spaces_router
from application.ports.space_repository import SpaceRepository
from infrastructure.repositories.in_memory_space_repository import (
    InMemorySpaceRepository,
)
from infrastructure.authentication_factory import build_application_runtime


def create_app(
    space_repository: SpaceRepository | None = None,
    environment: str | None = None,
    authentication_service: AuthenticationService | None = None,
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
    runtime = build_application_runtime(active_environment)
    app.state.authentication_service = authentication_service or runtime.authentication
    app.state.user_repository = runtime.users
    app.state.institution_repository = runtime.institutions
    app.state.user_management_service = runtime.user_management
    app.state.institution_management_service = runtime.institution_management
    app.state.institution_invite_code_service = runtime.invite_codes
    app.state.authorized_enrollment_repository = runtime.authorized_enrollments
    app.state.enrollment_management_service = runtime.enrollment_management
    app.include_router(health_router)
    app.include_router(auth_router)
    if active_environment in {"development", "test"}:
        app.include_router(spaces_router)
        app.include_router(admin_users_router)
        app.include_router(institutions_router)
        app.include_router(invite_code_router)
        app.include_router(enrollments_router)
        app.include_router(member_signup_router)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
    return app

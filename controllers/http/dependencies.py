from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from application.services.authentication_service import (
    AuthenticationService,
    InvalidSession,
)
from application.services.space_service import SpaceService
from models.domain.entities.user import User


bearer_scheme = HTTPBearer(auto_error=False)


def get_space_service(request: Request) -> SpaceService:
    return SpaceService(repository=request.app.state.space_repository)


def get_authentication_service(request: Request) -> AuthenticationService:
    return request.app.state.authentication_service


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    service: AuthenticationService = Depends(get_authentication_service),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Autenticação necessária.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return service.authenticate(credentials.credentials)
    except InvalidSession:
        raise HTTPException(
            status_code=401,
            detail="Sessão inválida ou expirada.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

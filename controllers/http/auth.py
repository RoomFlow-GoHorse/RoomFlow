from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, ConfigDict, Field

from application.services.authentication_service import (
    AuthenticationService,
    InvalidCredentials,
    InvalidSession,
    TooManyLoginAttempts,
)
from controllers.http.dependencies import (
    bearer_scheme,
    get_authentication_service,
    get_current_user,
)
from models.domain.entities.profile import Profile
from models.domain.entities.user import User


router = APIRouter(prefix="/auth", tags=["authentication"])


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=1024)


class AuthenticatedUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    email: str
    profile: Profile
    institution_id: str | None


class LoginData(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: AuthenticatedUserResponse


class LoginResponse(BaseModel):
    data: LoginData


class UserResponse(BaseModel):
    data: AuthenticatedUserResponse


class LogoutResponse(BaseModel):
    data: dict[str, str]


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    request: Request,
    service: AuthenticationService = Depends(get_authentication_service),
) -> LoginResponse:
    attempt_key = request.client.host if request.client else "local"
    try:
        result = service.login(payload.email, payload.password, attempt_key)
    except InvalidCredentials:
        raise HTTPException(status_code=401, detail="E-mail ou senha incorretos.") from None
    except TooManyLoginAttempts:
        raise HTTPException(
            status_code=429,
            detail="Muitas tentativas de login. Aguarde um minuto e tente novamente.",
            headers={"Retry-After": "60"},
        ) from None
    return LoginResponse(data=LoginData(
        access_token=result.access_token,
        expires_at=result.expires_at,
        user=_user_response(result.user),
    ))


@router.get("/me", response_model=UserResponse)
def identify(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse(data=_user_response(current_user))


@router.post("/logout", response_model=LogoutResponse)
def logout(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    service: AuthenticationService = Depends(get_authentication_service),
    current_user: User = Depends(get_current_user),
) -> LogoutResponse:
    del current_user
    if credentials is None:
        raise HTTPException(status_code=401, detail="Autenticação necessária.")
    try:
        service.logout(credentials.credentials)
    except InvalidSession:
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada.") from None
    return LogoutResponse(data={"status": "logged_out"})


def _user_response(user: User) -> AuthenticatedUserResponse:
    return AuthenticatedUserResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        profile=user.profile,
        institution_id=user.institution_id,
    )

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, ConfigDict, Field

from application.services.authentication_service import (
    AuthenticationService,
    InstitutionSelectionRequired,
    InvalidCredentials,
    InvalidSession,
    TooManyLoginAttempts,
)
from application.services.user_management_service import UserManagementService
from controllers.http.dependencies import (
    bearer_scheme,
    get_authentication_service,
    get_current_user,
    get_user_management_service,
)
from models.domain.entities.profile import Profile
from models.domain.entities.user import User
from models.domain.exceptions import DomainAuthorizationError, DuplicateResource, ResourceNotFound


router = APIRouter(prefix="/auth", tags=["authentication"])


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=1024)
    institution_id: str | None = Field(default=None, max_length=100)


class AuthenticatedUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    email: str
    profile: Profile
    institution_id: str | None
    phone: str | None = None


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


class AccountUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    email: str = Field(min_length=5, max_length=255)
    phone: str | None = Field(default=None, max_length=20)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=1024)
    new_password: str = Field(min_length=8, max_length=1024)


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    request: Request,
    service: AuthenticationService = Depends(get_authentication_service),
) -> LoginResponse | JSONResponse:
    attempt_key = request.client.host if request.client else "local"
    try:
        result = service.login(payload.email, payload.password, attempt_key, payload.institution_id)
    except InstitutionSelectionRequired as exc:
        return JSONResponse(status_code=409, content={
            "error": {
                "code": "institution_selection_required",
                "message": "Selecione a instituição para acessar.",
                "details": [{"institution_id": item} for item in exc.institution_ids],
            }
        })
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


@router.patch("/me", response_model=UserResponse)
def update_account(
    payload: AccountUpdateRequest,
    actor: User = Depends(get_current_user),
    service: UserManagementService = Depends(get_user_management_service),
) -> UserResponse:
    try:
        user = service.update_own_profile(actor, payload.name, payload.email, payload.phone)
    except DomainAuthorizationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from None
    except DuplicateResource as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    except ResourceNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return UserResponse(data=_user_response(user))


@router.post("/password", response_model=LogoutResponse)
def change_password(
    payload: PasswordChangeRequest,
    actor: User = Depends(get_current_user),
    service: AuthenticationService = Depends(get_authentication_service),
) -> LogoutResponse:
    try:
        service.change_password(actor.id, payload.current_password, payload.new_password, actor.institution_id)
    except InvalidCredentials:
        raise HTTPException(status_code=401, detail="A senha atual está incorreta.") from None
    return LogoutResponse(data={"status": "password_changed"})


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
        phone=user.phone,
    )

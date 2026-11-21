from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from application.services.user_management_service import UserManagementService
from controllers.http.dependencies import get_current_user, get_user_management_service
from models.domain.entities.profile import Profile
from models.domain.entities.user import User, UserStatus
from models.domain.exceptions import (
    DomainAuthorizationError,
    DuplicateResource,
    LastActiveAdministrator,
    ResourceNotFound,
)


router = APIRouter(prefix="/admin/users", tags=["user administration"])


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    profile: Profile
    institution_id: str | None
    status: UserStatus


class UserListResponse(BaseModel):
    data: list[UserResponse]


class SingleUserResponse(BaseModel):
    data: UserResponse


class CreateUserRequest(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    email: str = Field(min_length=5, max_length=255, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=8, max_length=1024)
    profile: Profile = Profile.REQUESTER


class UpdateUserRequest(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    email: str = Field(min_length=5, max_length=255)


class UpdateProfileRequest(BaseModel):
    profile: Profile


class UpdateStatusRequest(BaseModel):
    status: UserStatus


@router.get("", response_model=UserListResponse)
def list_users(
    q: str = Query(default="", max_length=150),
    institution_id: str | None = Query(default=None, max_length=100),
    actor: User = Depends(get_current_user),
    service: UserManagementService = Depends(get_user_management_service),
) -> UserListResponse:
    try:
        users = service.list_users(actor, q, institution_id)
    except DomainAuthorizationError as exc:
        _raise_http_error(403, str(exc))
    return UserListResponse(data=[_user_response(user) for user in users])


@router.post("", response_model=SingleUserResponse, status_code=201)
def create_user(
    payload: CreateUserRequest,
    actor: User = Depends(get_current_user),
    service: UserManagementService = Depends(get_user_management_service),
) -> SingleUserResponse:
    try:
        user = service.create_user(
            actor, payload.name, payload.email, payload.password, payload.profile
        )
    except DomainAuthorizationError as exc:
        _raise_http_error(403, str(exc))
    except DuplicateResource as exc:
        _raise_http_error(409, str(exc))
    except ValueError as exc:
        _raise_http_error(422, str(exc))
    return SingleUserResponse(data=_user_response(user))


@router.get("/{user_id}", response_model=SingleUserResponse)
def get_user(
    user_id: str,
    actor: User = Depends(get_current_user),
    service: UserManagementService = Depends(get_user_management_service),
) -> SingleUserResponse:
    try:
        user = service.get_user(actor, user_id)
    except DomainAuthorizationError as exc:
        _raise_http_error(403, str(exc))
    except ResourceNotFound as exc:
        _raise_http_error(404, str(exc))
    return SingleUserResponse(data=_user_response(user))


@router.patch("/{user_id}", response_model=SingleUserResponse)
def update_user(
    user_id: str,
    payload: UpdateUserRequest,
    actor: User = Depends(get_current_user),
    service: UserManagementService = Depends(get_user_management_service),
) -> SingleUserResponse:
    try:
        user = service.update_user(actor, user_id, payload.name, payload.email)
    except DomainAuthorizationError as exc:
        _raise_http_error(403, str(exc))
    except ResourceNotFound as exc:
        _raise_http_error(404, str(exc))
    except DuplicateResource as exc:
        _raise_http_error(409, str(exc))
    except ValueError as exc:
        _raise_http_error(422, str(exc))
    return SingleUserResponse(data=_user_response(user))


@router.patch("/{user_id}/profile", response_model=SingleUserResponse)
def update_profile(
    user_id: str,
    payload: UpdateProfileRequest,
    actor: User = Depends(get_current_user),
    service: UserManagementService = Depends(get_user_management_service),
) -> SingleUserResponse:
    try:
        user = service.update_profile(actor, user_id, payload.profile)
    except DomainAuthorizationError as exc:
        _raise_http_error(403, str(exc))
    except ResourceNotFound as exc:
        _raise_http_error(404, str(exc))
    except LastActiveAdministrator as exc:
        _raise_http_error(409, str(exc))
    return SingleUserResponse(data=_user_response(user))


@router.patch("/{user_id}/status", response_model=SingleUserResponse)
def update_status(
    user_id: str,
    payload: UpdateStatusRequest,
    actor: User = Depends(get_current_user),
    service: UserManagementService = Depends(get_user_management_service),
) -> SingleUserResponse:
    try:
        user = service.set_status(actor, user_id, payload.status)
    except DomainAuthorizationError as exc:
        _raise_http_error(403, str(exc))
    except ResourceNotFound as exc:
        _raise_http_error(404, str(exc))
    except LastActiveAdministrator as exc:
        _raise_http_error(409, str(exc))
    return SingleUserResponse(data=_user_response(user))


def _user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        profile=user.profile,
        institution_id=user.institution_id,
        status=user.status,
    )


def _raise_http_error(status_code: int, message: str) -> None:
    raise HTTPException(status_code=status_code, detail=message)

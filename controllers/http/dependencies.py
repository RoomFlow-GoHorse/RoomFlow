from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from application.services.authentication_service import (
    AuthenticationService,
    InvalidSession,
)
from application.services.enrollment_management_service import EnrollmentManagementService
from application.services.institution_invite_code_service import InstitutionInviteCodeService
from application.services.institution_management_service import InstitutionManagementService
from application.services.space_service import SpaceService
from application.services.resource_management_service import ResourceManagementService
from application.services.floor_plan_service import FloorPlanService
from application.services.user_management_service import UserManagementService
from application.services.member_signup_service import MemberSignupService
from models.domain.entities.user import User


bearer_scheme = HTTPBearer(auto_error=False)


def get_space_service(request: Request) -> SpaceService:
    return request.app.state.space_query_service


def get_space_management_service(request: Request) -> SpaceService:
    return request.app.state.space_management_service


def get_resource_management_service(request: Request) -> ResourceManagementService:
    return request.app.state.resource_management_service


def get_floor_plan_management_service(request: Request) -> FloorPlanService:
    return request.app.state.floor_plan_management_service


def get_authentication_service(request: Request) -> AuthenticationService:
    return request.app.state.authentication_service


def get_user_management_service(request: Request) -> UserManagementService:
    return request.app.state.user_management_service


def get_institution_management_service(request: Request) -> InstitutionManagementService:
    return request.app.state.institution_management_service


def get_institution_invite_code_service(request: Request) -> InstitutionInviteCodeService:
    return request.app.state.institution_invite_code_service


def get_enrollment_management_service(request: Request) -> EnrollmentManagementService:
    return request.app.state.enrollment_management_service


def get_member_signup_service(request: Request) -> MemberSignupService:
    return request.app.state.member_signup_service


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

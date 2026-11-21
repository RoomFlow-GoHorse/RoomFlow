from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime
from urllib.parse import quote, urlsplit

import httpx2

from application.services.authentication_service import (
    InstitutionSelectionRequired, InvalidCredentials, InvalidSession, LoginResult, TooManyLoginAttempts,
)
from application.services.institution_invite_code_service import InvitationCodeStatus
from application.services.enrollment_management_service import (
    EnrollmentImportPreview, ImportRowResult, MemberIdentityNotConfirmed, TooManyEnrollmentAttempts,
)
from application.services.member_signup_service import InvalidEmailVerification, MemberSignupStarted, RegisteredMember
from application.services.password_recovery_service import InvalidRecoveryToken
from controllers.structure_api import ApiAdminDashboard, ApiFloorPlans, ApiResourceManagement, ApiSpaceManagement
from controllers.reservation_api import ApiReservations
from controllers.conflict_api import ApiConflicts
from controllers.manager_operations_api import ApiManagerOperations
from controllers.notification_api import ApiNotifications
from models.domain.entities.admin_audit_event import AdminAuditAction, AdminAuditEvent
from models.domain.entities.authorized_enrollment import AuthorizedEnrollment
from models.domain.entities.institution import (
    ConflictPreferences, Institution, InstitutionPreferences,
    NotificationPreferences, ReservationPreferences,
)
from models.domain.entities.user import User
from models.domain.exceptions import (
    DomainAuthorizationError, DuplicateResource, LastActiveAdministrator, ResourceNotFound,
)


class ApiUnavailable(DomainAuthorizationError):
    pass


class ApiTimeout(ApiUnavailable):
    pass


class ApiResponseError(ApiUnavailable):
    pass


class ApiSessionExpired(InvalidSession, DomainAuthorizationError):
    pass


class RoomFlowApi:
    def __init__(self, base_url: str, token: Callable[[], str | None]):
        try:
            url = urlsplit(base_url)
            valid = (
                url.scheme in {"http", "https"} and bool(url.hostname)
                and url.username is None and url.password is None
                and not url.query and not url.fragment
                and url.port != 0
            )
        except ValueError:
            valid = False
        if not valid:
            raise ApiUnavailable("Configure ROOMFLOW_API_URL com um endereço HTTP ou HTTPS válido da API.")
        self._client = httpx2.Client(base_url=base_url, timeout=6.0, trust_env=False)
        self._token = token

    def request(
        self, method, path, *, payload=None, params=None, token=None, authenticated=True,
        conflict=DuplicateResource, bad_request=ValueError, rate_error=TooManyLoginAttempts,
        files=None, binary=False, enveloped=True,
    ):
        credential = (token or self._token()) if authenticated else None
        headers = {"Authorization": f"Bearer {credential}"} if credential else {}
        try:
            response = self._client.request(method, path, json=payload, params=params, headers=headers, files=files)
        except httpx2.TimeoutException:
            raise ApiTimeout("A API do RoomFlow demorou para responder. Tente novamente.") from None
        except httpx2.RequestError:
            raise ApiUnavailable(
                "Não foi possível conectar à API do RoomFlow. Verifique se o FastAPI está rodando e confira ROOMFLOW_API_URL."
            ) from None
        if response.status_code == 204:
            return None
        if response.is_success and binary:
            return response.content
        unexpected = f"Resposta inesperada da API do RoomFlow (HTTP {response.status_code}). Confira ROOMFLOW_API_URL."
        try:
            body = response.json()
        except ValueError:
            raise ApiResponseError(unexpected) from None
        if not isinstance(body, dict):
            raise ApiResponseError(unexpected)
        if response.is_success:
            if enveloped and "data" not in body:
                raise ApiResponseError(unexpected)
            return body["data"] if enveloped else body
        error = body.get("error")
        if not isinstance(error, dict):
            raise ApiResponseError(unexpected)
        message = error.get("message", "A solicitação não pode ser concluída.")
        if error.get("code") == "institution_selection_required":
            raise InstitutionSelectionRequired(tuple(item["institution_id"] for item in error["details"]))
        if response.status_code == 401:
            raise ApiSessionExpired(message)
        if response.status_code == 429:
            raise rate_error(message)
        if response.status_code == 409:
            raise conflict(message)
        if response.status_code == 400:
            raise bad_request(message)
        if response.status_code == 422:
            raise ValueError(message)
        if response.status_code == 404:
            raise ResourceNotFound(message)
        if response.status_code == 403:
            raise DomainAuthorizationError(message)
        if response.status_code == 503:
            raise ApiResponseError(f"{message} (HTTP 503)")
        raise ApiResponseError(f"A API do RoomFlow retornou um erro (HTTP {response.status_code}). Consulte o terminal do FastAPI.")


class ApiAuthentication:
    def __init__(self, api: RoomFlowApi):
        self._api = api

    def login(self, email, password, attempt_key="local", institution_id=None):
        del attempt_key
        try:
            data = self._api.request("POST", "/auth/login", authenticated=False, payload={
                "email": email, "password": password, "institution_id": institution_id,
            })
        except InvalidSession:
            raise InvalidCredentials from None
        return LoginResult(data["access_token"], datetime.fromisoformat(data["expires_at"]), User(**data["user"]))

    def authenticate(self, token):
        return User(**self._api.request("GET", "/auth/me", token=token))

    def logout(self, token):
        self._api.request("POST", "/auth/logout", token=token)

    def change_password(self, user_id, current_password, new_password):
        del user_id
        try:
            self._api.request("POST", "/auth/password", payload={
                "current_password": current_password, "new_password": new_password,
            })
        except InvalidSession:
            raise InvalidCredentials from None


class ApiUserManagement:
    def __init__(self, api: RoomFlowApi):
        self._api = api

    def list_users(self, actor, query=""):
        return [User(**item) for item in self._api.request("GET", "/admin/users", params={"q": query})]

    def create_user(self, actor, name, email, password, profile):
        return User(**self._api.request("POST", "/admin/users", payload={
            "name": name, "email": email, "password": password, "profile": profile.value,
        }))

    def update_user(self, actor, user_id, name, email):
        return User(**self._api.request("PATCH", f"/admin/users/{quote(user_id, safe='')}", payload={
            "name": name, "email": email,
        }))

    def update_profile(self, actor, user_id, profile):
        return User(**self._api.request("PATCH", f"/admin/users/{quote(user_id, safe='')}/profile",
            payload={"profile": profile.value}, conflict=LastActiveAdministrator))

    def set_status(self, actor, user_id, status):
        return User(**self._api.request("PATCH", f"/admin/users/{quote(user_id, safe='')}/status",
            payload={"status": status.value}, conflict=LastActiveAdministrator))

    def update_own_profile(self, actor, name, email, phone=None):
        return User(**self._api.request("PATCH", "/auth/me", payload={"name": name, "email": email, "phone": phone}))


class ApiInstitutionManagement:
    def __init__(self, api: RoomFlowApi):
        self._api = api

    def get_own(self, actor):
        return self._institution(self._api.request("GET", "/institutions/me"))

    def register(self, registration):
        data = self._api.request("POST", "/institutions/signup", authenticated=False, payload=asdict(registration))
        institution = self._institution(data["institution"])
        owner = User(**data["administrator"], institution_id=institution.id)
        return institution, owner, data["invitation_code"]

    def update_own(self, actor, update):
        return self._institution(self._api.request("PATCH", "/institutions/me", payload=asdict(update)))

    @staticmethod
    def _institution(data):
        preferences = data["preferences"]
        return Institution(**{
            **data, "preferences": InstitutionPreferences(
                reservations=ReservationPreferences(**preferences["reservations"]),
                conflicts=ConflictPreferences(**preferences["conflicts"]),
                notifications=NotificationPreferences(**preferences["notifications"]),
            ),
        })


class ApiAdminAudit:
    def __init__(self, api: RoomFlowApi):
        self._api = api

    def list_events(self, actor, *, start_at, end_at, action, actor_user_id, limit):
        params = {"limit": limit}
        if start_at:
            params["start_at"] = start_at.isoformat()
        if end_at:
            params["end_at"] = end_at.isoformat()
        if action:
            params["action"] = action.value
        if actor_user_id:
            params["actor_user_id"] = actor_user_id
        return [
            AdminAuditEvent(**{**item, "action": AdminAuditAction(item["action"]),
                "occurred_at": datetime.fromisoformat(item["occurred_at"])})
            for item in self._api.request("GET", "/admin/audit", params=params)
        ]


class ApiInstitutionInvites:
    def __init__(self, api: RoomFlowApi):
        self._api = api

    @staticmethod
    def _status(data):
        created_at = datetime.fromisoformat(data["created_at"]) if data["created_at"] else None
        return InvitationCodeStatus(data["active"], created_at)

    def status_for(self, actor):
        return self._status(self._api.request("GET", "/institutions/me/invitation-code"))

    def issue_or_replace(self, actor):
        data = self._api.request("POST", "/institutions/me/invitation-code/rotate")
        return data["code"], self._status(data)

    def revoke(self, actor):
        return self._status(self._api.request("DELETE", "/institutions/me/invitation-code"))


@dataclass(frozen=True, slots=True)
class ApiInstitutionPreview:
    institution_name: str


class ApiEnrollmentManagement:
    def __init__(self, api: RoomFlowApi):
        self._api = api

    def add_manual(self, actor, registration_number, name, email):
        return AuthorizedEnrollment(**self._api.request("POST", "/admin/enrollments", payload={
            "registration_number": registration_number, "name": name, "email": email,
        }))

    def list_enrollments(self, actor, query, status):
        params = {"q": query}
        if status:
            params["status"] = status.value
        return [AuthorizedEnrollment(**item) for item in self._api.request("GET", "/admin/enrollments", params=params)]

    def deactivate(self, actor, enrollment_id):
        return AuthorizedEnrollment(**self._api.request(
            "DELETE", f"/admin/enrollments/{quote(enrollment_id, safe='')}", conflict=ValueError,
        ))

    def preview_import(self, actor, content):
        data = self._api.request("POST", "/admin/enrollments/import/preview",
                                 files={"file": ("matriculas.xlsx", content)})
        return EnrollmentImportPreview(
            data["preview_id"], *(tuple(ImportRowResult(**item) for item in data[key])
                                  for key in ("valid", "duplicates", "invalid"))
        )

    def confirm_import(self, actor, preview_id):
        data = self._api.request("POST", "/admin/enrollments/import/confirm", payload={"preview_id": preview_id})
        return data["imported"]

    def preview_member_institution(self, raw_code, registration_number, name, email, attempt_key):
        del attempt_key
        data = self._api.request("POST", "/auth/signup/member/preview", authenticated=False,
            rate_error=TooManyEnrollmentAttempts, bad_request=MemberIdentityNotConfirmed,
            payload={"institutional_code": raw_code, "registration_number": registration_number,
                     "name": name, "email": email})
        return ApiInstitutionPreview(data["institution_name"])


class ApiMemberSignup:
    def __init__(self, api: RoomFlowApi):
        self._api = api

    def start(self, *, name, email, registration_number, institutional_code, password, attempt_key):
        del attempt_key
        data = self._api.request("POST", "/auth/signup/member/start", authenticated=False,
            rate_error=TooManyEnrollmentAttempts, bad_request=MemberIdentityNotConfirmed, payload={
                "name": name, "email": email, "registration_number": registration_number,
                "institutional_code": institutional_code, "password": password,
            })
        return MemberSignupStarted(data["institution_name"], data["email"])

    def verify_email(self, token, attempt_key):
        del attempt_key
        data = self._api.request("POST", "/auth/signup/member/verify-email", authenticated=False,
            rate_error=TooManyEnrollmentAttempts, bad_request=InvalidEmailVerification, payload={"token": token})
        return RegisteredMember(User(**data))


class ApiRuntime:
    def __init__(self, api: RoomFlowApi):
        self.authentication = ApiAuthentication(api)
        self.user_management = ApiUserManagement(api)
        self.institution_management = ApiInstitutionManagement(api)
        self.admin_audit = ApiAdminAudit(api)
        self.invite_codes = ApiInstitutionInvites(api)
        self.enrollment_management = ApiEnrollmentManagement(api)
        self.member_signup = ApiMemberSignup(api)
        self.space_management = ApiSpaceManagement(api)
        self.resource_management = ApiResourceManagement(api)
        self.floor_plan_management = ApiFloorPlans(api)
        self.admin_dashboard = ApiAdminDashboard(api)
        self.password_recovery = ApiPasswordRecovery(api)
        self.reservation_service = ApiReservations(api)
        self.conflict_service = ApiConflicts(api)
        self.manager_operations = ApiManagerOperations(api)
        self.notifications = ApiNotifications(api)


class ApiPasswordRecovery:
    def __init__(self, api: RoomFlowApi):
        self._api = api

    def request(self, email: str) -> None:
        self._api.request("POST", "/auth/password/recovery", authenticated=False, payload={"email": email})

    def reset(self, token: str, new_password: str) -> None:
        self._api.request(
            "POST", "/auth/password/reset", authenticated=False, bad_request=InvalidRecoveryToken,
            payload={"token": token, "new_password": new_password},
        )

from application.services.authentication_service import InvalidSession
from models.domain.exceptions import DomainAuthorizationError


class RuntimeUnavailable(DomainAuthorizationError):
    """A safe, user-facing persistence failure."""


class SessionExpired(InvalidSession, DomainAuthorizationError):
    pass

class DomainAuthorizationError(Exception):
    """Base error for denied domain actions."""


class PermissionDenied(DomainAuthorizationError):
    """The user's profile does not grant the requested action."""


class InstitutionAccessDenied(DomainAuthorizationError):
    """The target institution is outside the authenticated user's scope."""

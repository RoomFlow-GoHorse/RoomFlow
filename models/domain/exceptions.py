class DomainAuthorizationError(Exception):
    """Base error for denied domain actions."""


class PermissionDenied(DomainAuthorizationError):
    """The user's profile does not grant the requested action."""


class InstitutionAccessDenied(DomainAuthorizationError):
    """The target institution is outside the authenticated user's scope."""


class DuplicateResource(Exception):
    """A resource conflicts with an existing unique value."""


class ResourceNotFound(Exception):
    """A requested resource does not exist."""


class LastActiveAdministrator(Exception):
    """The institution must keep at least one active administrator."""

from models.domain.entities.institution import Institution
from models.domain.entities.permission import Permission
from models.domain.entities.profile import Profile
from models.domain.entities.user import User
from models.domain.exceptions import PermissionDenied
from models.domain.policies.institution_access_policy import InstitutionAccessPolicy


class PermissionPolicy:
    """Returns effective grants only where both action and scope are confirmed."""

    _COMMON_PERMISSIONS = frozenset({Permission.MANAGE_OWN_ACCOUNT, Permission.VIEW_NOTIFICATIONS})
    _EFFECTIVE_PERMISSIONS = {
        Profile.ADMIN: frozenset(
            {
                Permission.VIEW_ADMIN_DASHBOARD,
                Permission.VIEW_ADMIN_AUDIT,
                Permission.MANAGE_USERS,
                Permission.VIEW_PERMISSIONS,
                Permission.MANAGE_FLOOR_PLAN,
                Permission.EDIT_INSTITUTION_SETTINGS,
            }
        ) | _COMMON_PERMISSIONS,
        Profile.MANAGER: frozenset({
            Permission.MANAGE_SPACES, Permission.REVIEW_RESERVATIONS, Permission.RESOLVE_CONFLICTS,
            Permission.VIEW_MANAGER_DASHBOARD,
        }) | _COMMON_PERMISSIONS,
        Profile.REQUESTER: frozenset({
            Permission.CREATE_RESERVATION, Permission.VIEW_OWN_RESERVATIONS, Permission.CANCEL_OWN_RESERVATION,
        }) | _COMMON_PERMISSIONS,
   Profile.PARTICIPANT: frozenset({
    Permission.VIEW_PARTICIPANT_DASHBOARD,
    Permission.VIEW_AGENDA,
    Permission.LOCATE_SPACES,
}) | _COMMON_PERMISSIONS, }

    def __init__(self, institution_access: InstitutionAccessPolicy | None = None):
        self._institution_access = institution_access or InstitutionAccessPolicy()

    def effective_permissions(self, profile: Profile) -> frozenset[Permission]:
        return self._EFFECTIVE_PERMISSIONS.get(
            profile,
            self._COMMON_PERMISSIONS,
        )

    def authorize_own_account(self, user: User, target_user_id: str) -> None:
        self._require_permission(user, Permission.MANAGE_OWN_ACCOUNT)
        if user.id != target_user_id:
            raise PermissionDenied("O usuário só pode gerenciar a própria conta.")

    def authorize_listing(
        self,
        user: User,
        permission: Permission,
        requested_institution_id: str | None = None,
    ) -> str:
        self._require_permission(user, permission)
        return self._institution_access.resolve_listing_scope(
            user,
            requested_institution_id,
        )

    def authorize_resource(
        self,
        user: User,
        permission: Permission,
        resource_institution: Institution,
    ) -> None:
        """Authorize using the institution loaded from the target resource."""
        self._require_permission(user, permission)
        self._institution_access.assert_resource_access(
            user,
            resource_institution,
        )

    def _require_permission(self, user: User, permission: Permission) -> None:
        if not user.is_active:
            raise PermissionDenied("O usuário está inativo.")
        if permission not in self.effective_permissions(user.profile):
            raise PermissionDenied(
                "A permissão não está habilitada para este perfil."
            )

from datetime import timedelta

from application.ports.clock import Clock
from application.ports.resource_repository import ResourceRepository
from application.ports.space_repository import SpaceRepository
from application.ports.user_repository import UserRepository
from application.read_models.admin_dashboard import (
    AdminDashboardMetrics,
    EntityCounts,
    ProfileCount,
    RecentUser,
)
from models.domain.entities.permission import Permission
from models.domain.entities.profile import Profile
from models.domain.entities.user import User, UserStatus
from models.domain.policies.permission_policy import PermissionPolicy


class AdminDashboardService:
    """Calculates institution-scoped admin indicators from application stores."""

    RECENT_PERIODS = frozenset({7, 30, 90})

    def __init__(
        self,
        users: UserRepository,
        spaces: SpaceRepository,
        resources: ResourceRepository,
        clock: Clock,
        permission_policy: PermissionPolicy | None = None,
    ) -> None:
        self._users = users
        self._spaces = spaces
        self._resources = resources
        self._clock = clock
        self._permissions = permission_policy or PermissionPolicy()

    def get_metrics(self, actor: User, period_days: int = 30) -> AdminDashboardMetrics:
        if period_days not in self.RECENT_PERIODS:
            raise ValueError("O período deve ser de 7, 30 ou 90 dias.")
        institution_id = self._permissions.authorize_listing(
            actor, Permission.VIEW_ADMIN_DASHBOARD
        )

        accounts = tuple(self._users.list_by_institution(institution_id))
        people = tuple(account.user for account in accounts)
        buildings = tuple(self._spaces.list_buildings(institution_id, include_inactive=True))
        floors = tuple(
            floor
            for building in buildings
            for floor in self._spaces.list_floors(building.id, include_inactive=True)
        )
        spaces = tuple(self._spaces.list_spaces(institution_id, include_inactive=True))
        resources = tuple(self._resources.list_resources(institution_id, include_inactive=True))

        now = self._clock.now()
        cutoff = now - timedelta(days=period_days)
        recent = sorted(
            (
                user for user in people
                if user.created_at is not None and cutoff <= user.created_at <= now
            ),
            key=lambda user: (user.created_at, user.id),
            reverse=True,
        )
        return AdminDashboardMetrics(
            institution_id=institution_id,
            period_days=period_days,
            users=self._counts(people, lambda user: user.status is UserStatus.ACTIVE),
            users_by_profile=tuple(
                ProfileCount(profile, sum(user.profile is profile for user in people))
                for profile in Profile
            ),
            recent_user_count=len(recent),
            recent_users=tuple(
                RecentUser(
                    id=user.id,
                    name=user.name,
                    email=user.email,
                    profile=user.profile,
                    active=user.status is UserStatus.ACTIVE,
                    created_at=user.created_at,
                )
                for user in recent[:5]
            ),
            buildings=self._counts(buildings, lambda item: item.active),
            floors=self._counts(floors, lambda item: item.active),
            spaces=self._counts(spaces, lambda item: item.active),
            resources=self._counts(resources, lambda item: item.active),
        )

    @staticmethod
    def _counts(items, is_active) -> EntityCounts:
        active = sum(is_active(item) for item in items)
        return EntityCounts(total=len(items), active=active, inactive=len(items) - active)

from dataclasses import dataclass
from datetime import datetime

from models.domain.entities.profile import Profile


@dataclass(frozen=True, slots=True)
class EntityCounts:
    total: int
    active: int
    inactive: int


@dataclass(frozen=True, slots=True)
class ProfileCount:
    profile: Profile
    count: int


@dataclass(frozen=True, slots=True)
class RecentUser:
    id: str
    name: str
    email: str
    profile: Profile
    active: bool
    created_at: datetime


@dataclass(frozen=True, slots=True)
class AdminDashboardMetrics:
    institution_id: str
    period_days: int
    users: EntityCounts
    users_by_profile: tuple[ProfileCount, ...]
    recent_user_count: int
    recent_users: tuple[RecentUser, ...]
    buildings: EntityCounts
    floors: EntityCounts
    spaces: EntityCounts
    resources: EntityCounts

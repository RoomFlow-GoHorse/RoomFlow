from dataclasses import dataclass

from application.services.authentication_service import AuthenticationService
from application.services.login_attempt_limiter import LoginAttemptLimiter
from application.services.institution_management_service import InstitutionManagementService
from application.services.user_management_service import UserManagementService
from infrastructure.repositories.in_memory_institution_repository import InMemoryInstitutionRepository
from infrastructure.repositories.in_memory_session_repository import InMemorySessionRepository
from infrastructure.repositories.in_memory_user_repository import InMemoryUserRepository
from infrastructure.security.pbkdf2_password_hasher import Pbkdf2PasswordHasher
from models.domain.entities.profile import Profile
from models.domain.entities.institution import Institution
from models.domain.entities.user import User, UserStatus
from models.domain.entities.user_account import UserAccount


@dataclass(frozen=True, slots=True)
class InMemoryApplicationRuntime:
    authentication: AuthenticationService
    users: InMemoryUserRepository
    institutions: InMemoryInstitutionRepository
    user_management: UserManagementService
    institution_management: InstitutionManagementService


def build_application_runtime(environment: str) -> InMemoryApplicationRuntime:
    """Build process-shared adapters; demo data exists only in local envs."""
    hasher = Pbkdf2PasswordHasher()
    accounts = []
    institutions = []
    if environment in {"development", "test"}:
        institutions = [Institution("inst-demo", "Instituição de Demonstração")]
        demo_accounts = (
            ("u1", "Marina Costa", "admin@gmail.com", "admin123", Profile.ADMIN),
            ("u2", "Rafael Nunes", "gerente@gmail.com", "gerente123", Profile.MANAGER),
            ("u3", "Ana Beatriz", "solicitante@gmail.com", "solicitante123", Profile.REQUESTER),
            ("u4", "Lucas Lima", "participante@gmail.com", "participante123", Profile.PARTICIPANT),
        )
        accounts = [
            UserAccount(
                user=User(
                    id=user_id,
                    name=name,
                    email=email,
                    profile=profile,
                    institution_id="inst-demo",
                    status=UserStatus.ACTIVE,
                ),
                password_hash=hasher.hash_password(password),
            )
            for user_id, name, email, password, profile in demo_accounts
        ]
    limiter = LoginAttemptLimiter() if environment in {"development", "test"} else None
    user_repository = InMemoryUserRepository(accounts)
    institution_repository = InMemoryInstitutionRepository(institutions)
    authentication = AuthenticationService(
        users=user_repository,
        sessions=InMemorySessionRepository(),
        password_hasher=hasher,
        login_limiter=limiter,
    )
    return InMemoryApplicationRuntime(
        authentication=authentication,
        users=user_repository,
        institutions=institution_repository,
        user_management=UserManagementService(
            user_repository, institution_repository, hasher
        ),
        institution_management=InstitutionManagementService(
            institution_repository, user_repository, hasher
        ),
    )

from application.services.authentication_service import AuthenticationService
from application.services.login_attempt_limiter import LoginAttemptLimiter
from infrastructure.repositories.in_memory_session_repository import InMemorySessionRepository
from infrastructure.repositories.in_memory_user_repository import InMemoryUserRepository
from infrastructure.security.pbkdf2_password_hasher import Pbkdf2PasswordHasher
from models.domain.entities.profile import Profile
from models.domain.entities.user import User, UserStatus
from models.domain.entities.user_account import UserAccount


def build_authentication_service(environment: str) -> AuthenticationService:
    """Build process-shared adapters; demo credentials exist only in local envs."""
    hasher = Pbkdf2PasswordHasher()
    accounts = []
    if environment in {"development", "test"}:
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
    return AuthenticationService(
        users=InMemoryUserRepository(accounts),
        sessions=InMemorySessionRepository(),
        password_hasher=hasher,
        login_limiter=limiter,
    )

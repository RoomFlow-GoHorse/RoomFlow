import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from application.ports.clock import Clock
from application.ports.password_hasher import PasswordHasher
from application.ports.session_repository import SessionRepository
from application.ports.user_repository import UserRepository
from application.services.login_attempt_limiter import LoginAttemptLimiter
from models.domain.entities.user import User
from models.domain.entities.user_session import UserSession


GENERIC_LOGIN_ERROR = "E-mail ou senha incorretos."


class InvalidCredentials(Exception):
    pass


class TooManyLoginAttempts(Exception):
    pass


class InvalidSession(Exception):
    pass


@dataclass(frozen=True, slots=True)
class LoginResult:
    access_token: str
    expires_at: datetime
    user: User


class UtcSystemClock:
    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class AuthenticationService:
    """Login/session use cases; identity and scope are loaded from stored users."""

    def __init__(
        self,
        users: UserRepository,
        sessions: SessionRepository,
        password_hasher: PasswordHasher,
        clock: Clock | None = None,
        session_lifetime: timedelta = timedelta(hours=8),
        login_limiter: LoginAttemptLimiter | None = None,
    ) -> None:
        self._users = users
        self._sessions = sessions
        self._password_hasher = password_hasher
        self._clock = clock or UtcSystemClock()
        self._session_lifetime = session_lifetime
        self._login_limiter = login_limiter
        self._dummy_password_hash = self._password_hasher.hash_password(
            secrets.token_urlsafe(24)
        )

    def login(self, email: str, password: str, attempt_key: str = "local") -> LoginResult:
        now = self._clock.now()
        if self._login_limiter and not self._login_limiter.register_attempt(attempt_key, now):
            raise TooManyLoginAttempts

        account = self._users.find_by_email(email)
        valid_password = self._password_hasher.verify_password(
            password, account.password_hash if account else self._dummy_password_hash
        )
        if account is None or not valid_password or not account.user.is_active:
            raise InvalidCredentials

        if self._login_limiter:
            self._login_limiter.record_success(attempt_key)
        token = secrets.token_urlsafe(32)
        expires_at = now + self._session_lifetime
        self._sessions.save(UserSession(
            token_digest=self._digest(token),
            user_id=account.user.id,
            expires_at=expires_at,
        ))
        return LoginResult(token, expires_at, account.user)

    def authenticate(self, token: str) -> User:
        session = self._sessions.find_by_digest(self._digest(token))
        now = self._clock.now()
        if session is None or not session.is_valid_at(now):
            raise InvalidSession
        account = self._users.find_by_id(session.user_id)
        if account is None or not account.user.is_active:
            raise InvalidSession
        return account.user

    def logout(self, token: str) -> None:
        digest = self._digest(token)
        session = self._sessions.find_by_digest(digest)
        now = self._clock.now()
        if session is None or not session.is_valid_at(now):
            raise InvalidSession
        self._sessions.save(session.revoke(now))

    @staticmethod
    def _digest(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()


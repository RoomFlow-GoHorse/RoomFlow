import hashlib
import secrets
from collections.abc import Callable
from contextlib import nullcontext
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone

from application.ports.clock import Clock
from application.ports.password_hasher import PasswordHasher
from application.ports.session_repository import SessionRepository
from application.ports.user_repository import UserRepository
from application.services.login_attempt_limiter import LoginAttemptLimiter
from models.domain.entities.user import User
from models.domain.entities.user_session import UserSession
from models.domain.identity_normalization import normalize_email


GENERIC_LOGIN_ERROR = "E-mail ou senha incorretos."


class InvalidCredentials(Exception):
    pass


class TooManyLoginAttempts(Exception):
    pass


class InvalidSession(Exception):
    pass


class InstitutionSelectionRequired(Exception):
    def __init__(self, institution_ids: tuple[str, ...]):
        self.institution_ids = institution_ids


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
        lock=None,
        atomic=None,
        session_user_lookup: Callable[[str], tuple[UserSession, User] | None] | None = None,
    ) -> None:
        self._lock = lock if lock is not None else nullcontext()
        self._atomic = atomic if atomic is not None else lambda: self._lock
        self._users = users
        self._sessions = sessions
        self._session_user_lookup = session_user_lookup
        self._password_hasher = password_hasher
        self._clock = clock or UtcSystemClock()
        self._session_lifetime = session_lifetime
        self._login_limiter = login_limiter
        self._dummy_password_hash = self._password_hasher.hash_password(
            secrets.token_urlsafe(24)
        )

    def login(
        self, email: str, password: str, attempt_key: str = "local",
        institution_id: str | None = None,
    ) -> LoginResult:
        now = self._clock.now()
        if self._login_limiter and not self._login_limiter.register_attempt(attempt_key, now):
            raise TooManyLoginAttempts

        accounts = self._users.list_login_accounts(normalize_email(email))
        stored_hash = accounts[0].password_hash if accounts else self._dummy_password_hash
        valid_password = self._password_hasher.verify_password(
            password, stored_hash
        )
        eligible = [
            account for account in accounts
            if account.user.is_active
            and (institution_id is None or account.user.institution_id == institution_id)
        ]
        if not valid_password or not eligible:
            raise InvalidCredentials

        if self._login_limiter:
            self._login_limiter.record_success(attempt_key)
        if len(eligible) > 1:
            raise InstitutionSelectionRequired(
                tuple(account.user.institution_id for account in eligible if account.user.institution_id)
            )
        account = eligible[0]
        token = secrets.token_urlsafe(32)
        expires_at = now + self._session_lifetime
        with self._atomic():
            current = self._users.find_by_id(account.user.id, account.user.institution_id)
            if current != account:
                raise InvalidCredentials
            self._sessions.save(UserSession(
                token_digest=self._digest(token),
                user_id=account.user.id,
                expires_at=expires_at,
                institution_id=account.user.institution_id,
            ))
        return LoginResult(token, expires_at, account.user)

    def authenticate(self, token: str) -> User:
        digest = self._digest(token)
        with self._lock:
            if self._session_user_lookup is not None:
                result = self._session_user_lookup(digest)
                if result is None:
                    raise InvalidSession
                session, user = result
                if not session.is_valid_at(self._clock.now()) or not user.is_active:
                    raise InvalidSession
                return user

            session = self._sessions.find_by_digest(digest)
            now = self._clock.now()
            if session is None or not session.is_valid_at(now):
                raise InvalidSession
            account = self._users.find_by_id(session.user_id, session.institution_id)
            if account is None or not account.user.is_active:
                raise InvalidSession
            return account.user

    def logout(self, token: str) -> None:
        digest = self._digest(token)
        with self._atomic():
            session = self._sessions.find_by_digest(digest)
            now = self._clock.now()
            if session is None or not session.is_valid_at(now):
                raise InvalidSession
            self._sessions.save(session.revoke(now))

    def change_password(
        self, user_id: str, current_password: str, new_password: str,
        institution_id: str | None = None,
    ) -> None:
        account = self._users.find_by_id(user_id, institution_id)
        if (
            account is None
            or not account.user.is_active
            or not self._password_hasher.verify_password(
                current_password, account.password_hash
            )
        ):
            raise InvalidCredentials
        password_hash = self._password_hasher.hash_password(new_password)
        with self._atomic():
            current = self._users.find_by_id(user_id, institution_id)
            if current is None or not current.user.is_active or current.password_hash != account.password_hash:
                raise InvalidCredentials
            self._users.save(replace(current, password_hash=password_hash))

    @staticmethod
    def _digest(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

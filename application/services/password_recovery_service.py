import hashlib
import secrets
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import replace
from datetime import timedelta

from application.ports.clock import Clock
from application.ports.email_sender import EmailDeliveryUnavailable, EmailSender
from application.ports.password_hasher import PasswordHasher
from application.ports.password_recovery_repository import PasswordRecoveryRepository
from application.ports.session_repository import SessionRepository
from application.ports.user_repository import UserRepository
from application.services.authentication_service import TooManyLoginAttempts
from application.services.login_attempt_limiter import LoginAttemptLimiter
from models.domain.identity_normalization import normalize_email


class InvalidRecoveryToken(Exception):
    pass


class PasswordRecoveryService:
    def __init__(
        self, users: UserRepository, sessions: SessionRepository, recoveries: PasswordRecoveryRepository,
        hasher: PasswordHasher, sender: EmailSender, clock: Clock,
        atomic: Callable[[], AbstractContextManager],
    ) -> None:
        self._users, self._sessions, self._recoveries = users, sessions, recoveries
        self._hasher, self._sender, self._clock, self._atomic = hasher, sender, clock, atomic
        self._limiter = LoginAttemptLimiter()

    def request(self, email: str, attempt_key: str) -> None:
        now = self._clock.now()
        address = normalize_email(email)
        if not self._limiter.register_attempt(attempt_key, now):
            return
        if not self._limiter.register_attempt(f"email:{address}", now):
            return
        token = secrets.token_urlsafe(32)
        digest = self._digest(token)
        with self._atomic():
            account = next((item for item in self._users.list_login_accounts(address) if item.user.is_active), None)
            if account is None:
                return
            self._recoveries.issue(digest, account.user.id, now + timedelta(minutes=20), now)
        try:
            self._sender.send_password_reset(address, token)
        except EmailDeliveryUnavailable:
            with self._atomic():
                self._recoveries.consume(digest, self._clock.now())

    def reset(self, token: str, password: str, attempt_key: str) -> None:
        if not 8 <= len(password) <= 1024:
            raise ValueError("A senha deve ter entre 8 e 1024 caracteres.")
        now = self._clock.now()
        if not self._limiter.register_attempt(f"reset:{attempt_key}", now):
            raise TooManyLoginAttempts
        password_hash = self._hasher.hash_password(password)
        with self._atomic():
            user_id = self._recoveries.consume(self._digest(token), now)
            account = self._users.find_by_id(user_id) if user_id is not None else None
            if account is None or not account.user.is_active:
                raise InvalidRecoveryToken
            self._users.save(replace(account, password_hash=password_hash))
            self._sessions.revoke_user(account.user.id, now)
        self._limiter.record_success(f"reset:{attempt_key}")

    @staticmethod
    def _digest(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

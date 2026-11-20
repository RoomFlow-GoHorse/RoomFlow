import hashlib
import secrets
from dataclasses import dataclass
from datetime import timedelta
from threading import RLock

from application.ports.authorized_enrollment_repository import AuthorizedEnrollmentRepository
from application.ports.clock import Clock
from application.ports.email_sender import EmailSender
from application.ports.pending_member_signup_repository import PendingMemberSignupRepository
from application.ports.password_hasher import PasswordHasher
from application.ports.user_repository import UserRepository
from application.services.enrollment_management_service import (
    EnrollmentManagementService,
    MemberIdentityNotConfirmed,
    TooManyEnrollmentAttempts,
)
from application.services.login_attempt_limiter import LoginAttemptLimiter
from application.services.institution_invite_code_service import InstitutionInviteCodeService
from models.domain.entities.pending_member_signup import PendingMemberSignup
from models.domain.entities.profile import Profile
from models.domain.entities.user import User, UserStatus
from models.domain.entities.user_account import UserAccount
from models.domain.exceptions import DuplicateResource, ResourceNotFound


@dataclass(frozen=True, slots=True)
class MemberSignupStarted:
    institution_name: str
    email: str


@dataclass(frozen=True, slots=True)
class RegisteredMember:
    user: User


class MemberSignupService:
    """Email-confirmed member signup; infrastructure and time are injected."""

    TOKEN_TTL = timedelta(minutes=20)

    def __init__(
        self,
        eligibility: EnrollmentManagementService,
        enrollments: AuthorizedEnrollmentRepository,
        invite_codes: InstitutionInviteCodeService,
        pending_signups: PendingMemberSignupRepository,
        users: UserRepository,
        password_hasher: PasswordHasher,
        email_sender: EmailSender,
        attempt_limiter: LoginAttemptLimiter,
        clock: Clock,
    ) -> None:
        self._eligibility = eligibility
        self._enrollments = enrollments
        self._invite_codes = invite_codes
        self._pending = pending_signups
        self._users = users
        self._password_hasher = password_hasher
        self._email_sender = email_sender
        self._attempt_limiter = attempt_limiter
        self._clock = clock
        self._lock = RLock()

    def start(
        self, *, name: str, email: str, registration_number: str,
        institutional_code: str, password: str, attempt_key: str,
    ) -> MemberSignupStarted:
        if len(password) < 8:
            raise ValueError("A senha deve possuir pelo menos 8 caracteres.")
        normalized_email = email.strip().lower()
        now = self._clock.now()
        email_key = f"signup-email:{normalized_email}"
        if (
            not self._attempt_limiter.register_attempt(attempt_key, now)
            or not self._attempt_limiter.register_attempt(email_key, now)
        ):
            raise TooManyEnrollmentAttempts
        self._pending.delete_expired(now)
        try:
            preview = self._eligibility.preview_member_institution(
                institutional_code, registration_number, name, normalized_email,
                f"signup:{attempt_key}",
            )
        except TooManyEnrollmentAttempts:
            raise
        if self._users.find_by_email(normalized_email):
            raise DuplicateResource("N\u00e3o foi poss\u00edvel concluir o cadastro com os dados informados.")
        enrollment = self._enrollments.find(preview.institution_id, registration_number)
        if enrollment is None or not enrollment.is_available:
            raise MemberIdentityNotConfirmed

        token = secrets.token_urlsafe(32)
        pending = PendingMemberSignup(
            token_digest=self._digest(token),
            institution_id=preview.institution_id,
            registration_number=enrollment.registration_number,
            name=name.strip(),
            email=normalized_email,
            password_hash=self._password_hasher.hash_password(password),
            invitation_digest=self._invite_codes.digest_code(institutional_code),
            expires_at=self._clock.now() + self.TOKEN_TTL,
        )
        self._pending.save(pending)
        try:
            self._email_sender.send_verification(normalized_email, token)
        except Exception:
            self._pending.delete(pending.token_digest)
            raise
        self._attempt_limiter.record_success(attempt_key)
        self._attempt_limiter.record_success(email_key)
        return MemberSignupStarted(preview.institution_name, normalized_email)

    def verify_email(self, token: str, attempt_key: str) -> RegisteredMember:
        digest = self._digest(token) if token and len(token) <= 200 else "invalid"
        rate_key = f"verify:{attempt_key}"
        if not self._attempt_limiter.register_attempt(rate_key, self._clock.now()):
            raise TooManyEnrollmentAttempts
        with self._lock:
            pending = self._pending.find_by_digest(digest)
            if pending is None or pending.expires_at <= self._clock.now():
                raise InvalidEmailVerification
            if self._invite_codes.resolve_active_digest(pending.invitation_digest) != pending.institution_id:
                raise InvalidEmailVerification
            enrollment = self._enrollments.find(pending.institution_id, pending.registration_number)
            if enrollment is None or not enrollment.is_available:
                raise InvalidEmailVerification

            user = User(
                id=f"u-{secrets.token_urlsafe(12)}",
                name=pending.name,
                email=pending.email,
                profile=Profile.PARTICIPANT,
                institution_id=pending.institution_id,
                status=UserStatus.ACTIVE,
            )

            def create_account() -> None:
                self._users.add(UserAccount(user, pending.password_hash))

            try:
                self._enrollments.consume_with(
                    pending.institution_id, pending.registration_number, user.id,
                    create_account,
                )
            except (DuplicateResource, ResourceNotFound):
                raise InvalidEmailVerification from None
            self._pending.delete(digest)
            self._attempt_limiter.record_success(rate_key)
            return RegisteredMember(user)

    @staticmethod
    def _digest(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

class InvalidEmailVerification(Exception):
    """Invalid, expired, revoked or already used email verification token."""

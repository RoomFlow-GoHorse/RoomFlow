from dataclasses import dataclass

from sqlalchemy.orm import Session, sessionmaker

from application.ports.email_sender import EmailSender
from application.services.admin_audit_service import AdminAuditService
from application.services.admin_dashboard_service import AdminDashboardService
from application.services.authentication_service import AuthenticationService
from application.services.conflict_service import ConflictService
from application.services.institution_management_service import InstitutionManagementService
from application.services.institution_invite_code_service import InstitutionInviteCodeService
from application.services.enrollment_management_service import EnrollmentManagementService
from application.services.member_signup_service import MemberSignupService
from application.services.manager_operations_service import ManagerOperationsService
from application.services.notification_service import NotificationService
from application.services.password_recovery_service import PasswordRecoveryService
from application.services.floor_plan_service import FloorPlanService
from application.services.resource_management_service import ResourceManagementService
from application.services.space_service import SpaceService
from application.services.reservation_service import ReservationService
from application.services.login_attempt_limiter import LoginAttemptLimiter
from application.services.user_management_service import UserManagementService
from infrastructure.persistence.audit_repository import PostgresAdminAuditRepository
from infrastructure.persistence.conflict_repository import PostgresConflictRepository
from infrastructure.persistence.enrollment_repository import PostgresAuthorizedEnrollmentRepository
from infrastructure.persistence.enrollment_preview_repository import PostgresEnrollmentPreviewRepository
from infrastructure.persistence.institutions import PostgresInstitutionRepository
from infrastructure.persistence.notification_repository import PostgresNotificationRepository
from infrastructure.persistence.invite_repository import PostgresInviteCodeRepository
from infrastructure.persistence.pending_signup_repository import PostgresPendingSignupRepository
from infrastructure.persistence.password_recovery_repository import PostgresPasswordRecoveryRepository
from infrastructure.persistence.plant_repository import PostgresFloorPlanRepository, PostgresPlantFileStorage
from infrastructure.persistence.structure_repository import PostgresStructureRepository
from infrastructure.persistence.reservation_repository import PostgresReservationRepository
from infrastructure.persistence.session_repository import PostgresSessionRepository
from infrastructure.persistence.transaction import PostgresTransaction
from infrastructure.persistence.users import PostgresUserRepository
from infrastructure.email.smtp_email_sender import SmtpEmailSender
from infrastructure.security.pbkdf2_password_hasher import Pbkdf2PasswordHasher
from infrastructure.time.system_clock import SystemClock
from infrastructure.spreadsheets.openpyxl_enrollment_parser import OpenpyxlEnrollmentSpreadsheetParser


@dataclass(frozen=True, slots=True)
class PostgresRuntime:
    authentication: AuthenticationService
    user_management: UserManagementService
    institution_management: InstitutionManagementService
    admin_audit: AdminAuditService
    invite_codes: InstitutionInviteCodeService
    enrollment_management: EnrollmentManagementService
    member_signup: MemberSignupService
    space_management: SpaceService
    resource_management: ResourceManagementService
    floor_plan_management: FloorPlanService
    admin_dashboard: AdminDashboardService
    password_recovery: PasswordRecoveryService
    reservation_service: ReservationService
    conflict_service: ConflictService
    manager_operations: ManagerOperationsService
    notifications: NotificationService


def build_postgres_runtime(
    factory: sessionmaker[Session], email_sender: EmailSender | None = None,
) -> PostgresRuntime:
    transaction = PostgresTransaction(factory)
    hasher = Pbkdf2PasswordHasher()
    clock = SystemClock()
    users = PostgresUserRepository(transaction)
    institutions = PostgresInstitutionRepository(transaction)
    sessions = PostgresSessionRepository(transaction)
    email = email_sender or SmtpEmailSender()
    audit = AdminAuditService(
        PostgresAdminAuditRepository(transaction), clock, atomic=transaction.atomic, users=users,
    )
    invites = InstitutionInviteCodeService(PostgresInviteCodeRepository(transaction), audit=audit)
    enrollments = PostgresAuthorizedEnrollmentRepository(transaction)
    structure = PostgresStructureRepository(transaction)
    conflicts = PostgresConflictRepository(transaction)
    reservations = PostgresReservationRepository(transaction)
    notifications = NotificationService(
        PostgresNotificationRepository(transaction), institutions, users, clock, transaction.snapshot, reservations,
    )
    reservation_service = ReservationService(
        reservations, structure, institutions, clock, transaction.atomic, audit.current_actor, conflicts, notifications, users,
    )
    enrollment_management = EnrollmentManagementService(
        enrollments, institutions, invites, OpenpyxlEnrollmentSpreadsheetParser(),
        PostgresEnrollmentPreviewRepository(transaction),
        attempt_limiter=LoginAttemptLimiter(max_attempts=8), audit=audit,
    )
    return PostgresRuntime(
        authentication=AuthenticationService(
            users, sessions, hasher, clock=clock, login_limiter=LoginAttemptLimiter(),
            atomic=transaction.atomic,
        ),
        user_management=UserManagementService(
            users, institutions, hasher, clock=clock, audit=audit, sessions=sessions,
        ),
        institution_management=InstitutionManagementService(
            institutions, users, hasher, clock=clock, audit=audit,
        ),
        admin_audit=audit,
        invite_codes=invites,
        enrollment_management=enrollment_management,
        space_management=SpaceService(structure, audit=audit),
        reservation_service=reservation_service,
        conflict_service=ConflictService(
            conflicts, reservations, reservation_service, institutions, clock, transaction.atomic, audit.current_actor,
        ),
        manager_operations=ManagerOperationsService(
            institutions, structure, reservation_service, reservations, structure, clock, transaction.snapshot,
        ),
        notifications=notifications,
        resource_management=ResourceManagementService(structure, structure, audit=audit),
        floor_plan_management=FloorPlanService(
            PostgresFloorPlanRepository(transaction, structure), PostgresPlantFileStorage(transaction), audit=audit,
        ),
        admin_dashboard=AdminDashboardService(users, structure, structure, clock),
        password_recovery=PasswordRecoveryService(
            users, sessions, PostgresPasswordRecoveryRepository(transaction), hasher, email,
            clock, transaction.atomic,
        ),
        member_signup=MemberSignupService(
            eligibility=enrollment_management, enrollments=enrollments, invite_codes=invites,
            pending_signups=PostgresPendingSignupRepository(transaction), users=users,
            password_hasher=hasher, email_sender=email,
            attempt_limiter=LoginAttemptLimiter(max_attempts=8), clock=clock, audit=audit,
        ),
    )

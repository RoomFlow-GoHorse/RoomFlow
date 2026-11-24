from dataclasses import dataclass
from threading import RLock

from application.services.authentication_service import AuthenticationService
from application.services.login_attempt_limiter import LoginAttemptLimiter
from application.services.institution_management_service import InstitutionManagementService
from application.services.institution_invite_code_service import InstitutionInviteCodeService
from application.services.enrollment_management_service import EnrollmentManagementService
from application.services.user_management_service import UserManagementService
from application.services.member_signup_service import MemberSignupService
from application.services.space_service import SpaceService
from application.services.resource_management_service import ResourceManagementService
from application.services.floor_plan_service import FloorPlanService
from application.services.admin_dashboard_service import AdminDashboardService
from application.services.admin_audit_service import AdminAuditService
from infrastructure.in_memory_admin_transaction import InMemoryAdminTransaction
from infrastructure.repositories.in_memory_institution_repository import InMemoryInstitutionRepository
from infrastructure.repositories.in_memory_institution_invite_code_repository import InMemoryInstitutionInviteCodeRepository
from infrastructure.repositories.in_memory_authorized_enrollment_repository import InMemoryAuthorizedEnrollmentRepository
from infrastructure.repositories.in_memory_enrollment_preview_repository import InMemoryEnrollmentPreviewRepository
from infrastructure.repositories.in_memory_session_repository import InMemorySessionRepository
from infrastructure.repositories.in_memory_user_repository import InMemoryUserRepository
from infrastructure.repositories.in_memory_space_repository import InMemorySpaceRepository
from infrastructure.repositories.in_memory_admin_audit_repository import InMemoryAdminAuditRepository
from infrastructure.storage.temporary_plant_file_storage import TemporaryPlantFileStorage
from infrastructure.security.pbkdf2_password_hasher import Pbkdf2PasswordHasher
from infrastructure.spreadsheets.openpyxl_enrollment_parser import OpenpyxlEnrollmentSpreadsheetParser
from infrastructure.repositories.in_memory_pending_member_signup_repository import InMemoryPendingMemberSignupRepository
from infrastructure.email.in_memory_email_sender import InMemoryEmailSender
from infrastructure.time.system_clock import SystemClock
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
    invite_codes: InstitutionInviteCodeService
    authorized_enrollments: InMemoryAuthorizedEnrollmentRepository
    enrollment_management: EnrollmentManagementService
    member_signup: MemberSignupService
    simulated_email_sender: InMemoryEmailSender
    pending_member_signups: InMemoryPendingMemberSignupRepository
    spaces: InMemorySpaceRepository
    space_management: SpaceService
    resource_management: ResourceManagementService
    floor_plan_management: FloorPlanService
    plant_file_storage: TemporaryPlantFileStorage
    admin_dashboard: AdminDashboardService
    admin_audit: AdminAuditService
    admin_audit_repository: InMemoryAdminAuditRepository


def build_application_runtime(environment: str) -> InMemoryApplicationRuntime:
    """Build process-shared adapters; demo data exists only in local envs."""
    hasher = Pbkdf2PasswordHasher()
    clock = SystemClock()
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
    transaction = InMemoryAdminTransaction(RLock())
    user_repository = InMemoryUserRepository(accounts, transaction=transaction)
    institution_repository = InMemoryInstitutionRepository(institutions, transaction=transaction)
    spaces = InMemorySpaceRepository(spaces=None if accounts else (), transaction=transaction)
    plant_file_storage = TemporaryPlantFileStorage()
    admin_audit_repository = InMemoryAdminAuditRepository(transaction=transaction)
    admin_audit = AdminAuditService(admin_audit_repository, clock, atomic=transaction.atomic, users=user_repository)
    invite_code_repository = InMemoryInstitutionInviteCodeRepository(transaction=transaction)
    invite_code_service = InstitutionInviteCodeService(invite_code_repository, audit=admin_audit)
    enrollment_repository = InMemoryAuthorizedEnrollmentRepository(transaction=transaction)
    sessions = InMemorySessionRepository(transaction=transaction)
    authentication = AuthenticationService(
        users=user_repository,
        sessions=sessions,
        lock=transaction.lock,
        password_hasher=hasher,
        login_limiter=limiter,
    )
    if accounts:
        InstitutionInviteCodeService(invite_code_repository).issue_or_replace(accounts[0].user)
    enrollment_management = EnrollmentManagementService(
        enrollments=enrollment_repository,
        institutions=institution_repository,
        invite_codes=invite_code_service,
        spreadsheet_parser=OpenpyxlEnrollmentSpreadsheetParser(),
        previews=InMemoryEnrollmentPreviewRepository(),
        attempt_limiter=LoginAttemptLimiter(max_attempts=8),
        audit=admin_audit,
    )
    simulated_email_sender = InMemoryEmailSender()
    pending_member_signups = InMemoryPendingMemberSignupRepository()
    member_signup = MemberSignupService(
        eligibility=enrollment_management,
        enrollments=enrollment_repository,
        invite_codes=invite_code_service,
        pending_signups=pending_member_signups,
        users=user_repository,
        password_hasher=hasher,
        email_sender=simulated_email_sender,
        attempt_limiter=LoginAttemptLimiter(max_attempts=8),
        clock=clock,
        audit=admin_audit,
    )
    return InMemoryApplicationRuntime(
        authentication=authentication,
        users=user_repository,
        institutions=institution_repository,
        user_management=UserManagementService(
            user_repository, institution_repository, hasher, clock=clock, audit=admin_audit,
            sessions=sessions,
        ),
        institution_management=InstitutionManagementService(
            institution_repository, user_repository, hasher, clock=clock, audit=admin_audit
        ),
        invite_codes=invite_code_service,
        authorized_enrollments=enrollment_repository,
        enrollment_management=enrollment_management,
        member_signup=member_signup,
        simulated_email_sender=simulated_email_sender,
        pending_member_signups=pending_member_signups,
        spaces=spaces,
        space_management=SpaceService(spaces, audit=admin_audit),
        resource_management=ResourceManagementService(spaces, spaces, audit=admin_audit),
        floor_plan_management=FloorPlanService(spaces, plant_file_storage, audit=admin_audit, lock=transaction.lock),
        plant_file_storage=plant_file_storage,
        admin_dashboard=AdminDashboardService(user_repository, spaces, spaces, clock),
        admin_audit=admin_audit,
        admin_audit_repository=admin_audit_repository,
    )

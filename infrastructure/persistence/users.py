from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from infrastructure.persistence.transaction import PostgresTransaction
from infrastructure.persistence.user_mapping import to_database_identity_id, to_user_account
from models.database_models import Instituicao, TipoUsuario, Usuario, UsuarioInstituicao
from models.domain.entities.user import UserStatus
from models.domain.entities.user_account import UserAccount
from models.domain.exceptions import DuplicateResource, LastActiveAdministrator, PermissionDenied, ResourceNotFound
from models.domain.identity_normalization import normalize_email


class PostgresUserRepository:
    def __init__(self, transaction: PostgresTransaction):
        self._transaction = transaction

    @staticmethod
    def _memberships():
        return (
            select(Usuario, UsuarioInstituicao, Instituicao)
            .join(UsuarioInstituicao, UsuarioInstituicao.user_id == Usuario.id)
            .join(Instituicao, Instituicao.id == UsuarioInstituicao.institution_id)
        )

    def list_login_accounts(self, email: str) -> tuple[UserAccount, ...]:
        lookup = self._memberships().where(func.lower(func.btrim(Usuario.email)) == normalize_email(email))
        with self._transaction.session() as session:
            rows = session.execute(lookup.order_by(Instituicao.id)).all()
            if len({row[0].id for row in rows}) > 1:
                return ()
            return tuple(to_user_account(*row) for row in rows)

    def find_by_email(self, email: str) -> UserAccount | None:
        return next(iter(self.list_login_accounts(email)), None)

    def find_by_id(self, user_id: str, institution_id: str | None = None) -> UserAccount | None:
        try:
            lookup = self._memberships().where(Usuario.id == to_database_identity_id(user_id))
            if institution_id is not None:
                lookup = lookup.where(Instituicao.id == to_database_identity_id(institution_id))
        except ValueError:
            return None
        with self._transaction.session() as session:
            active = (Usuario.status == "ativo") & (UsuarioInstituicao.status == "ativo") & (Instituicao.status == "ativo")
            row = session.execute(lookup.order_by(active.desc(), Instituicao.id).limit(1)).first()
            return to_user_account(*row) if row else None

    def list_by_institution(self, institution_id: str) -> tuple[UserAccount, ...]:
        lookup = self._memberships().where(Instituicao.id == to_database_identity_id(institution_id))
        with self._transaction.session() as session:
            return tuple(to_user_account(*row) for row in session.execute(lookup.order_by(Usuario.id)))

    def has_other_memberships(self, user_id: str, institution_id: str) -> bool:
        lookup = select(UsuarioInstituicao.id).where(
            UsuarioInstituicao.user_id == to_database_identity_id(user_id),
            UsuarioInstituicao.institution_id != to_database_identity_id(institution_id),
        )
        with self._transaction.session() as session:
            return session.scalar(lookup.limit(1)) is not None

    def add(self, account: UserAccount) -> UserAccount:
        candidate = account.user
        institution_id = to_database_identity_id(candidate.institution_id or "")
        with self._transaction.atomic(), self._transaction.session() as session:
            institution = session.get(Instituicao, institution_id)
            if institution is None or institution.status != "ativo":
                raise PermissionDenied("A instituição não está ativa.")
            email = normalize_email(candidate.email)
            self._check_email(session, email)
            profile = candidate.profile.value
            profile_id = session.scalar(select(TipoUsuario.id).where(TipoUsuario.name == profile))
            if profile_id is None:
                session.execute(insert(TipoUsuario).values(name=profile).on_conflict_do_nothing(
                    index_elements=[TipoUsuario.name],
                ))
                profile_id = session.scalar(select(TipoUsuario.id).where(TipoUsuario.name == profile))
            user = Usuario(
                name=candidate.name, email=email, password_hash=account.password_hash,
                status="ativo", role=candidate.profile.value, tipo_usuario_id=profile_id,
            )
            session.add(user)
            session.flush()
            membership = UsuarioInstituicao(
                user_id=user.id, institution_id=institution_id,
                role=candidate.profile.value, status=candidate.status.value,
            )
            session.add(membership)
            session.flush()
            return to_user_account(user, membership, institution)

    def save(self, account: UserAccount) -> None:
        candidate = account.user
        user_id = to_database_identity_id(candidate.id)
        institution_id = to_database_identity_id(candidate.institution_id or "")
        lookup = self._memberships().where(Usuario.id == user_id, Instituicao.id == institution_id)
        with self._transaction.atomic(), self._transaction.session() as session:
            row = session.execute(lookup).one_or_none()
            if row is None:
                raise ResourceNotFound("Usuário não encontrado.")
            user, membership, institution = row
            previous = to_user_account(*row).user
            if previous.is_active and previous.profile.value == "admin" and (
                not candidate.is_active or candidate.profile.value != "admin"
            ):
                others = self._memberships().where(
                    Instituicao.id == institution_id, Usuario.id != user_id,
                    Usuario.status == "ativo", UsuarioInstituicao.status == "ativo",
                    UsuarioInstituicao.role == "admin",
                )
                if session.execute(others.limit(1)).first() is None:
                    raise LastActiveAdministrator("A instituição precisa manter pelo menos um administrador ativo.")
            if candidate.status != previous.status:
                if candidate.status is UserStatus.ACTIVE and (user.status != "ativo" or institution.status != "ativo"):
                    raise PermissionDenied("A conta ou a instituição está inativa.")
                membership.status = candidate.status.value
            membership.role = candidate.profile.value
            email = normalize_email(candidate.email)
            if email != normalize_email(user.email):
                self._check_email(session, email, user_id)
                user.email = email
            user.name = candidate.name
            user.password_hash = account.password_hash

    def save_preserving_active_admin(self, account: UserAccount, institution_id: str) -> None:
        if account.user.institution_id != institution_id:
            raise ResourceNotFound("Usuário não encontrado.")
        self.save(account)

    @staticmethod
    def _check_email(session, email: str, user_id: int | None = None) -> None:
        lookup = select(Usuario.id).where(func.lower(func.btrim(Usuario.email)) == email)
        if user_id is not None:
            lookup = lookup.where(Usuario.id != user_id)
        if session.scalar(lookup.limit(1)) is not None:
            raise DuplicateResource("Já existe uma conta com este e-mail.")

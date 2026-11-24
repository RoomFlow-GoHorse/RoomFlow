from models.database_models import Instituicao, Usuario, UsuarioInstituicao
from models.domain.entities.profile import Profile
from models.domain.entities.user import User, UserStatus
from models.domain.entities.user_account import UserAccount
from models.domain.identity_normalization import normalize_email


def to_database_identity_id(domain_id: str, *, bits: int = 32) -> int:
    """Decode an ID issued by the existing integer identity tables."""
    try:
        database_id = int(domain_id)
    except ValueError:
        raise ValueError("Identificador inválido para o banco de dados.") from None
    limit = 2 ** (bits - 1)
    if str(database_id) != domain_id or not -limit <= database_id < limit:
        raise ValueError("Identificador inválido para o banco de dados.")
    return database_id


def to_user_account(
    user: Usuario,
    membership: UsuarioInstituicao,
    institution: Instituicao,
) -> UserAccount:
    """Project a stored account within the membership explicitly selected by the caller."""
    if (
        user.id is None
        or institution.id is None
        or membership.user_id != user.id
        or membership.institution_id != institution.id
    ):
        raise ValueError("O vínculo não corresponde ao usuário e à instituição informados.")

    statuses = (UserStatus(user.status), UserStatus(membership.status), UserStatus(institution.status))
    status = UserStatus.INACTIVE if UserStatus.INACTIVE in statuses else UserStatus.ACTIVE
    return UserAccount(
        user=User(
            id=str(user.id),
            name=user.name,
            email=normalize_email(user.email),
            profile=Profile(membership.role),
            institution_id=str(institution.id),
            status=status,
            created_at=user.criado_em,
            phone=user.phone,
        ),
        password_hash=user.password_hash,
    )

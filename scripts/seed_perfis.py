from sqlalchemy.dialects.postgresql import insert

from config.constants import ROLE_LABELS
from config.database import SessionLocal
from models.database_models import TipoUsuario


def semear_perfis() -> None:
    comando = (
        insert(TipoUsuario)
        .values([{"name": perfil} for perfil in ROLE_LABELS])
        .on_conflict_do_nothing(index_elements=[TipoUsuario.name])
    )

    with SessionLocal.begin() as sessao:
        sessao.execute(comando)


if __name__ == "__main__":
    semear_perfis()
    print("Perfis cadastrados: " + ", ".join(ROLE_LABELS.values()))

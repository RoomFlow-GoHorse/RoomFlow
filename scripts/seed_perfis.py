from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from config.constants import ROLE_LABELS
from config.database import SessionLocal
from models.database_models import TipoUsuario


def cadastrar_perfis(sessao: Session) -> None:
    comando = (
        insert(TipoUsuario)
        .values([{"name": perfil} for perfil in ROLE_LABELS])
        .on_conflict_do_nothing(index_elements=[TipoUsuario.name])
    )

    sessao.execute(comando)


def semear_perfis() -> None:
    with SessionLocal.begin() as sessao:
        cadastrar_perfis(sessao)


if __name__ == "__main__":
    semear_perfis()
    print("Perfis cadastrados: " + ", ".join(ROLE_LABELS.values()))

from pathlib import Path

from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

from models.database_models import Base


class DatabaseNotReady(RuntimeError):
    pass


def check_postgres_readiness(factory) -> None:
    migrations = Path(__file__).resolve().parents[2] / "migrations"
    expected_revisions = set(ScriptDirectory(str(migrations)).get_heads())
    with factory() as session:
        try:
            tables = set(inspect(session.connection()).get_table_names())
            revisions = (
                set(session.scalars(text("SELECT version_num FROM alembic_version")))
                if "alembic_version" in tables else set()
            )
        except SQLAlchemyError:
            raise DatabaseNotReady("Falha ao acessar o PostgreSQL. Confira o serviço e a configuração do banco.") from None
    if revisions != expected_revisions or not Base.metadata.tables.keys() <= tables:
        raise DatabaseNotReady("O esquema do PostgreSQL não está pronto. Confira a revisão com python -m alembic current.")

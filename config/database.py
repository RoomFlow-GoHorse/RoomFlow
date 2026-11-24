import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError
from sqlalchemy.orm import sessionmaker

from infrastructure.persistence.base import Base


load_dotenv()


def database_url():
    if configured_url := os.getenv("DATABASE_URL", "").strip():
        try:
            url = make_url(configured_url)
            if url.drivername in {"postgres", "postgresql", "postgresql+psycopg"}:
                return url.set(drivername="postgresql+psycopg")
        except (ArgumentError, ValueError):
            pass
        raise RuntimeError("DATABASE_URL deve conter uma URL PostgreSQL válida.") from None

    required = ("DB_HOST", "DB_PORT", "DB_NAME", "DB_USERNAME", "DB_PASSWORD")
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise RuntimeError(f"Configure no .env: {', '.join(missing)}")
    return URL.create(
        "postgresql+psycopg",
        username=os.environ["DB_USERNAME"],
        password=os.environ["DB_PASSWORD"],
        host=os.environ["DB_HOST"],
        port=int(os.environ["DB_PORT"]),
        database=os.environ["DB_NAME"],
    )


engine = create_engine(
    database_url(), pool_pre_ping=True, connect_args={"connect_timeout": 5}, hide_parameters=True,
)
SessionLocal = sessionmaker(bind=engine)

from contextlib import contextmanager
from contextvars import ContextVar

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker


class PostgresTransaction:
    def __init__(self, factory: sessionmaker[Session]):
        self._factory = factory
        self._active: ContextVar[Session | None] = ContextVar("roomflow_sql_session", default=None)

    @contextmanager
    def session(self):
        active = self._active.get()
        if active is not None:
            yield active
        else:
            with self._factory.begin() as session:
                yield session

    @contextmanager
    def atomic(self):
        if self._active.get() is not None:
            yield
            return
        with self._factory.begin() as session:
            # Serialize identity writes across workers, including normalized uniqueness checks.
            session.execute(text("SELECT pg_advisory_xact_lock(189923011, 1)"))
            token = self._active.set(session)
            try:
                yield
            finally:
                self._active.reset(token)

    @contextmanager
    def snapshot(self):
        if self._active.get() is not None:
            yield
            return
        with self._factory.begin() as session:
            session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
            token = self._active.set(session)
            try:
                yield
            finally:
                self._active.reset(token)

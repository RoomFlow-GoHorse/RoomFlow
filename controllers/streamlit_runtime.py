import logging
import os

import streamlit as st

from application.services.authentication_service import InvalidSession
from config.runtime import persistence_mode
from controllers.local_runtime import LocalRuntime
from controllers.runtime_errors import RuntimeUnavailable
from infrastructure.persistence.runtime import build_postgres_runtime
from infrastructure.authentication_factory import InMemoryApplicationRuntime, build_application_runtime


PERSISTENT_PAGES = frozenset({
    "admin_dashboard", "usuarios", "historico_admin", "configuracoes_instituicao",
    "permissoes", "planta_instituicao", "espacos", "conta",
    "nova_reserva", "minhas_reservas", "gerente_reservas", "gerente_conflitos",
    "gerente_dashboard", "ocupacao", "notificacoes", "participante_dashboard", "agenda", "localizar",
})

LOGGER = logging.getLogger(__name__)


def uses_persistent_runtime() -> bool:
    try:
        return persistence_mode() == "postgres"
    except ValueError as exc:
        raise RuntimeUnavailable(str(exc)) from None


def uses_roomflow_api() -> bool:
    """Compatibility for pages integrated before Streamlit moved to local services."""
    return uses_persistent_runtime()


@st.cache_resource
def _get_local_runtime(environment: str) -> InMemoryApplicationRuntime:
    return build_application_runtime(environment)


@st.cache_resource
def _get_postgres_runtime():
    from infrastructure.persistence.readiness import check_postgres_readiness, DatabaseNotReady
    from sqlalchemy.exc import SQLAlchemyError

    try:
        from config.database import SessionLocal
        check_postgres_readiness(SessionLocal)
        return build_postgres_runtime(SessionLocal)
    except DatabaseNotReady as exc:
        raise RuntimeUnavailable(str(exc)) from None
    except (RuntimeError, ValueError, SQLAlchemyError):
        raise RuntimeUnavailable("Não foi possível inicializar o PostgreSQL. Confira DATABASE_URL ou DB_* e as migrations do banco.") from None


def get_streamlit_runtime() -> InMemoryApplicationRuntime | LocalRuntime:
    environment = os.getenv("APP_ENV", "production").strip().lower()
    try:
        mode = persistence_mode(environment)
    except ValueError as exc:
        raise RuntimeUnavailable(str(exc)) from None
    if mode != "memory":
        return LocalRuntime(_get_postgres_runtime(), lambda: st.session_state.get("auth_token"))
    return _get_local_runtime(environment)


def _clear_runtime_cache():
    _get_local_runtime.clear()
    _get_postgres_runtime.clear()


get_streamlit_runtime.clear = _clear_runtime_cache


def render_runtime_error(error: RuntimeUnavailable) -> None:
    LOGGER.error("RoomFlow persistence failed: %s", error)
    st.error(str(error))
    if st.button("Tentar novamente", key="roomflow_runtime_retry"):
        st.rerun()


def get_streamlit_actor(user_view: dict | None = None):
    """Resolve the current page user against server-side account state."""
    del user_view
    token = st.session_state.get("auth_token")
    if not token:
        return None
    try:
        return get_streamlit_runtime().authentication.authenticate(token)
    except InvalidSession:
        return None
    except RuntimeUnavailable as exc:
        render_runtime_error(exc)
        st.stop()

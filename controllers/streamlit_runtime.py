import os

import streamlit as st

from application.services.authentication_service import InvalidSession
from controllers.roomflow_api import ApiRuntime, ApiUnavailable, RoomFlowApi
from infrastructure.authentication_factory import InMemoryApplicationRuntime, build_application_runtime


API_PAGES = frozenset({
    "admin_dashboard", "usuarios", "historico_admin", "configuracoes_instituicao",
    "permissoes", "planta_instituicao", "espacos", "conta",
    "nova_reserva", "minhas_reservas", "gerente_reservas", "gerente_conflitos",
    "gerente_dashboard", "ocupacao", "notificacoes",
})


def uses_roomflow_api() -> bool:
    return bool(os.getenv("ROOMFLOW_API_URL", "").strip())


@st.cache_resource
def _get_local_runtime(environment: str) -> InMemoryApplicationRuntime:
    return build_application_runtime(environment)


@st.cache_resource
def _get_api_runtime(url: str) -> ApiRuntime:
    return ApiRuntime(RoomFlowApi(url, lambda: st.session_state.get("auth_token")))


def get_streamlit_runtime() -> InMemoryApplicationRuntime | ApiRuntime:
    if uses_roomflow_api():
        return _get_api_runtime(os.environ["ROOMFLOW_API_URL"].strip())
    environment = os.getenv("APP_ENV", "development").strip().lower()
    return _get_local_runtime(environment)


get_streamlit_runtime.clear = _get_local_runtime.clear


def render_api_error(error: ApiUnavailable) -> None:
    st.error(str(error))
    if st.button("Tentar novamente", key="roomflow_api_retry"):
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
    except ApiUnavailable as exc:
        render_api_error(exc)
        st.stop()

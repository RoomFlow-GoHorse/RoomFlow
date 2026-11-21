import os

import streamlit as st

from application.services.authentication_service import InvalidSession
from infrastructure.authentication_factory import InMemoryApplicationRuntime, build_application_runtime


@st.cache_resource
def get_streamlit_runtime() -> InMemoryApplicationRuntime:
    """Shared process-local application services for Streamlit pages."""
    environment = os.getenv("APP_ENV", "development").strip().lower()
    return build_application_runtime(environment)


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

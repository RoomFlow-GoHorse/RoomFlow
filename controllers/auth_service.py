import streamlit as st

from application.services.authentication_service import InvalidCredentials, InvalidSession
from controllers.streamlit_runtime import get_streamlit_runtime


def login(email, password):
    email = email.strip().lower()
    if not email or not password:
        return None, "E-mail ou senha incorretos. Verifique seus dados e tente novamente."
    try:
        result = get_streamlit_runtime().authentication.login(
            email, password, attempt_key="streamlit-local"
        )
    except InvalidCredentials:
        return None, "E-mail ou senha incorretos. Verifique seus dados e tente novamente."

    account = result.user
    session_user = {
        "id": account.id,
        "name": account.name,
        "email": account.email,
        "role": account.profile.value,
        "status": account.status.value,
        "institution_id": account.institution_id,
        "initials": "".join(part[0] for part in account.name.split()[:2]).upper(),
    }
    st.session_state.auth_token = result.access_token
    st.session_state.user = session_user
    return session_user, ""


def logout():
    token = st.session_state.get("auth_token")
    if token:
        try:
            get_streamlit_runtime().authentication.logout(token)
        except InvalidSession:
            pass
    st.session_state.auth_token = None
    st.session_state.user = None
    st.session_state.page = "landing"
    st.query_params.clear()
    st.query_params["page"] = "landing"
    st.rerun()

import streamlit as st

from application.services.authentication_service import (
    InstitutionSelectionRequired,
    InvalidCredentials,
    InvalidSession,
    TooManyLoginAttempts,
)
from controllers.roomflow_api import ApiUnavailable
from controllers.streamlit_runtime import get_streamlit_runtime
from models.domain.identity_normalization import normalize_email


def login(email, password, institution_id=None):
    email = normalize_email(email or "")
    if not email or not password:
        return None, "E-mail ou senha incorretos. Verifique seus dados e tente novamente."
    try:
        result = get_streamlit_runtime().authentication.login(
            email, password, attempt_key="streamlit-local", institution_id=institution_id
        )
    except InstitutionSelectionRequired as exc:
        st.session_state["login_institutions"] = exc.institution_ids
        return None, "Selecione a instituição para acessar."
    except InvalidCredentials:
        return None, "E-mail ou senha incorretos. Verifique seus dados e tente novamente."
    except TooManyLoginAttempts:
        return None, "Muitas tentativas de login. Aguarde um minuto e tente novamente."
    except (ApiUnavailable, ValueError) as exc:
        return None, str(exc)

    st.session_state.pop("login_institutions", None)
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
        except ApiUnavailable as exc:
            st.error(str(exc))
            return
    st.session_state.auth_token = None
    st.session_state.user = None
    st.session_state.page = "landing"
    st.query_params.clear()
    st.query_params["page"] = "landing"
    st.rerun()

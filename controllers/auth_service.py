import hashlib

import streamlit as st

from application.services.authentication_service import (
    InstitutionSelectionRequired,
    InvalidCredentials,
    InvalidSession,
    TooManyLoginAttempts,
)
from controllers.app_state_service import clear_operational_dialogs
from controllers.runtime_errors import RuntimeUnavailable
from controllers.streamlit_runtime import get_streamlit_runtime
from models.domain.identity_normalization import normalize_email


def login(email, password, institution_id=None):
    email = normalize_email(email or "")
    if not email or not password:
        return None, "E-mail ou senha incorretos. Verifique seus dados e tente novamente."
    try:
        result = get_streamlit_runtime().authentication.login(
            email, password, attempt_key="streamlit-login:" + hashlib.sha256(email.encode()).hexdigest(), institution_id=institution_id
        )
    except InstitutionSelectionRequired as exc:
        st.session_state["login_institutions"] = exc.institution_ids
        return None, "Selecione a instituição para acessar."
    except InvalidCredentials:
        return None, "E-mail ou senha incorretos. Verifique seus dados e tente novamente."
    except TooManyLoginAttempts:
        return None, "Muitas tentativas de login. Aguarde um minuto e tente novamente."
    except (RuntimeUnavailable, ValueError) as exc:
        return None, str(exc)
    except Exception as exc:
        # Streamlit can retain cached services while reloading modules. In that
        # case the exception class may have the same canonical name but a
        # different identity from this script run's imported class.
        error_type = type(exc)
        if (
            error_type.__name__ == InvalidCredentials.__name__
            and error_type.__module__ == InvalidCredentials.__module__
        ):
            return None, "E-mail ou senha incorretos. Verifique seus dados e tente novamente."
        raise

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
        except RuntimeUnavailable as exc:
            st.error(str(exc))
            return
    st.session_state.auth_token = None
    st.session_state.user = None
    clear_operational_dialogs()
    st.session_state.page = "landing"
    st.query_params.clear()
    st.query_params["page"] = "landing"
    st.rerun()

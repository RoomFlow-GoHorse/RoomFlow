import streamlit as st

from models.store import initialize_data


def boot_state():
    initialize_data(st.session_state)
    defaults = {
        "page": "landing",
        "user": None,
        "agenda_view": "Semana",
        "toast": "",
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def go(page):
    st.session_state.page = page
    st.query_params["page"] = page
    st.rerun()


def current_user():
    return st.session_state.get("user")


def set_toast(message):
    st.session_state.toast = message


def model_state():
    """Fornece o armazenamento da sessão aos controllers."""
    return st.session_state

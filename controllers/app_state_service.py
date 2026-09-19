import copy
import streamlit as st

from models import mock_data


def boot_state():
    defaults = {
        "page": "landing",
        "user": None,
        "reservations": copy.deepcopy(mock_data.RESERVATIONS),
        "spaces": copy.deepcopy(mock_data.SPACES),
        "users": copy.deepcopy(mock_data.USERS),
        "resources": copy.deepcopy(mock_data.RESOURCES),
        "institutions": copy.deepcopy(mock_data.INSTITUTIONS),
        "notifications": copy.deepcopy(mock_data.NOTIFICATIONS),
        "conflicts": copy.deepcopy(mock_data.CONFLICTS),
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

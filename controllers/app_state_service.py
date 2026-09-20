import copy
import streamlit as st

from models import mock_data


def boot_state():
    simple_defaults = {
        "page": "landing",
        "user": None,
        "agenda_view": "Semana",
        "toast": "",
    }
    for key, value in simple_defaults.items():
        st.session_state.setdefault(key, value)

    deep_defaults = {
        "reservations": mock_data.RESERVATIONS,
        "spaces": mock_data.SPACES,
        "users": mock_data.USERS,
        "resources": mock_data.RESOURCES,
        "institutions": mock_data.INSTITUTIONS,
        "notifications": mock_data.NOTIFICATIONS,
        "conflicts": mock_data.CONFLICTS,
    }
    for key, source in deep_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = copy.deepcopy(source)


def go(page):
    st.session_state.page = page
    st.query_params["page"] = page


def current_user():
    return st.session_state.get("user")


def set_toast(message):
    st.session_state.toast = message

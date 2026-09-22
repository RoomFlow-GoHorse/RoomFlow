import copy
import streamlit as st

from models import mock_data
from models.mock_data import USERS


def _recover_user_from_query():
    """Re-hydrates the authenticated user after a browser refresh.

    On refresh the WebSocket (and session_state) is recreated from scratch,
    but st.query_params survives. If 'uid' is present in the URL we look up
    the user in mock data so the session feels uninterrupted.
    """
    uid = st.query_params.get("uid")
    if not uid:
        return None
    return next((u for u in USERS if u.get("id") == uid), None)


def _clear_occupancy_modal_state():
    """Ensure modal state for the occupancy page does not leak across navigation."""
    st.session_state.pop("occupancy_detail_id", None)
    st.session_state.pop("occupancy_edit_id", None)
    st.session_state.pop("occupancy_reservation_selector", None)


def boot_state():
    simple_defaults = {
        "page": "landing",
        "user": None,
        "agenda_view": "Semana",
        "toast": "",
    }
    for key, value in simple_defaults.items():
        st.session_state.setdefault(key, value)

    # Recover authenticated user after a browser refresh.
    if st.session_state.user is None:
        recovered = _recover_user_from_query()
        if recovered:
            session_user = {k: v for k, v in recovered.items() if k != "password_hash"}
            st.session_state.user = session_user

    deep_defaults = {
        "reservations": mock_data.RESERVATIONS,
        "spaces": mock_data.SPACES,
        "buildings": mock_data.BUILDINGS,
        "floors": mock_data.FLOORS,
        "plans": {},
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
    """Navega imediatamente para uma rota pública ou interna."""
    st.session_state.page = page
    _clear_occupancy_modal_state()
    st.query_params["page"] = page
    st.rerun()


def go_authenticated(page, user):
    """Navigate to an internal page and persist the user id in the URL."""
    st.session_state.page = page
    _clear_occupancy_modal_state()
    st.query_params["page"] = page
    st.query_params["uid"] = user["id"]
    st.rerun()


def current_user():
    return st.session_state.get("user")


def set_toast(message):
    st.session_state.toast = message

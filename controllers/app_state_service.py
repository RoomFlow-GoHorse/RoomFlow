import copy
import streamlit as st

from models import mock_data
from controllers.streamlit_runtime import get_streamlit_actor


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
    """Navigate after authentication without putting identity in the URL."""
    del user
    st.session_state.page = page
    _clear_occupancy_modal_state()
    st.query_params["page"] = page
    if "uid" in st.query_params:
        del st.query_params["uid"]
    st.rerun()


def current_user():
    actor = get_streamlit_actor()
    if actor is None:
        st.session_state.user = None
        st.session_state.auth_token = None
        return None
    initials = "".join(part[0] for part in actor.name.split()[:2]).upper()
    user_view = {
        "id": actor.id,
        "name": actor.name,
        "email": actor.email,
        "role": actor.profile.value,
        "status": actor.status.value,
        "institution_id": actor.institution_id,
        "initials": initials,
    }
    st.session_state.user = user_view
    return user_view


def set_toast(message):
    st.session_state.toast = message

import copy
import streamlit as st

from models import mock_data
from controllers.streamlit_runtime import get_streamlit_actor, uses_persistent_runtime


def clear_operational_dialogs():
    for key in (
        "occupancy_detail_id", "occupancy_reservation_selector", "reservation_dialog",
        "edit_space_id", "block_space_id", "resolve_conflict_id",
    ):
        st.session_state.pop(key, None)


def boot_state():
    simple_defaults = {
        "page": "landing",
        "user": None,
        "agenda_view": "Semana",
        "toast": "",
    }
    for key, value in simple_defaults.items():
        st.session_state.setdefault(key, value)

    if uses_persistent_runtime():
        return

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
    clear_operational_dialogs()
    st.query_params["page"] = page
    st.rerun()


def go_authenticated(page, user):
    """Navigate after authentication without putting identity in the URL."""
    del user
    st.session_state.page = page
    clear_operational_dialogs()
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
        "phone": getattr(actor, "phone", None),
        "role": actor.profile.value,
        "status": actor.status.value,
        "institution_id": actor.institution_id,
        "initials": initials,
    }
    st.session_state.user = user_view
    return user_view


def set_toast(message):
    st.session_state.toast = message

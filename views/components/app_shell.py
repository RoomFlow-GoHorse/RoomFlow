import streamlit as st

from views.components.sidebar import render_sidebar


def shell_start(user, wide=False):
    """Renders the shared sidebar and returns the authenticated page container."""
    render_sidebar(user)
    container_key = "rf_page_container_wide" if wide else "rf_page_container"
    return st.container(key=container_key)


def shell_end():
    """Keeps the shared app-shell call site stable for the page router."""

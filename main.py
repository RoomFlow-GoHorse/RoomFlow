"""Ponto de entrada do RoomFlow."""

import streamlit as st

from controllers.app_controller import render_page
from services.app_state_service import boot_state
from views.components.ui_components import load_css, toast


def main():
    st.set_page_config(
        page_title="RoomFlow",
        page_icon="R",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    boot_state()
    load_css()
    toast()
    render_page()


if __name__ == "__main__":
    main()

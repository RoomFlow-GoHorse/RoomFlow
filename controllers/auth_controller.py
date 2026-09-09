"""Controla a autenticação e a sessão do usuário."""

import streamlit as st

from models.auth_model import authenticate
from services.app_state_service import model_state


def login(email, password):
    user, error = authenticate(model_state(), email, password)
    if user is not None:
        st.session_state.user = user
    return user, error


def logout():
    st.session_state.user = None
    st.session_state.page = "landing"
    st.rerun()

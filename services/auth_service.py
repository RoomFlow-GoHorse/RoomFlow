import streamlit as st

from data.mock_data import USERS


def login(email, password):
    if not password:
        return None, "E-mail ou senha incorretos. Verifique seus dados e tente novamente."
    user = next((item for item in USERS if item["email"].lower() == email.lower()), None)
    if not user:
        return None, "Nao encontramos uma conta com esses dados. Confirme seu cadastro com a instituicao."
    if user["status"] != "ativo":
        return None, "Esta conta esta inativa. Entre em contato com a instituicao."
    st.session_state.user = user.copy()
    return user, ""


def logout():
    st.session_state.user = None
    st.session_state.page = "landing"
    st.rerun()

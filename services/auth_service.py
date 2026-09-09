import streamlit as st

from data.mock_data import USERS, password_hash


def login(email, password):
    email = email.strip().lower()

    if not email or not password:
        return None, "E-mail ou senha incorretos. Verifique seus dados e tente novamente."

    user = next((item for item in USERS if item["email"].lower() == email), None)
    if not user:
        return None, "Não encontramos uma conta com esses dados. Confirme seu cadastro com a instituição."
    if user.get("password_hash") != password_hash(password):
        return None, "E-mail ou senha incorretos. Verifique seus dados e tente novamente."
    if user["status"] != "ativo":
        return None, "Esta conta está inativa. Entre em contato com a instituição."

    session_user = {key: value for key, value in user.items() if key != "password_hash"}
    st.session_state.user = session_user
    return session_user, ""


def logout():
    st.session_state.user = None
    st.session_state.page = "landing"
    st.query_params.clear()
    st.query_params["page"] = "landing"
    st.rerun()

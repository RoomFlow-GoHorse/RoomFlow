import streamlit as st

from config.constants import ROLE_LABELS
from views.components.ui_components import page_header


def account(user):
    page_header("Configuracoes da conta", "Dados pessoais e preferencias visuais.")
    with st.form("account"):
        st.text_input("Nome", value=user["name"])
        st.text_input("E-mail", value=user["email"])
        st.text_input("Perfil", value=ROLE_LABELS[user["role"]], disabled=True)
        st.checkbox("Receber notificacoes por e-mail", value=True)
        if st.form_submit_button("Salvar ajustes", type="primary"):
            st.success("Preferencias salvas no estado mockado.")

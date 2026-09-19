import streamlit as st

from services import mock_data_service
from views.components.ui_components import page_header


def settings(user):
    page_header(
        "Configuracoes da instituicao",
        "Dados institucionais disponiveis para administracao.",
    )

    institutions = mock_data_service.institutions()
    institution_name = institutions[0] if institutions else "Instituicao nao cadastrada"

    with st.form("institution_settings"):
        st.text_input("Instituicao", value=institution_name, disabled=True)
        st.text_input("Administrador responsavel", value=user.get("name", ""), disabled=True)
        st.text_input("E-mail do administrador", value=user.get("email", ""), disabled=True)
        st.form_submit_button("Salvar alteracoes", disabled=True)

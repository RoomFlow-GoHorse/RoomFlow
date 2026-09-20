import streamlit as st

from config.constants import ROLE_LABELS
from controllers import mock_data_service
from views.components.ui_components import badge, page_header, table


def users_page(user):
    page_header("Usuarios", "Administracao de membros e perfis.")
    rows = [[u["name"], u["email"], ROLE_LABELS[u["role"]], badge(u["status"])] for u in mock_data_service.users()]
    table(["Nome", "E-mail", "Perfil", "Status"], rows)
    for u in mock_data_service.users():
        if st.button(f"Ativar/Desativar {u['name']}", key=f"user_{u['id']}"):
            mock_data_service.toggle_user(u["id"])
            st.rerun()

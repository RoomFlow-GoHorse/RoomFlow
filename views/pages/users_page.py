from controllers import user_controller
import streamlit as st

from config.constants import ROLE_LABELS
from views.components.ui_components import badge, page_header, table


def users_page(user):
    page_header("Usuarios", "Administracao de membros e perfis.")
    rows = [[u["name"], u["email"], ROLE_LABELS[u["role"]], badge(u["status"])] for u in user_controller.users()]
    table(["Nome", "E-mail", "Perfil", "Status"], rows)
    for u in user_controller.users():
        if st.button(f"Ativar/Desativar {u['name']}", key=f"user_{u['id']}"):
            user_controller.toggle_user(u["id"])
            st.rerun()

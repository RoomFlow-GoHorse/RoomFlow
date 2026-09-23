import pandas as pd
import streamlit as st

from config.constants import ROLE_LABELS
from controllers import mock_data_service
from controllers.app_state_service import go
from views.components.ui_components import page_header


ROLE_CONFIG = [
    ("admin", "Governança, usuários e configurações"),
    ("gerente", "Gestão operacional de espaços e reservas"),
    ("solicitante", "Criação e acompanhamento de reservas"),
    ("participante", "Consulta de agenda e espaços"),
]

QUICK_ACTIONS = [
    ("Gerenciar usuários", "Criar, editar e ativar contas de acesso", "usuarios", ":material/group:"),
    ("Permissões", "Matriz de permissões por perfil de acesso", "permissoes", ":material/shield:"),
    ("Configurações", "Políticas, regras e preferências do sistema", "configuracoes_instituicao", ":material/settings:"),
]


def _navigate(page: str) -> None:
    go(page)
    st.rerun()


def _user_stats(users: list[dict]) -> dict[str, int]:
    return {
        "active": sum(user["status"] == "ativo" for user in users),
        "inactive": sum(user["status"] == "inativo" for user in users),
        "total": len(users),
    }


def _render_stats(users: list[dict]) -> None:
    stats = _user_stats(users)
    for column, label, value, delta, delta_color in zip(
        st.columns(3, gap="small"),
        ("Usuários ativos", "Usuários inativos", "Total de usuários"),
        (stats["active"], stats["inactive"], stats["total"]),
        ("Ativos", "Requer atenção", "Contas cadastradas"),
        ("normal", "off", "off"),
    ):
        with column.container(border=True):
            st.metric(label, value, delta=delta, delta_color=delta_color)


def _render_quick_actions() -> None:
    st.subheader("Ações rápidas")
    for label, description, page, icon in QUICK_ACTIONS:
        with st.container(border=True):
            st.markdown(f"{icon} **{label}**")
            st.caption(description)
            if st.button("Abrir", key=f"quick_action_{page}", icon=":material/arrow_forward:"):
                _navigate(page)


def _render_role_distribution(users: list[dict]) -> None:
    st.subheader("Distribuição por perfil")
    if st.button("Gerenciar usuários", key="distribution_manage", icon=":material/group:"):
        _navigate("usuarios")

    counts = {role: sum(user["role"] == role for user in users) for role, _ in ROLE_CONFIG}
    total = len(users)
    with st.container(border=True):
        for role, description in ROLE_CONFIG:
            count = counts[role]
            percentage = count / total if total else 0
            label_column, count_column = st.columns([5, 1], vertical_alignment="center")
            with label_column:
                st.markdown(f"**{ROLE_LABELS[role]}**")
                st.caption(description)
            with count_column:
                st.markdown(f"**{count}**")
                st.caption(f"{percentage:.0%}")
            st.progress(percentage, text=f"{percentage:.0%} dos usuários")


def _render_recent_users(users: list[dict]) -> None:
    header, action = st.columns([5, 1], vertical_alignment="center")
    with header:
        st.subheader("Usuários recentes")
    with action:
        if st.button("Ver todos", key="recent_users_all", icon=":material/arrow_forward:"):
            _navigate("usuarios")

    rows = [
        {
            "Nome": user["name"],
            "E-mail": user["email"],
            "Perfil": ROLE_LABELS.get(user["role"], user["role"]),
            "Status": "Ativo" if user["status"] == "ativo" else "Inativo",
        }
        for user in users[:5]
    ]
    st.dataframe(
        pd.DataFrame(rows),
        column_config={
            "Nome": st.column_config.TextColumn("Nome", width="medium"),
            "E-mail": st.column_config.TextColumn("E-mail", width="large"),
            "Perfil": st.column_config.TextColumn("Perfil", width="medium"),
            "Status": st.column_config.TextColumn("Status", width="small"),
        },
        hide_index=True,
        width="stretch",
    )


def dashboard(user):
    page_header("Painel de gerência", "Controle de usuários, permissões e configurações.")
    users = mock_data_service.users()

    _render_stats(users)
    st.space("small")

    actions, distribution = st.columns([1, 2], gap="medium")
    with actions:
        _render_quick_actions()
    with distribution:
        _render_role_distribution(users)

    st.space("small")
    _render_recent_users(users)

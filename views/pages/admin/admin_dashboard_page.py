import pandas as pd
import streamlit as st

from config.constants import ROLE_LABELS
from controllers.app_state_service import set_page
from controllers.streamlit_runtime import get_streamlit_actor, get_streamlit_runtime
from models.domain.exceptions import DomainAuthorizationError
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


def _render_user_stats(metrics) -> None:
    indicators = (
        ("Usuários ativos", metrics.users.active, "Contas ativas", "normal"),
        ("Usuários inativos", metrics.users.inactive, "Requer atenção", "off"),
        ("Total de usuários", metrics.users.total, "Na instituição", "off"),
        (f"Cadastros em {metrics.period_days} dias", metrics.recent_user_count, "Com data registrada", "off"),
    )
    for column, (label, value, delta, color) in zip(st.columns(4, gap="small"), indicators):
        with column.container(border=True):
            st.metric(label, value, delta=delta, delta_color=color)


def _render_structure_stats(metrics) -> None:
    indicators = (
        ("Prédios", metrics.buildings),
        ("Andares", metrics.floors),
        ("Salas", metrics.spaces),
        ("Recursos", metrics.resources),
    )
    for column, (label, counts) in zip(st.columns(4, gap="small"), indicators):
        with column.container(border=True):
            st.metric(
                label,
                counts.total,
                delta=f"{counts.active} ativos · {counts.inactive} inativos",
                delta_color="off",
            )


def _render_quick_actions() -> None:
    st.subheader("Ações rápidas")
    for label, description, page, icon in QUICK_ACTIONS:
        with st.container(border=True):
            col_info, col_btn = st.columns([3, 1], vertical_alignment="center")
            with col_info:
                st.markdown(f"{icon} **{label}**")
            with col_btn:
                st.button(
                    "Abrir", key=f"quick_action_{page}", icon=":material/arrow_forward:", use_container_width=True,
                    on_click=set_page, args=(page,),
                )
            st.caption(description)


def _role_bar(label: str, count: int, total: int) -> None:
    columns = st.columns([1.5, 3.5, 0.4], vertical_alignment="center")
    columns[0].caption(label)
    columns[1].progress(count / total if total else 0.0, text=None)
    columns[2].write(f"**{count}**")


def _render_role_distribution(metrics) -> None:
    st.html("""
        <style>
        div[data-testid="stButton"] button[key="distribution_manage"] {
            background-color: #7C3AED !important; color: #FFFFFF !important; border: none !important;
        }
        div[data-testid="stButton"] button[key="distribution_manage"]:hover {
            background-color: #6D28D9 !important; color: #FFFFFF !important;
        }
        </style>
    """)
    header, action = st.columns([1, 0.3], vertical_alignment="center")
    header.subheader("Distribuição por perfil")
    action.button(
        "Gerenciar", key="distribution_manage", icon=":material/group:", type="primary", use_container_width=True,
        on_click=set_page, args=("usuarios",),
    )

    with st.container(border=True):
        counts = {
            row.profile.value: row.count
            for row in metrics.users_by_profile
        }
        for role, _ in ROLE_CONFIG:
            _role_bar(ROLE_LABELS[role], counts.get(role, 0), metrics.users.total)
        if not metrics.users.total:
            st.info("Ainda não há usuários cadastrados nesta instituição.")
            return
        most_common = max(ROLE_CONFIG, key=lambda role: counts.get(role[0], 0))[0]
        percentage = counts.get(most_common, 0) / metrics.users.total * 100
        st.divider()
        st.caption(
            f"Perfil com maior presença: **{ROLE_LABELS[most_common]}** ({percentage:.0f}% do total)"
        )


def _render_recent_users(metrics) -> None:
    header, action = st.columns([5, 1], vertical_alignment="center")
    header.subheader("Usuários recentes")
    action.button(
        "Ver todos", key="recent_users_all", icon=":material/arrow_forward:", use_container_width=True,
        on_click=set_page, args=("usuarios",),
    )

    if not metrics.recent_users:
        st.info(
            f"Não há cadastros com data registrada nos últimos {metrics.period_days} dias. "
            "Registros antigos sem data não aparecem nesta lista."
        )
        return

    rows = [
        {
            "Nome": item.name,
            "E-mail": item.email,
            "Perfil": ROLE_LABELS.get(item.profile.value, item.profile.value),
            "Status": "Ativo" if item.active else "Inativo",
            "Cadastro": item.created_at.astimezone().strftime("%d/%m/%Y %H:%M"),
        }
        for item in metrics.recent_users
    ]
    if metrics.recent_user_count > len(rows):
        st.caption(f"Exibindo os {len(rows)} mais recentes de {metrics.recent_user_count} cadastros no período.")
    st.dataframe(
        pd.DataFrame(rows),
        column_config={
            "Nome": st.column_config.TextColumn("Nome", width="medium"),
            "E-mail": st.column_config.TextColumn("E-mail", width="large"),
            "Perfil": st.column_config.TextColumn("Perfil", width="medium"),
            "Status": st.column_config.TextColumn("Status", width="small"),
            "Cadastro": st.column_config.TextColumn("Cadastro", width="medium"),
        },
        hide_index=True,
        width="stretch",
    )


def dashboard(user):
    page_header("Painel administrativo", "Indicadores da instituição e acesso às configurações.")
    actor = get_streamlit_actor()
    if actor is None:
        st.error("Sua sessão expirou. Entre novamente para visualizar o painel.")
        return

    period_days = st.selectbox(
        "Período de cadastros recentes",
        options=[7, 30, 90],
        index=1,
        format_func=lambda days: f"Últimos {days} dias",
        key="admin_dashboard_recent_period",
    )
    try:
        metrics = get_streamlit_runtime().admin_dashboard.get_metrics(actor, period_days)
    except (DomainAuthorizationError, ValueError) as exc:
        st.error(str(exc))
        return

    _render_user_stats(metrics)
    st.space("small")
    _render_structure_stats(metrics)
    st.space("small")

    actions, distribution = st.columns([1, 2], gap="medium")
    with actions:
        _render_quick_actions()
    with distribution:
        _render_role_distribution(metrics)

    st.space("small")
    _render_recent_users(metrics)
    st.space("small")
    with st.container(border=True):
        st.subheader("Reservas e ocupação")
        st.info("Estes indicadores ficarão disponíveis quando o módulo de reservas estiver integrado.")

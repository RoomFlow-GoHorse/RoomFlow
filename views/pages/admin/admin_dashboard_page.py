import streamlit as st

from config.constants import ROLE_LABELS
from controllers import mock_data_service
from controllers.app_state_service import go
from views.components.ui_components import page_header


# =========================================================
# CONFIGURAÇÕES
# =========================================================

ROLE_CONFIG = [
    {
        "key": "admin",
        "label": "Administrador",
        "description": "Governança, usuários e configurações",
    },
    {
        "key": "gerente",
        "label": "Gerente",
        "description": "Gestão operacional de espaços e reservas",
    },
    {
        "key": "solicitante",
        "label": "Solicitante",
        "description": "Criação e acompanhamento de reservas",
    },
    {
        "key": "participante",
        "label": "Participante",
        "description": "Consulta de agenda e espaços",
    },
]


QUICK_ACTIONS = [
    {
        "icon": "👥",
        "label": "Gerenciar usuários",
        "description": "Criar, editar e ativar contas de acesso",
        "page": "usuarios",
        "color": "background:#EDE9FE; color:#6D28D9;",
    },
    {
        "icon": "🛡",
        "label": "Permissões",
        "description": "Matriz de permissões por perfil de acesso",
        "page": "permissoes",
        "color": "background:#FEF3C7; color:#B45309;",
    },
    {
        "icon": "⚙",
        "label": "Configurações",
        "description": "Políticas, regras e preferências do sistema",
        "page": "configuracoes_instituicao",
        "color": "background:#F0EEE9; color:#52525B;",
    },
]


ROLE_BADGE_STYLES = {
    "admin": "background:#EDE9FE; color:#6D28D9;",
    "gerente": "background:#FEF3C7; color:#B45309;",
    "solicitante": "background:#F4F4F5; color:#52525B;",
    "participante": "background:#F4F4F5; color:#52525B;",
}


# =========================================================
# HELPERS
# =========================================================

def _navigate(page: str) -> None:
    """Navega para outra página."""
    go(page)
    st.rerun()


def _avatar_html(initials: str, size: int = 28) -> str:
    """Cria o avatar circular do usuário."""
    return (
        f'<span style="'
        f"display:inline-flex;"
        f"align-items:center;"
        f"justify-content:center;"
        f"width:{size}px;"
        f"height:{size}px;"
        f"border-radius:50%;"
        f"background:#EDE9FE;"
        f"color:#6D28D9;"
        f"font-size:11px;"
        f"font-weight:700;"
        f"flex-shrink:0;"
        f'">{initials}</span>'
    )


def _role_badge_html(role: str) -> str:
    """Cria o badge visual do perfil."""
    label = ROLE_LABELS.get(role, role)

    style = ROLE_BADGE_STYLES.get(
        role,
        "background:#F4F4F5; color:#52525B;",
    )

    return (
        f'<span style="'
        f"display:inline-block;"
        f"padding:2px 10px;"
        f"border-radius:999px;"
        f"font-size:11px;"
        f"font-weight:600;"
        f"{style}"
        f'">{label}</span>'
    )


def _get_user_stats(users: list) -> dict:
    """Calcula as métricas principais."""
    return {
        "active": sum(
            1
            for user in users
            if user["status"] == "ativo"
        ),
        "inactive": sum(
            1
            for user in users
            if user["status"] == "inativo"
        ),
        "total": len(users),
    }


def _get_role_counts(users: list) -> dict:
    """Calcula a quantidade de usuários por perfil."""
    role_count = {}

    for user in users:
        role = user["role"]
        role_count[role] = role_count.get(role, 0) + 1

    return role_count


# =========================================================
# CARDS DE MÉTRICAS
# =========================================================

def _render_stat_card(
    label: str,
    value: int,
    value_color: str = "#1C1C2E",
) -> None:
    """Renderiza um card de métrica."""

    with st.container(border=True):

        st.html(
            f'<p style="'
            f"font-size:11px;"
            f"font-weight:600;"
            f"color:#A1A1AA;"
            f"text-transform:uppercase;"
            f"letter-spacing:0.06em;"
            f"margin:0 0 6px;"
            f'">{label}</p>'
        )

        st.html(
            f'<p style="'
            f"font-size:24px;"
            f"font-weight:600;"
            f"color:{value_color};"
            f"margin:0;"
            f'">{value}</p>'
        )


def _render_stats(users: list) -> None:
    """Renderiza os três cards de métricas."""

    stats = _get_user_stats(users)

    col1, col2, col3 = st.columns(
        3,
        gap="small",
    )

    with col1:
        _render_stat_card(
            "Usuários ativos",
            stats["active"],
            "#16A34A",
        )

    with col2:
        _render_stat_card(
            "Usuários inativos",
            stats["inactive"],
            "#A1A1AA",
        )

    with col3:
        _render_stat_card(
            "Total de usuários",
            stats["total"],
            "#1C1C2E",
        )


# =========================================================
# AÇÕES RÁPIDAS
# =========================================================

def _render_quick_action(action: dict) -> None:
    """Renderiza uma ação rápida."""

    with st.container(border=True):

        col_icon, col_text, col_arrow = st.columns(
            [1, 8, 1]
        )

        with col_icon:
            st.html(
                f'<div style="'
                f"width:40px;"
                f"height:40px;"
                f"border-radius:10px;"
                f"display:flex;"
                f"align-items:center;"
                f"justify-content:center;"
                f"font-size:18px;"
                f"{action['color']}"
                f'">{action["icon"]}</div>'
            )

        with col_text:
            st.html(
                f'<p style="'
                f"margin:0;"
                f"font-size:13px;"
                f"font-weight:600;"
                f"color:#1C1C2E;"
                f'">{action["label"]}</p>'
                f'<p style="'
                f"margin:2px 0 0;"
                f"font-size:12px;"
                f"color:#A1A1AA;"
                f'">{action["description"]}</p>'
            )

        with col_arrow:
            if st.button(
                "→",
                key=f"quick_action_{action['page']}",
                help=action["label"],
            ):
                _navigate(action["page"])


def _render_quick_actions() -> None:
    """Renderiza todas as ações rápidas."""

    st.markdown("**Ações rápidas**")

    for action in QUICK_ACTIONS:
        _render_quick_action(action)


# =========================================================
# DISTRIBUIÇÃO POR PERFIL
# =========================================================

def _render_role_distribution(users: list) -> None:
    """Renderiza a distribuição de usuários por perfil."""

    role_count = _get_role_counts(users)
    total_users = len(users)

    # Cabeçalho da seção
    header_left, header_right = st.columns(
        [3, 1]
    )

    with header_left:
        st.markdown("**Distribuição por perfil**")

    with header_right:
        if st.button(
            "Gerenciar →",
            key="distribution_manage",
            help="Ir para Usuários",
            use_container_width=True,
        ):
            _navigate("usuarios")

    # Card da distribuição
    with st.container(border=True):

        for role in ROLE_CONFIG:

            role_key = role["key"]

            count = role_count.get(
                role_key,
                0,
            )

            percentage = (
                round(
                    (count / total_users) * 100
                )
                if total_users
                else 0
            )

            col_label, col_bar, col_count = st.columns(
                [3, 6, 1]
            )

            # Nome e descrição
            with col_label:
                st.html(
                    f'<p style="'
                    f"font-size:12px;"
                    f"font-weight:500;"
                    f"color:#1C1C2E;"
                    f"margin:0;"
                    f'">{role["label"]}</p>'
                    f'<p style="'
                    f"font-size:11px;"
                    f"color:#A1A1AA;"
                    f"margin:0;"
                    f'">{role["description"]}</p>'
                )

            # Barra
            with col_bar:
                st.html(
                    f'<div style="'
                    f"margin-top:6px;"
                    f"height:8px;"
                    f"background:#EDE9FE;"
                    f"border-radius:999px;"
                    f"overflow:hidden;"
                    f'">'
                    f'<div style="'
                    f"height:100%;"
                    f"width:{percentage}%;"
                    f"background:#6D28D9;"
                    f"border-radius:999px;"
                    f'"></div>'
                    f"</div>"
                )

            # Quantidade
            with col_count:
                st.html(
                    f'<p style="'
                    f"font-size:13px;"
                    f"font-weight:600;"
                    f"color:#1C1C2E;"
                    f"margin:6px 0 0;"
                    f"text-align:right;"
                    f'">{count}</p>'
                )

            st.html(
                '<div style="height:8px;"></div>'
            )


# =========================================================
# USUÁRIOS RECENTES
# =========================================================

def _render_recent_users(users: list) -> None:
    """Renderiza a lista de usuários recentes."""

    header_left, header_right = st.columns(
        [5, 1]
    )

    with header_left:
        st.markdown("**Usuários recentes**")

    with header_right:
        if st.button(
            "Ver todos →",
            key="recent_users_all",
            help="Ir para Usuários",
            use_container_width=True,
        ):
            _navigate("usuarios")

    with st.container(border=True):

        # Cabeçalho da tabela
        columns = st.columns(
            [3, 3, 2, 2]
        )

        columns[0].caption("**Nome**")
        columns[1].caption("**E-mail**")
        columns[2].caption("**Perfil**")
        columns[3].caption("**Status**")

        st.divider()

        # Usuários
        for user in users[:5]:

            initials = user.get(
                "initials",
                user["name"][:2].upper(),
            )

            columns = st.columns(
                [3, 3, 2, 2]
            )

            # Nome
            with columns[0]:
                st.html(
                    f'<div style="'
                    f"display:flex;"
                    f"align-items:center;"
                    f"gap:8px;"
                    f"padding:2px 0;"
                    f'">'
                    f"{_avatar_html(initials)}"
                    f'<span style="'
                    f"font-size:13px;"
                    f"font-weight:600;"
                    f"color:#1C1C2E;"
                    f'">{user["name"]}</span>'
                    f"</div>"
                )

            # E-mail
            with columns[1]:
                st.html(
                    f'<p style="'
                    f"font-size:12px;"
                    f"color:#A1A1AA;"
                    f"margin:6px 0;"
                    f'">{user["email"]}</p>'
                )

            # Perfil
            with columns[2]:
                st.html(
                    f'<div style="padding:4px 0;">'
                    f"{_role_badge_html(user['role'])}"
                    f"</div>"
                )

            # Status
            with columns[3]:

                if user["status"] == "ativo":
                    st.html(
                        '<span style="'
                        'font-size:12px;'
                        'font-weight:500;'
                        'color:#16A34A;'
                        '">Ativo</span>'
                    )
                else:
                    st.html(
                        '<span style="'
                        'font-size:12px;'
                        'font-weight:500;'
                        'color:#A1A1AA;'
                        '">Inativo</span>'
                    )


# =========================================================
# PÁGINA PRINCIPAL
# =========================================================

def dashboard(user):

    # -----------------------------------------------------
    # HEADER
    # -----------------------------------------------------

    page_header(
        "Painel de gerência",
        "Controle de usuários, permissões e configurações.",
    )

    users = mock_data_service.users()

    # -----------------------------------------------------
    # MÉTRICAS
    # -----------------------------------------------------

    _render_stats(users)

    st.html(
        '<div style="height:12px;"></div>'
    )

    # -----------------------------------------------------
    # AÇÕES RÁPIDAS + DISTRIBUIÇÃO
    # -----------------------------------------------------

    col_left, col_right = st.columns(
        [1, 2],
        gap="medium",
    )

    # ESQUERDA
    with col_left:
        _render_quick_actions()

    # DIREITA
    with col_right:
        _render_role_distribution(users)

    st.html(
        '<div style="height:12px;"></div>'
    )

    # -----------------------------------------------------
    # USUÁRIOS RECENTES
    # -----------------------------------------------------

    _render_recent_users(users)


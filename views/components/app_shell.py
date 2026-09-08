import streamlit as st

from services import auth_service
from services.app_state_service import go
from services.mock_data_service import notifications_for
from views.components.ui_components import logo, role_label


NAV_GROUPS = {
    "admin": [
        [
            ("Início", "admin_dashboard", ":material/home:"),
            ("Reservas", "admin_reservas", ":material/calendar_month:"),
            ("Agenda", "agenda", ":material/schedule:"),
            ("Espaços", "espacos", ":material/location_on:"),
            ("Notificações", "notificacoes", ":material/notifications:"),
        ],
        [("Conflitos", "admin_conflitos", ":material/warning:")],
    ],
    "gerente": [
        [
            ("Início", "gerente_dashboard", ":material/home:"),
            ("Agenda", "agenda", ":material/schedule:"),
            ("Espaços", "espacos", ":material/location_on:"),
            ("Notificações", "notificacoes", ":material/notifications:"),
        ],
        [
            ("Usuários", "usuarios", ":material/group:"),
            ("Permissões", "permissoes", ":material/shield:"),
        ],
    ],
    "solicitante": [
        [
            ("Início", "solicitante_dashboard", ":material/home:"),
            ("Nova reserva", "nova_reserva", ":material/add_circle:"),
            ("Minhas reservas", "minhas_reservas", ":material/calendar_month:"),
            ("Agenda", "agenda", ":material/schedule:"),
            ("Notificações", "notificacoes", ":material/notifications:"),
        ]
    ],
    "participante": [
        [
            ("Início", "participante_dashboard", ":material/home:"),
            ("Agenda", "agenda", ":material/schedule:"),
            ("Notificações", "notificacoes", ":material/notifications:"),
            ("Localizar espaço", "localizar", ":material/location_on:"),
            ("Alterações", "alteracoes", ":material/history:"),
        ]
    ],
}


def _navigate(page):
    go(page)


def render_sidebar(user):
    current_page = st.session_state.page
    unread = sum(not item["read"] for item in notifications_for(user["role"]))

    with st.sidebar:
        st.html('<div class="rf-sidebar-logo">' + logo() + "</div>")
        st.html('<div class="rf-sidebar-section-label">Navegação</div>')

        for group_index, group in enumerate(NAV_GROUPS[user["role"]]):
            if group_index:
                st.html('<div class="rf-sidebar-divider"></div>')

            for label, page, icon in group:
                is_active = current_page == page
                notification_suffix = f" ({unread})" if page == "notificacoes" and unread else ""
                button_key = "rf_nav_active" if is_active else f"rf_nav_{page}"
                if st.button(
                    f"{label}{notification_suffix}",
                    key=button_key,
                    icon=icon,
                    type="primary" if is_active else "tertiary",
                    width="stretch",
                ):
                    _navigate(page)

        with st.container(key="rf_sidebar_footer"):
            st.html(
                f"""
                <div class="rf-user-summary">
                  <span class="rf-avatar">{user['initials']}</span>
                  <div>
                    <div class="rf-user-name">{user['name']}</div>
                    <div class="rf-user-role">{role_label(user['role'])}</div>
                  </div>
                </div>
                """
            )
            if st.button(
                "Configurações da conta",
                key="rf_account",
                icon=":material/account_circle:",
                type="tertiary",
                width="stretch",
            ):
                _navigate("conta")
            if st.button(
                "Sair",
                key="rf_logout",
                icon=":material/logout:",
                type="tertiary",
                width="stretch",
            ):
                auth_service.logout()


def shell_start(user):
    render_sidebar(user)


def shell_end():
    """Keeps the shared app-shell call site stable for the page router."""

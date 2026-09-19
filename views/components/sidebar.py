import streamlit as st

from config.constants import ROLE_NAV
from services import auth_service
from services.app_state_service import go
from services.mock_data_service import notifications_for
from views.components.ui_components import logo, role_label


NAV_GROUPS = {
    "admin": [
        [
            ("Início", "admin_dashboard", ":material/home:"),
            ("Usuários", "usuarios", ":material/group:"),
            ("Permissões", "permissoes", ":material/shield:"),
            ("Configurações da instituição", "configuracoes_instituicao", ":material/settings:"),
        ],
    ],
    "gerente": [
        [
            ("Início", "gerente_dashboard", ":material/home:"),
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
    current_page = st.session_state.get("page", "landing")
    role = user.get("role", "participante")
    allowed_pages = {page for _, page in ROLE_NAV.get(role, [])}
    unread = sum(not item["read"] for item in notifications_for(role))

    with st.sidebar:
        st.html('<div class="rf-sidebar-logo">' + logo() + "</div>")
        st.html('<div class="rf-sidebar-section-label">Navegação</div>')

        for group_index, group in enumerate(NAV_GROUPS.get(role, [])):
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
                  <span class="rf-avatar">{user.get('initials', '')}</span>
                  <div>
                    <div class="rf-user-name">{user.get('name', 'Usuário')}</div>
                    <div class="rf-user-role">{role_label(role)}</div>
                  </div>
                </div>
                """
            )
            if "conta" in allowed_pages:
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

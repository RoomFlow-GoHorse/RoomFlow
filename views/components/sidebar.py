import streamlit as st

from config.constants import ROLE_NAV
from controllers import auth_service
from controllers.app_state_service import go
from controllers.mock_data_service import notifications_for
from views.components.ui_components import logo, role_label


NAV_ICONS = {
    "admin_dashboard": ":material/home:",
    "gerente_dashboard": ":material/home:",
    "solicitante_dashboard": ":material/home:",
    "participante_dashboard": ":material/home:",
    "usuarios": ":material/group:",
    "permissoes": ":material/shield:",
    "configuracoes_instituicao": ":material/settings:",
    "nova_reserva": ":material/add_circle:",
    "minhas_reservas": ":material/calendar_month:",
    "agenda": ":material/schedule:",
    "notificacoes": ":material/notifications:",
    "localizar": ":material/location_on:",
    "conta": ":material/account_circle:",
}

NAV_LABEL_OVERRIDES = {
    "admin_dashboard": "Início",
    "gerente_dashboard": "Início",
    "solicitante_dashboard": "Início",
    "participante_dashboard": "Início",
    "usuarios": "Usuários",
    "permissoes": "Permissões",
    "configuracoes_instituicao": "Configurações",
    "notificacoes": "Notificações",
    "localizar": "Localizar espaço",
}


def _sidebar_items(role):
    for label, page in ROLE_NAV.get(role, []):
        yield (
            NAV_LABEL_OVERRIDES.get(page, label),
            page,
            NAV_ICONS.get(page, ":material/circle:"),
        )


def _navigate(page):
    go(page)


def render_sidebar(user):
    current_page = st.session_state.get("page", "landing")
    role = user.get("role", "participante")
    allowed_pages = {page for _, page in ROLE_NAV.get(role, [])}
    unread = sum(not item["read"] for item in notifications_for(role) if item.get("category") != "sistema")

    with st.sidebar:
        st.html('<div class="rf-sidebar-logo">' + logo() + "</div>")
        st.html('<div class="rf-sidebar-section-label">Navegação</div>')

        for label, page, icon in _sidebar_items(role):
            if page == "conta":
                continue

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
                    icon=NAV_ICONS["conta"],
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

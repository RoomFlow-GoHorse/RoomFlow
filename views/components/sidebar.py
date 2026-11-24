import logging

import streamlit as st

from config.constants import ROLE_NAV
from controllers import auth_service
from controllers.app_state_service import set_page
from controllers.streamlit_runtime import PERSISTENT_PAGES, get_streamlit_runtime, uses_persistent_runtime
from controllers.runtime_errors import RuntimeUnavailable
from models.domain.exceptions import DomainAuthorizationError
from views.components.ui_components import is_dark_theme, logo, role_label


NAV_ICONS = {
    "admin_dashboard": ":material/home:",
    "historico_admin": ":material/history:",
    "gerente_dashboard": ":material/home:",
    "solicitante_dashboard": ":material/home:",
    "participante_dashboard": ":material/home:",
    "usuarios": ":material/group:",
    "permissoes": ":material/shield:",
    "planta_instituicao": ":material/architecture:",
    "configuracoes_instituicao": ":material/settings:",
    "nova_reserva": ":material/add_circle:",
    "minhas_reservas": ":material/calendar_month:",
    "agenda": ":material/schedule:",
    "gerente_reservas": ":material/event_note:",
    "espacos": ":material/meeting_room:",
    "ocupacao": ":material/monitoring:",
    "gerente_conflitos": ":material/warning:",
    "notificacoes": ":material/notifications:",
    "localizar": ":material/location_on:",
    "conta": ":material/account_circle:",
}

NAV_LABEL_OVERRIDES = {
    "historico_admin": "Histórico administrativo",
    "admin_dashboard": "Início",
    "gerente_dashboard": "Início",
    "solicitante_dashboard": "Início",
    "participante_dashboard": "Início",
    "usuarios": "Usuários",
    "permissoes": "Permissões",
    "planta_instituicao": "Planta da instituição",
    "configuracoes_instituicao": "Configurações",
    "notificacoes": "Notificações",
    "localizar": "Localizar espaço",
}

LOGGER = logging.getLogger(__name__)


def _sidebar_items(role):
    for label, page in ROLE_NAV.get(role, []):
        yield (
            NAV_LABEL_OVERRIDES.get(page, label),
            page,
            NAV_ICONS.get(page, ":material/circle:"),
        )


def _sidebar_logo_variant():
    theme = getattr(st.context, "theme", None)
    theme_type = getattr(theme, "type", None) or getattr(theme, "base", None)
    if not theme_type and hasattr(theme, "get"):
        theme_type = theme.get("type") or theme.get("base")

    return "light" if theme_type == "dark" or is_dark_theme() else "dark"


def render_sidebar(user):
    current_page = st.session_state.get("page", "landing")
    role = user.get("role", "participante")
    allowed_pages = {page for _, page in ROLE_NAV.get(role, [])}
    notifications_unavailable = not uses_persistent_runtime()
    if uses_persistent_runtime():
        allowed_pages &= PERSISTENT_PAGES
        try:
            unread = get_streamlit_runtime().notifications.unread_count()
            notifications_unavailable = False
        except (DomainAuthorizationError, RuntimeUnavailable) as error:
            LOGGER.warning("Could not load the sidebar notification count: %s", error)
            unread = 0
            notifications_unavailable = True
    else:
        unread = 0

    with st.sidebar:
        with st.container(key="rf_sidebar_logo"):
            st.html(logo(size="small", variant=_sidebar_logo_variant()))

        st.divider()
        with st.container(key="rf_sidebar_navigation_label"):
            st.caption("Navegação")

        for label, page, icon in _sidebar_items(role):
            if page == "conta" or page not in allowed_pages:
                continue

            is_active = current_page == page
            notification_suffix = f" ({unread})" if page == "notificacoes" and unread else ""
            button_key = "rf_nav_active" if is_active else f"rf_nav_{page}"
            st.button(
                f"{label}{notification_suffix}",
                key=button_key,
                icon=icon,
                type="primary" if is_active else "tertiary",
                width="stretch",
                on_click=set_page,
                args=(page,),
            )
            if page == "notificacoes" and notifications_unavailable:
                st.caption("Notificações indisponíveis no momento.")

        with st.container(key="rf_sidebar_footer"):
            avatar_column, profile_column = st.columns(
                [1, 4],
                vertical_alignment="center",
            )
            with avatar_column:
                with st.container(key="rf_sidebar_avatar"):
                    st.markdown(f"**{user.get('initials', '')}**")
            with profile_column:
                with st.container(key="rf_sidebar_profile_text"):
                    st.markdown(f"**{user.get('name', 'Usuário')}**")
                    st.caption(role_label(role))
            if "conta" in allowed_pages:
                st.button(
                    "Configurações da conta",
                    key="rf_account",
                    icon=NAV_ICONS["conta"],
                    type="tertiary",
                    width="stretch",
                    on_click=set_page,
                    args=("conta",),
                )
            if st.button(
                "Sair",
                key="rf_logout",
                icon=":material/logout:",
                type="tertiary",
                width="stretch",
            ):
                auth_service.logout()

import streamlit as st

from config.constants import ROLE_NAV
from controllers.app_state_service import boot_state, current_user
from views.components.app_shell import shell_end, shell_start
from views.components.ui_components import load_auth_css, load_css, toast

from views.pages.admin import admin_dashboard_page, floor_plan_page, permissions_page, settings_page, users_page
from views.pages.auth import forgot_password_page, login_page, signup_choice_page, signup_institution_page, signup_member_page
from views.pages.manager import conflicts_page, manager_dashboard_page, occupancy_page, requests_page, spaces_page
from views.pages.participant import find_space_page, participant_dashboard_page
from views.pages.public import landing_page
from views.pages.requester import my_requests_page, new_request_page, requester_dashboard_page
from views.pages.shared import account_settings_page, agenda_page, notifications_page


# =========================================================
# CONFIGURAÇÃO
# =========================================================

st.set_page_config(
    page_title="RoomFlow",
    page_icon=":material/meeting_room:",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# INICIALIZAÇÃO
# =========================================================

boot_state()
load_css()
if st.session_state.get("page") != "planta_instituicao":
    toast()


# =========================================================
# ROTAS PÚBLICAS
# =========================================================

PUBLIC_ROUTES = {
    "landing": landing_page.landing,
    "login": login_page.login,

    # Cadastro
    "signup_choice": signup_choice_page.signup_choice,
    "signup_institution": signup_institution_page.signup_institution,
    "signup_member": signup_member_page.signup_member,

    # Recuperação
    "forgot_password": forgot_password_page.forgot_password,
}


# =========================================================
# ROTAS INTERNAS
# =========================================================

APP_ROUTES = {
    # Dashboards
    "admin_dashboard": admin_dashboard_page.dashboard,
    "gerente_dashboard": manager_dashboard_page.dashboard,
    "solicitante_dashboard": requester_dashboard_page.dashboard,
    "participante_dashboard": participant_dashboard_page.dashboard,

    # Agenda
    "agenda": agenda_page.agenda,

    # Reservas
    "admin_reservas": requests_page.reservations_admin,
    "gerente_reservas": requests_page.manager_reservations,
    "nova_reserva": new_request_page.new_reservation,
    "minhas_reservas": my_requests_page.minhas_reservas,

    # Conflitos
    "admin_conflitos": conflicts_page.conflicts,
    "gerente_conflitos": conflicts_page.conflicts,

    # Espaços
    "espacos": spaces_page.spaces,
    "ocupacao": occupancy_page.occupancy,
    "localizar": find_space_page.localizar,

    # Usuários e permissões
    "usuarios": users_page.users_page,
    "permissoes": permissions_page.permissions,
    "planta_instituicao": floor_plan_page.floor_plan,
    "configuracoes_instituicao": settings_page.settings,

    # Notificações
    "notificacoes": notifications_page.notifications,

    # Conta
    "conta": account_settings_page.account,
}


# Rotas cujo conteúdo precisa de uma área de trabalho maior, mas ainda segue
# o mesmo container global das demais telas internas.
WIDE_APP_ROUTES = {
    "admin_dashboard",
    "gerente_dashboard",
    "solicitante_dashboard",
    "participante_dashboard",
    "agenda",
    "admin_reservas",
    "gerente_reservas",
    "gerente_conflitos",
    "espacos",
    "ocupacao",
    "usuarios",
    "permissoes",
    "planta_instituicao",
    "configuracoes_instituicao",
}


# =========================================================
# SINCRONIZAÇÃO DA URL
# =========================================================

def sync_page_from_query():
    page = st.query_params.get("page")

    valid_routes = PUBLIC_ROUTES.keys() | APP_ROUTES.keys()

    if page in valid_routes:
        st.session_state.page = page


# =========================================================
# DASHBOARD POR PERFIL
# =========================================================

def get_dashboard_by_role(user):
    dashboard_by_role = {
        "admin": "admin_dashboard",
        "gerente": "gerente_dashboard",
        "solicitante": "solicitante_dashboard",
        "participante": "participante_dashboard",
    }

    return dashboard_by_role.get(
        user.get("role"),
        "participante_dashboard",
    )


def get_allowed_pages_by_role(role):
    return {page for _, page in ROLE_NAV.get(role, [])}


def ensure_allowed_internal_page(page, user):
    role = user.get("role")
    allowed_pages = get_allowed_pages_by_role(role)

    if page in allowed_pages:
        return page

    dashboard = get_dashboard_by_role(user)
    st.session_state.page = dashboard
    st.query_params["page"] = dashboard
    return dashboard


# =========================================================
# MAIN
# =========================================================

def main():
    sync_page_from_query()

    page = st.session_state.page
    user = current_user()

    # ---------------------------------------------------------
    # USUÁRIO NÃO AUTENTICADO
    # ---------------------------------------------------------

    if not user:
        page_function = PUBLIC_ROUTES.get(page)

        if page_function:
            if page != "landing":
                load_auth_css()
            page_function()
            return

        # Se tentar acessar uma rota interna sem estar autenticado,
        # volta para a landing page.
        PUBLIC_ROUTES["landing"]()
        return

    # ---------------------------------------------------------
    # USUÁRIO AUTENTICADO TENTANDO ACESSAR ROTA PÚBLICA
    # ---------------------------------------------------------

    if page in PUBLIC_ROUTES:
        page = get_dashboard_by_role(user)
        st.session_state.page = page

    # ---------------------------------------------------------
    # ROTAS INTERNAS
    # ---------------------------------------------------------

    page = ensure_allowed_internal_page(page, user)

    page_function = APP_ROUTES.get(
        page,
        manager_dashboard_page.dashboard,
    )

    with shell_start(user, wide=page in WIDE_APP_ROUTES):
        if page == "planta_instituicao":
            toast(width=360, aligned_right=True)
        page_function(user)

    shell_end()


# =========================================================
# EXECUÇÃO
# =========================================================

main()

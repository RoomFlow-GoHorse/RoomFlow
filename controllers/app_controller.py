import streamlit as st

from services.app_state_service import current_user
from views.components.app_shell import shell_end, shell_start

from views.pages import (
    account_settings_page,
    agenda_page,
    changes_page,
    conflicts_page,
    dashboard_page,
    forgot_password_page,
    landing_page,
    login_page,
    notifications_page,
    permissions_page,
    reservations_page,
    signup_choice_page,
    signup_institution_page,
    signup_member_page,
    spaces_page,
    users_page,
)


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
    "admin_dashboard": dashboard_page.dashboard,
    "gerente_dashboard": dashboard_page.dashboard,
    "solicitante_dashboard": dashboard_page.dashboard,
    "participante_dashboard": dashboard_page.dashboard,

    # Agenda
    "agenda": agenda_page.agenda,

    # Reservas
    "admin_reservas": reservations_page.reservations_admin,
    "nova_reserva": reservations_page.new_reservation,
    "minhas_reservas": reservations_page.minhas_reservas,

    # Conflitos
    "admin_conflitos": conflicts_page.conflicts,

    # Espaços
    "espacos": spaces_page.spaces,
    "localizar": spaces_page.localizar,

    # Usuários e permissões
    "usuarios": users_page.users_page,
    "permissoes": permissions_page.permissions,

    # Notificações
    "notificacoes": notifications_page.notifications,

    # Conta
    "conta": account_settings_page.account,

    # Alterações
    "alteracoes": changes_page.alteracoes,
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


# =========================================================
# MAIN
# =========================================================

def render_page():
    sync_page_from_query()

    page = st.session_state.page
    user = current_user()

    # ---------------------------------------------------------
    # USUÁRIO NÃO AUTENTICADO
    # ---------------------------------------------------------

    if not user:
        page_function = PUBLIC_ROUTES.get(page)

        if page_function:
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

    shell_start(user)

    page_function = APP_ROUTES.get(
        page,
        dashboard_page.dashboard,
    )

    page_function(user)

    shell_end()

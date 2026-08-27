import streamlit as st

from services.app_state_service import boot_state, current_user
from views.components.app_shell import shell_end, shell_start
from views.components.ui_components import load_css, toast
from views.pages import account_settings_page, agenda_page, changes_page, conflicts_page, dashboard_page
from views.pages import forgot_password_page, landing_page, login_page, notifications_page, permissions_page, register_page
from views.pages import reservations_page, spaces_page, users_page


st.set_page_config(page_title="RoomFlow", page_icon="R", layout="wide", initial_sidebar_state="collapsed")
boot_state()
load_css()
toast()

PUBLIC_ROUTES = {
    "landing": landing_page.landing,
    "login": login_page.login,
    "signup_choice": register_page.signup_choice,
    "signup_institution": register_page.signup_institution,
    "signup_member": register_page.signup_member,
    "forgot_password": forgot_password_page.forgot_password,
}

APP_ROUTES = {
    "admin_dashboard": dashboard_page.dashboard,
    "gerente_dashboard": dashboard_page.dashboard,
    "solicitante_dashboard": dashboard_page.dashboard,
    "participante_dashboard": dashboard_page.dashboard,
    "agenda": agenda_page.agenda,
    "admin_reservas": reservations_page.reservations_admin,
    "nova_reserva": reservations_page.new_reservation,
    "minhas_reservas": reservations_page.minhas_reservas,
    "admin_conflitos": conflicts_page.conflicts,
    "espacos": spaces_page.spaces,
    "usuarios": users_page.users_page,
    "permissoes": permissions_page.permissions,
    "notificacoes": notifications_page.notifications,
    "conta": account_settings_page.account,
    "localizar": spaces_page.localizar,
    "alteracoes": changes_page.alteracoes,
}


def main():
    page = st.session_state.page
    user = current_user()
    if page in PUBLIC_ROUTES and not user:
        PUBLIC_ROUTES[page]()
        return
    if not user:
        PUBLIC_ROUTES["landing"]()
        return
    if page in PUBLIC_ROUTES:
        page = {
            "admin": "admin_dashboard",
            "gerente": "gerente_dashboard",
            "solicitante": "solicitante_dashboard",
            "participante": "participante_dashboard",
        }[user["role"]]
        st.session_state.page = page
    shell_start(user)
    APP_ROUTES.get(page, dashboard_page.dashboard)(user)
    shell_end()


main()

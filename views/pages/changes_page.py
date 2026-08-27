from views.pages.notifications_page import notifications
from views.components.ui_components import page_header


def alteracoes(user):
    page_header("Alteracoes", "Mudancas recentes relevantes para participantes.")
    notifications(user)

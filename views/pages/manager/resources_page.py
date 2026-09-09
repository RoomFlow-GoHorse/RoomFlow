from views.components.ui_components import empty_state, page_header


def resources(user):
    page_header("Recursos", "Consulte os recursos dos espacos.")
    empty_state("Recursos indisponiveis", "Esta visao ainda nao possui dados no ambiente mockado.")

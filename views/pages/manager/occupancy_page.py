from views.components.ui_components import empty_state, page_header


def occupancy(user):
    page_header("Ocupacao", "Acompanhe a ocupacao dos espacos.")
    empty_state("Ocupacao indisponivel", "Esta visao ainda nao possui dados no ambiente mockado.")

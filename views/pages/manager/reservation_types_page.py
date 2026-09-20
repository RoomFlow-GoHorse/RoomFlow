from views.components.ui_components import empty_state, page_header


def reservation_types(user):
    page_header("Tipos de reserva", "Consulte os tipos de reserva disponiveis.")
    empty_state("Tipos indisponiveis", "Esta visao ainda nao possui dados no ambiente mockado.")

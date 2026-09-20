from views.components.ui_components import empty_state, page_header


def history(user):
    page_header("Historico", "Consulte o historico de reservas e alteracoes.")
    empty_state("Historico indisponivel", "Esta visao ainda nao possui dados no ambiente mockado.")

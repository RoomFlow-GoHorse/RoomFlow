import streamlit as st

from config.constants import ROLE_LABELS
from controllers import mock_data_service
from views.components.reservation_cards import reservation_cards
from views.components.ui_components import cards_grid, page_header, stat_card


def dashboard(user):
    stats = mock_data_service.dashboard_stats(user["role"], user["id"])
    subtitle = {
        "admin": "Operacao diaria de reservas, espacos e conflitos.",
        "gerente": "Governanca de usuarios, permissoes e configuracoes.",
        "solicitante": "Acompanhe suas solicitacoes e proximas reservas.",
        "participante": "Consulte agenda, alteracoes e localizacao de espacos.",
    }[user["role"]]
    page_header(f"Dashboard {ROLE_LABELS[user['role']]}", subtitle)
    cards = [
        stat_card("Reservas", stats["reservas"], "total visivel"),
        stat_card("Aprovadas", stats["aprovadas"], "confirmadas"),
        stat_card("Pendentes", stats["pendentes"], "aguardando decisao"),
        stat_card("Espacos livres", stats["espacos_livres"], stats["hoje"]),
    ]
    if user["role"] in {"admin", "gerente"}:
        cards.append(stat_card("Conflitos", stats["conflitos"], "ativos"))
        cards.append(stat_card("Usuarios", stats["usuarios"], "na instituicao"))
    cards_grid(cards)
    st.markdown("### Proximas atividades")
    requester_id = user["id"] if user["role"] == "solicitante" else None
    reservation_cards(mock_data_service.reservations(requester_id=requester_id)[:3])

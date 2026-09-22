import streamlit as st

from views.components.cards import reservation_card
from views.components.ui_components import empty_state


def reservation_cards(items):
    if not items:
        empty_state("Nenhuma reserva", "Nao ha itens para os filtros selecionados.")
        return
    for item in items:
        st.html(reservation_card(item))

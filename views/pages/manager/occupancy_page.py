import streamlit as st

from controllers import mock_data_service
from views.components.ui_components import page_header
from views.pages.manager.spaces_page import _space_card


def occupancy(user):
    page_header("Ocupação", "Acompanhe salas, reservas e situações que exigem intervenção.")
    items = mock_data_service.spaces()
    metrics = (
        ("Ocupadas", sum(space["status"] == "ocupado" for space in items)),
        ("Disponíveis", sum(space["status"] == "disponivel" for space in items)),
        ("Bloqueadas", sum(space["status"] == "bloqueado" for space in items)),
    )
    for column, (label, value) in zip(st.columns(3), metrics):
        with column:
            st.metric(label, value)
    for space in items:
        _space_card(space)

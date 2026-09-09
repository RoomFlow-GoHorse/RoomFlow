from datetime import date

import streamlit as st

from services import mock_data_service
from services.app_state_service import go
from views.components.reservation_cards import reservation_cards
from views.components.ui_components import cards_grid, page_header, stat_card


def agenda(user):
    page_header("Agenda", "Visualizacao compartilhada com filtros por espaco e tipo.")
    col1, col2, col3 = st.columns([1, 1, 1])
    view = col1.segmented_control("Visualizacao", ["Dia", "Semana", "Mes"], default=st.session_state.agenda_view)
    st.session_state.agenda_view = view
    space_names = ["Todos"] + [s["name"] for s in st.session_state.spaces]
    space = col2.selectbox("Espaco", space_names)
    event_type = col3.selectbox("Tipo", ["Todos", "Aula", "Banca", "Workshop", "Reuniao", "Monitoria"])
    if user["role"] == "solicitante" and st.button("Nova reserva", type="primary"):
        go("nova_reserva")
    events = mock_data_service.agenda_events(space, event_type)
    if view == "Dia":
        reservation_cards([item for item in events if item["date"] == date.today().isoformat()])
    elif view == "Mes":
        cards_grid([stat_card(item["date"][-2:], item["title"], item["space"]) for item in events], columns=4)
    else:
        days = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sab", "Dom"]
        html = '<div class="rf-agenda-grid">'
        for index, day in enumerate(days):
            html += f'<div class="rf-day-col"><strong>{day}</strong>'
            for event in events[index::7] if events else []:
                html += f'<div class="rf-event"><strong>{event["title"]}</strong><br>{event["space"]}<br>{event["start"]}-{event["end"]}</div>'
            html += "</div>"
        html += "</div>"
        st.html(html)

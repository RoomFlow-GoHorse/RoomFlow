import streamlit as st

from services import mock_data_service
from views.components.ui_components import badge, page_header, table


def spaces(user):
    page_header("Espacos", "Gerencie disponibilidade, capacidade e recursos.")
    col1, col2 = st.columns(2)
    query = col1.text_input("Buscar")
    status = col2.selectbox("Status", ["Todos", "disponivel", "ocupado", "bloqueado"])
    items = mock_data_service.spaces(status, query)
    for space in items:
        st.html(
            f'<div class="rf-card"><strong>{space["name"]}</strong> {badge(space["status"])}<br><span style="color:var(--muted)">{space["type"]} - {space["capacity"]} pessoas - {space["location"]}</span><p>{", ".join(space["resources"])}</p></div>',
        )
        if user["role"] == "admin" and st.button("Bloquear/Desbloquear", key=f"space_{space['id']}"):
            mock_data_service.toggle_space(space["id"])
            st.rerun()
    st.markdown("### Recursos")
    table(["Recurso", "Total", "Disponivel"], [[r["name"], r["total"], r["available"]] for r in mock_data_service.resources()])


def localizar(user):
    page_header("Localizar espacos", "Consulte salas disponiveis e recursos.")
    spaces(user)

from controllers import space_controller
import streamlit as st

from views.components.ui_components import badge, page_header, table


def spaces(user):
    page_header("Espacos", "Gerencie disponibilidade, capacidade e recursos.")
    col1, col2 = st.columns(2)
    query = col1.text_input("Buscar")
    status = col2.selectbox("Status", ["Todos", "disponivel", "ocupado", "bloqueado"])
    items = space_controller.spaces(status, query)
    for space in items:
        st.html(
            f'<div class="rf-card"><strong>{space["name"]}</strong> {badge(space["status"])}<br><span style="color:var(--muted)">{space["type"]} - {space["capacity"]} pessoas - {space["location"]}</span><p>{", ".join(space["resources"])}</p></div>',
        )
        if user["role"] == "admin" and st.button("Bloquear/Desbloquear", key=f"space_{space['id']}"):
            space_controller.toggle_space(space["id"])
            st.rerun()
    st.markdown("### Recursos")
    table(["Recurso", "Total", "Disponivel"], [[r["name"], r["total"], r["available"]] for r in space_controller.resources()])


def localizar(user):
    page_header("Localizar espacos", "Consulte salas disponiveis e recursos.")
    spaces(user)

import streamlit as st

from services import mock_data_service
from services.app_state_service import set_toast
from views.components.ui_components import badge, page_header


def conflicts(user):
    page_header("Conflitos", "Resolva sobreposicoes de reservas.")
    for conflict in st.session_state.conflicts:
        st.html(
            f'<div class="rf-card"><strong>{conflict["space"]}</strong> {badge(conflict["status"])} {badge(conflict["severity"])}<p>{conflict["reason"]}</p></div>',
        )
        c1, c2, c3 = st.columns(3)
        if c1.button("Manter A", key=f"a_{conflict['id']}"):
            mock_data_service.resolve_conflict(conflict["id"], "manteve_a")
            set_toast("Conflito resolvido no mock.")
            st.rerun()
        if c2.button("Manter B", key=f"b_{conflict['id']}"):
            mock_data_service.resolve_conflict(conflict["id"], "manteve_b")
            set_toast("Conflito resolvido no mock.")
            st.rerun()
        if c3.button("Alterar", key=f"alt_{conflict['id']}"):
            mock_data_service.resolve_conflict(conflict["id"], "alterar")
            set_toast("Conflito enviado para analise no mock.")
            st.rerun()

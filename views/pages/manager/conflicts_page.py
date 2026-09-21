import streamlit as st

from controllers import mock_data_service
from controllers.app_state_service import set_toast
from views.components.ui_components import badge, page_header


def _reservations_for(conflict):
    identifiers = conflict.get("affected_reservations") or [
        conflict.get("reservation_a"), conflict.get("reservation_b"),
    ]
    by_id = {reservation["id"]: reservation for reservation in st.session_state.reservations}
    return [by_id[identifier] for identifier in identifiers if identifier in by_id]


def conflicts(user):
    page_header("Conflitos", "Analise reservas afetadas e escolha a solução operacional adequada.")
    items = [item for item in st.session_state.conflicts if item["status"] != "resolvido"]
    if not items:
        st.success("Não há conflitos pendentes.")
        return

    for conflict in items:
        involved = _reservations_for(conflict)
        with st.container(border=True):
            title, labels = st.columns([4, 1], vertical_alignment="center")
            with title:
                conflict_type = conflict.get("type", "Sobreposição").replace("_", " ").title()
                st.markdown(f"**{conflict_type} · {conflict['space']}**")
                st.caption(conflict["reason"])
            with labels:
                st.html(badge(conflict["status"]))
                st.html(badge(conflict["severity"]))

            if not involved:
                st.info("As reservas originais deste conflito não estão disponíveis no ambiente atual.")
            for reservation in involved:
                st.write(f"{reservation['title']} — {reservation['requester']} · {reservation['date']} · {reservation['start']}–{reservation['end']}")
                with st.container(horizontal=True):
                    if st.button("Alterar sala", key=f"conflict_room_{conflict['id']}_{reservation['id']}", icon=":material/edit_location:"):
                        from views.pages.manager.requests_page import change_room_dialog
                        change_room_dialog(reservation)
                    if st.button("Aprovar", key=f"conflict_approve_{conflict['id']}_{reservation['id']}", type="primary"):
                        mock_data_service.update_reservation_status(reservation["id"], "aprovada")
                        mock_data_service.resolve_conflict(conflict["id"], "aprovada")
                        set_toast("Reserva aprovada e conflito atualizado.")
                        st.rerun()
                    if st.button("Rejeitar", key=f"conflict_reject_{conflict['id']}_{reservation['id']}"):
                        mock_data_service.update_reservation_status(reservation["id"], "rejeitada")
                        mock_data_service.resolve_conflict(conflict["id"], "rejeitada")
                        set_toast("Reserva rejeitada e conflito atualizado.")
                        st.rerun()

            if st.button("Marcar para análise", key=f"conflict_review_{conflict['id']}", icon=":material/manage_search:"):
                mock_data_service.resolve_conflict(conflict["id"], "alterar")
                set_toast("Conflito marcado para análise.")
                st.rerun()

from datetime import datetime, timezone as utc

import streamlit as st

from config.constants import STATUS_LABELS
from controllers.app_state_service import go
from models.domain.entities.reservation import EDITABLE
from views.components.reservation_forms import RESERVATION_ERRORS, edit_reservation, local_times, reservation_api
from views.components.ui_components import badge, page_header


@st.dialog("Cancelar solicitação")
def _cancel_dialog(item):
    st.write(f"Cancelar {item['title']}?")
    if st.button("Confirmar cancelamento", type="primary"):
        api = reservation_api()
        if api is None:
            return
        try:
            api.cancel(item["id"])
        except RESERVATION_ERRORS as error:
            st.error(str(error))
        else:
            st.rerun()


def minhas_reservas(user):
    page_header("Minhas solicitações", "Acompanhe suas reservas e gerencie alterações.")
    api = reservation_api()
    if api is None:
        return
    if st.button("Nova solicitação", icon=":material/add:", type="primary"):
        go("nova_reserva")
    try:
        items = api.list_own()
        timezone = api.catalog()["timezone"]
    except RESERVATION_ERRORS as error:
        st.error(str(error))
        return

    statuses = sorted({item["status"] for item in items})
    selected = st.selectbox("Status", [None, *statuses], format_func=lambda status: STATUS_LABELS.get(status, status) if status else "Todos")
    visible = [item for item in items if selected is None or selected == item["status"]]
    if not visible:
        st.info("Nenhuma solicitação encontrada.")
    now = datetime.now(utc.utc)
    for item in visible:
        start, end = local_times(item, timezone)
        with st.container(border=True):
            title, status = st.columns([5, 1])
            title.subheader(item["title"])
            status.html(badge(item["status"]))
            st.caption(f"{item['space_name']} · {start:%d/%m/%Y %H:%M}–{end:%H:%M} · {item['participants']} participantes")
            if item["justification"]:
                st.write(item["justification"])
            if item["decision_reason"]:
                st.write("Motivo da decisão", item["decision_reason"])
            if item["has_overlap"]:
                st.info("Existe uma sobreposição no período solicitado.")
            if item["status"] in EDITABLE and start > now:
                change, cancel = st.columns(2)
                if change.button("Solicitar alteração", key=f"alter_{item['id']}"):
                    edit_reservation(item)
                if cancel.button("Cancelar", key=f"cancel_{item['id']}"):
                    _cancel_dialog(item)

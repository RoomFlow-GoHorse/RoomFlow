from datetime import datetime, timezone as utc

import streamlit as st

from config.constants import STATUS_LABELS
from controllers.app_state_service import go
from models.domain.entities.reservation import EDITABLE
from views.components.reservation_forms import (
    RESERVATION_ERRORS, close_reservation_dialog, edit_reservation, local_times, reservation_api,
)
from views.components.reservation_history import render_reservation_history
from views.components.ui_components import badge, page_header


@st.dialog("Cancelar solicitação", on_dismiss=close_reservation_dialog)
def _cancel_dialog(item):
    st.text(f"Cancelar {item['title']}?")
    with st.form(f"cancel_reservation_{item['id']}"):
        reason = st.text_area("Motivo do cancelamento (opcional)", max_chars=600)
        confirm = st.form_submit_button("Confirmar cancelamento", type="primary")
    if confirm:
        api = reservation_api()
        if api is None:
            return
        try:
            api.cancel(item["id"], reason)
        except RESERVATION_ERRORS as error:
            st.error(str(error))
        else:
            close_reservation_dialog()
            st.rerun()


@st.dialog("Histórico da solicitação", on_dismiss=close_reservation_dialog)
def _history_dialog(item, timezone):
    api = reservation_api()
    if api is None:
        return
    try:
        detail = api.detail_own(item["id"])
    except RESERVATION_ERRORS as error:
        st.error(str(error))
        return
    st.subheader(detail["title"])
    render_reservation_history(detail["history"], timezone)


def minhas_reservas(user):
    page_header("Minhas solicitações", "Acompanhe suas reservas e gerencie alterações.")
    api = reservation_api()
    if api is None:
        return
    if st.button("Nova solicitação", icon=":material/add:", type="primary"):
        go("nova_reserva")
    try:
        items = api.list_own()
        timezone = api.catalog_settings()["timezone"]
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
            editable = item["status"] in EDITABLE and start > now
            history, change, cancel = st.columns(3)
            if history.button("Ver histórico", key=f"history_{item['id']}"):
                st.session_state["reservation_dialog"] = (item["id"], "history")
            if editable:
                if change.button("Solicitar alteração", key=f"alter_{item['id']}"):
                    st.session_state["reservation_dialog"] = (item["id"], "edit")
                if cancel.button("Cancelar", key=f"cancel_{item['id']}"):
                    st.session_state["reservation_dialog"] = (item["id"], "cancel")
    by_id = {item["id"]: item for item in visible}
    opened = st.session_state.get("reservation_dialog")
    if opened and opened[0] in by_id:
        item = by_id[opened[0]]
        if opened[1] == "history":
            _history_dialog(item, timezone)
        elif item["status"] in EDITABLE and local_times(item, timezone)[0] > now:
            if opened[1] == "cancel":
                _cancel_dialog(item)
            elif opened[1] == "edit":
                edit_reservation(item)

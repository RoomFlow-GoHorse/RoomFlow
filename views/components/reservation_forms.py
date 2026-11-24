from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import streamlit as st

from controllers.streamlit_runtime import get_streamlit_runtime, uses_persistent_runtime
from models.domain.exceptions import DomainAuthorizationError, DuplicateResource, ResourceNotFound


RESERVATION_ERRORS = (DomainAuthorizationError, DuplicateResource, ResourceNotFound, ValueError)


def reservation_api():
    if not uses_persistent_runtime():
        st.info("Não foi possível carregar as reservas. Tente novamente.")
        return None
    return get_streamlit_runtime().reservation_service


def local_times(item, timezone):
    zone = ZoneInfo(timezone)
    return tuple(datetime.fromisoformat(item[key]).astimezone(zone) for key in ("start", "end"))


def period_inputs(timezone, key, item=None):
    zone = ZoneInfo(timezone)
    if item:
        start, end = local_times(item, timezone)
        day, start_time, end_time = start.date(), start.time(), end.time()
    else:
        day = datetime.now(zone).date() + timedelta(days=2)
        start_time, end_time = time(9), time(10)
    date_column, start_column, end_column = st.columns(3)
    day = date_column.date_input("Data", value=day, key=f"{key}_date", format="DD/MM/YYYY")
    start_time = start_column.time_input("Início", value=start_time, key=f"{key}_start")
    end_time = end_column.time_input("Fim", value=end_time, key=f"{key}_end")
    return datetime.combine(day, start_time, zone), datetime.combine(day, end_time, zone)


def request_fields(rooms, start, end, key, item=None, justification_required=True, participants=None):
    values = item or {}
    by_id = {room["id"]: room for room in rooms}
    ids = list(by_id)
    current = values.get("space_id")
    room_id = st.selectbox(
        "Sala", ids, index=ids.index(current) if current in by_id else None,
        format_func=lambda room_id: f"{by_id[room_id]['name']} · {by_id[room_id]['location']}",
        key=f"{key}_room",
    )
    title = st.text_input("Título", value=values.get("title", ""), max_chars=200, key=f"{key}_title")
    activity = st.text_input("Tipo de atividade", value=values.get("activity_type", ""), max_chars=60,
                             key=f"{key}_activity")
    if participants is None:
        participants = st.number_input("Participantes", min_value=1, max_value=10000,
                                       value=values.get("participants", 1), key=f"{key}_participants")
    label = "Justificativa" if justification_required else "Justificativa (opcional)"
    reason = st.text_area(label, value=values.get("justification") or "", max_chars=600, key=f"{key}_reason")
    return {
        "space_id": room_id or "", "title": title, "activity_type": activity,
        "start": start.isoformat(), "end": end.isoformat(), "participants": participants, "justification": reason,
    }


def close_reservation_dialog():
    st.session_state.pop("reservation_dialog", None)


@st.dialog("Alterar solicitação", width="large", on_dismiss=close_reservation_dialog)
def edit_reservation(item):
    api = reservation_api()
    if api is None:
        return
    try:
        catalog = api.catalog()
        with st.form("edit_reservation"):
            start, end = period_inputs(catalog["timezone"], "edit", item)
            payload = request_fields(catalog["spaces"], start, end, "edit", item, catalog["justification_required"])
            payload["reason"] = st.text_area("Motivo da alteração (opcional)", max_chars=600, key="edit_change_reason")
            submitted = st.form_submit_button("Salvar alterações", type="primary")
        if submitted:
            api.edit(item["id"], payload)
            close_reservation_dialog()
            st.rerun()
    except RESERVATION_ERRORS as error:
        st.error(str(error))

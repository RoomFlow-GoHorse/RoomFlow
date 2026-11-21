from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from config.constants import STATUS_LABELS
from controllers.app_state_service import set_toast
from controllers.streamlit_runtime import get_streamlit_runtime, uses_roomflow_api
from views.components.reservation_forms import RESERVATION_ERRORS, local_times
from views.components.ui_components import page_header


CONFLICT_LABELS = {"nao_resolvido": "Em aberto", "em_analise": "Em análise", "resolvido": "Resolvido"}


def _space_label(item):
    return " / ".join(dict.fromkeys(reservation["space_name"] for reservation in item["reservations"]))


def _schedule(item, timezone):
    periods = [local_times(reservation, timezone) for reservation in item["reservations"]]
    start = max(period[0] for period in periods)
    end = min(period[1] for period in periods)
    return f"{start:%d/%m/%Y · %H:%M}–{end:%H:%M}" if start < end else "Períodos distintos"


def _local_date(value, timezone):
    return datetime.fromisoformat(value).astimezone(ZoneInfo(timezone)).strftime("%d/%m/%Y %H:%M")


def _close_dialog():
    st.session_state.pop("resolve_conflict_id", None)


@st.dialog("Conflito de reservas", width="large", on_dismiss=_close_dialog)
def _conflict_dialog(conflict_id, timezone):
    api = get_streamlit_runtime().conflict_service
    try:
        conflict = api.detail(conflict_id)
    except RESERVATION_ERRORS as error:
        st.error(str(error))
        return
    reservations = conflict["reservations"]
    st.caption(f"{_space_label(conflict)} · {_schedule(conflict, timezone)}")
    st.text(conflict["reason"])
    for label, column, reservation in zip(("A", "B"), st.columns(2), reservations, strict=True):
        start, end = local_times(reservation, timezone)
        with column.container(border=True):
            st.caption(f"Reserva {label} · {STATUS_LABELS[reservation['status']]}")
            st.text(reservation["requester_name"])
            st.text(reservation["title"])
            st.caption(f"{start:%d/%m/%Y %H:%M}–{end:%H:%M} · {reservation['participants']} pessoas")
            st.text(reservation["space_name"])
            if reservation["justification"]:
                st.text(reservation["justification"])
    if conflict["decision"]:
        st.text(conflict["decision"])
        if conflict["resolved_at"]:
            date = _local_date(conflict["resolved_at"], timezone)
            st.caption(f"{conflict['resolver_name'] or 'Responsável indisponível'} · {date}")
    if conflict["available_actions"]:
        _resolution_form(api, conflict)


def _resolution_form(api, conflict):
    a, b = conflict["reservations"]
    conflict_id = conflict["id"]
    labels = {
        "manteve_a": f"Manter reserva A ({a['requester_name']})",
        "manteve_b": f"Manter reserva B ({b['requester_name']})",
        "alterou": "Mover uma reserva para uma sala alternativa",
    }
    action = st.selectbox("Resultado da análise", conflict["available_actions"], format_func=labels.__getitem__,
                          key=f"conflict_outcome_{conflict_id}")
    payload = {"action": action}
    can_submit = True
    if action == "alterou":
        try:
            alternatives = api.alternatives(conflict_id)
        except RESERVATION_ERRORS as error:
            st.error(str(error))
            return
        available = {item["id"]: item["title"] for item in (a, b) if alternatives.get(item["id"])}
        if available:
            reservation_id = st.selectbox("Reserva a mover", list(available), format_func=available.__getitem__)
            rooms = {room["id"]: f"{room['name']} · {room['capacity']} pessoas"
                     for room in alternatives[reservation_id]}
            space_id = st.selectbox("Sala alternativa", list(rooms), format_func=rooms.__getitem__)
            payload.update(reservation_id=reservation_id, space_id=space_id)
        else:
            st.info("Nenhuma sala alternativa está disponível para esta decisão.")
            can_submit = False

    with st.form(f"resolve_conflict_form_{conflict_id}"):
        reason = st.text_area("Justificativa da decisão", max_chars=600, key=f"conflict_justification_{conflict_id}")
        cancel_col, resolve_col = st.columns(2)
        cancelled = cancel_col.form_submit_button("Cancelar", width="stretch")
        resolved = resolve_col.form_submit_button(
            "Aplicar decisão", type="primary", icon=":material/check:", width="stretch", disabled=not can_submit,
        )
    if cancelled:
        _close_dialog()
        st.rerun()
    if resolved:
        try:
            api.resolve(conflict_id, {**payload, "reason": reason})
        except RESERVATION_ERRORS as error:
            st.error(str(error))
        else:
            _close_dialog()
            set_toast("Conflito resolvido.")
            st.rerun()


def conflicts(user=None):
    page_header("Conflitos", "Analise sobreposições de horários e aplique uma decisão às reservas.")
    if not uses_roomflow_api():
        st.info("Abra o RoomFlow conectado à API PostgreSQL para gerenciar conflitos.")
        return
    api = get_streamlit_runtime().conflict_service
    search, status_column, detect_column = st.columns([3, 2, 2], vertical_alignment="bottom")
    query = search.text_input("Buscar conflito", placeholder="ID, sala ou solicitante", max_chars=120,
                             key="conflict_search_query")
    status = status_column.selectbox(
        "Status", [None, *CONFLICT_LABELS],
        format_func=lambda value: CONFLICT_LABELS.get(value, "Todos"), key="conflict_status_filter",
    )
    try:
        if detect_column.button("Detectar sobreposições", key="detect_reservation_conflicts"):
            count = api.detect()["updated"]
            st.success(f"Conflitos atualizados: {count}.")
        listing = api.list(status, query)
    except RESERVATION_ERRORS as error:
        st.error(str(error))
        return

    items = listing["items"]
    timezone = listing["timezone"]
    if not items:
        st.info("Nenhum conflito encontrado.", icon=":material/search_off:")
        return
    st.dataframe(pd.DataFrame([{
        "ID": item["id"], "Espaço": _space_label(item), "Data / Horário": _schedule(item, timezone),
        "Solicitantes Envolvidos": " × ".join(res["requester_name"] for res in item["reservations"]),
        "Status": CONFLICT_LABELS[item["status"]], "Detectado": _local_date(item["created_at"], timezone),
    } for item in items]), hide_index=True, width="stretch")

    by_id = {item["id"]: item for item in items}
    select, action = st.columns([4, 1], vertical_alignment="bottom")
    selected = select.selectbox("Ações do conflito", list(by_id),
                                format_func=lambda key: f"#{key} · {_space_label(by_id[key])}",
                                key="select_conflict_action")
    label = "Ver detalhes" if by_id[selected]["status"] == "resolvido" else "Resolver conflito"
    if action.button(label, key="btn_resolve_conflict", type="primary", width="stretch"):
        st.session_state["resolve_conflict_id"] = selected
    if st.session_state.get("resolve_conflict_id") == selected:
        _conflict_dialog(selected, timezone)

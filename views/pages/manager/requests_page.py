from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from config.constants import STATUS_LABELS
from models.domain.entities.reservation import EDITABLE
from views.components.reservation_forms import (
    RESERVATION_ERRORS, close_reservation_dialog, edit_reservation, local_times, reservation_api,
)
from views.components.reservation_history import render_reservation_history
from views.components.ui_components import page_header


@st.dialog("Analisar solicitação", width="medium", on_dismiss=close_reservation_dialog)
def _review_dialog(item):
    decisions = {
        "em_analise": "Colocar em análise", "aprovada": "Aprovar", "rejeitada": "Rejeitar",
    }
    with st.form("review_reservation"):
        status = st.selectbox("Decisão", item["available_decisions"], format_func=decisions.__getitem__,
                              key="reservation_decision")
        reason = st.text_area("Motivo da decisão (obrigatório na rejeição)", max_chars=600)
        saved = st.form_submit_button("Confirmar decisão", type="primary")
    if saved:
        api = reservation_api()
        if api is None:
            return
        try:
            api.review(item["id"], status, reason)
            close_reservation_dialog()
            st.rerun()
        except RESERVATION_ERRORS as error:
            st.error(str(error))


def manager_reservations(user=None):
    page_header("Reservas", "Analise as solicitações da sua instituição.")
    api = reservation_api()
    if api is None:
        return
    try:
        items = api.list_institution()
        timezone = api.catalog_settings()["timezone"]
    except RESERVATION_ERRORS as error:
        st.error(str(error))
        return

    search, status_column, overlap_column = st.columns([3, 1, 1])
    query = search.text_input("Buscar solicitação", placeholder="Título, sala ou solicitante").strip().casefold()
    statuses = sorted({item["status"] for item in items})
    status = status_column.selectbox("Status", [None, *statuses],
                                      format_func=lambda value: STATUS_LABELS.get(value, value) if value else "Todos")
    only_overlap = overlap_column.checkbox("Só sobreposições")
    visible = [
        item for item in items
        if (status is None or status == item["status"])
        and (not only_overlap or item["has_overlap"])
        and query in " ".join((item["title"], item["space_name"], item["requester_name"])).casefold()
    ]
    if not visible:
        st.info("Nenhuma solicitação encontrada.")
        return
    rows = []
    for item in visible:
        start, end = local_times(item, timezone)
        rows.append({
            "Solicitação": item["title"], "Solicitante": item["requester_name"], "Sala": item["space_name"],
            "Período": f"{start:%d/%m/%Y %H:%M}–{end:%H:%M}",
            "Status": STATUS_LABELS.get(item["status"], item["status"]),
            "Sobreposição": "Sim" if item["has_overlap"] else "Não",
        })
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    by_id = {item["id"]: item for item in visible}
    selected_id = st.selectbox("Solicitação", list(by_id),
                               format_func=lambda key: f"#{key} · {by_id[key]['title']}")
    try:
        item = api.detail(selected_id)
    except RESERVATION_ERRORS as error:
        st.error(str(error))
        return
    st.caption(f"{item['activity_type']} · {item['participants']} participantes")
    if item["has_overlap"]:
        st.warning("Há reservas ou solicitações abertas para a mesma sala em horários sobrepostos.")
    if item["justification"]:
        st.write("Justificativa", item["justification"])
    if item["decision_reason"]:
        st.write("Motivo da decisão", item["decision_reason"])
    if item["history"]:
        with st.expander("Histórico da solicitação"):
            render_reservation_history(item["history"], timezone)
    elif item["reviewed_at"]:
        reviewed_at = datetime.fromisoformat(item["reviewed_at"]).astimezone(ZoneInfo(timezone))
        reviewer = f" · Avaliador #{item['reviewed_by']}" if item["reviewed_by"] else ""
        st.caption(f"Avaliada em {reviewed_at:%d/%m/%Y %H:%M}{reviewer}")
    start, _ = local_times(item, timezone)
    edit, review = st.columns(2)
    editable = item["status"] in EDITABLE and start > datetime.now(UTC)
    if editable and edit.button("Editar solicitação"):
        st.session_state["reservation_dialog"] = (selected_id, "edit")
    if item["available_decisions"] and review.button("Analisar solicitação", type="primary"):
        st.session_state["reservation_dialog"] = (selected_id, "review")
    opened = st.session_state.get("reservation_dialog")
    if opened == (selected_id, "edit") and editable:
        edit_reservation(item)
    elif opened == (selected_id, "review") and item["available_decisions"]:
        _review_dialog(item)
    elif opened:
        close_reservation_dialog()


reservations_admin = manager_reservations

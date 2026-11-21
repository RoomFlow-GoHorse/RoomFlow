from datetime import datetime, timezone as utc

import pandas as pd
import streamlit as st

from config.constants import STATUS_LABELS
from models.domain.entities.reservation import EDITABLE, REVIEWABLE
from views.components.reservation_forms import RESERVATION_ERRORS, edit_reservation, local_times, reservation_api
from views.components.ui_components import page_header


@st.dialog("Analisar solicitação", width="medium")
def _review_dialog(item):
    decisions = {
        "em_analise": "Colocar em análise", "aprovada": "Aprovar", "rejeitada": "Rejeitar",
    }
    with st.form("review_reservation"):
        status = st.selectbox("Decisão", [key for key in decisions if key != item["status"]],
                              format_func=decisions.__getitem__)
        reason = st.text_area("Motivo da decisão (obrigatório na rejeição)", max_chars=600)
        saved = st.form_submit_button("Confirmar decisão", type="primary")
    if saved:
        api = reservation_api()
        if api is None:
            return
        try:
            api.review(item["id"], status, reason)
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
        timezone = api.catalog()["timezone"]
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
    item = by_id[selected_id]
    st.caption(f"{item['activity_type']} · {item['participants']} participantes")
    if item["has_overlap"]:
        st.warning("Há reservas ou solicitações abertas para a mesma sala em horários sobrepostos.")
    if item["justification"]:
        st.write("Justificativa", item["justification"])
    if item["decision_reason"]:
        st.write("Motivo da decisão", item["decision_reason"])
    start, _ = local_times(item, timezone)
    edit, review = st.columns(2)
    if item["status"] in EDITABLE and start > datetime.now(utc.utc):
        if edit.button("Editar solicitação"):
            edit_reservation(item)
    if item["status"] in REVIEWABLE and review.button("Analisar solicitação", type="primary"):
        _review_dialog(item)


reservations_admin = manager_reservations

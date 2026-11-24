from datetime import date

import streamlit as st

from config.constants import STATUS_LABELS
from controllers.streamlit_runtime import get_streamlit_runtime, uses_persistent_runtime
from models.domain.entities.reservation import ReservationStatus


ROOM_STATUS_LABELS = {
    "disponivel": "Disponível", "ocupado": "Ocupada", "bloqueado": "Com bloqueio",
    "inativo": "Inativa", "indisponivel": "Indisponível",
}


def operations_api():
    if not uses_persistent_runtime():
        st.info("Esta área está indisponível no momento.")
        return None
    return get_streamlit_runtime().manager_operations


def space_filters(context, prefix, *, include_status=False):
    columns = st.columns(3 if include_status else 2)
    buildings = {item["id"]: item["name"] for item in context["buildings"]}
    building_id = columns[0].selectbox("Prédio", [None, *buildings],
                                      format_func=lambda value: buildings.get(value, "Todos"),
                                      key=f"{prefix}_building")
    rooms = {
        item["id"]: item["name"] for item in context["spaces"]
        if building_id is None or item["building_id"] == building_id
    }
    space_id = columns[1].selectbox("Sala", [None, *rooms],
                                   format_func=lambda value: rooms.get(value, "Todas"),
                                   key=f"{prefix}_space_{building_id}")
    filters = {"building_id": building_id, "space_id": space_id}
    if include_status:
        statuses = [status.value for status in ReservationStatus]
        filters["status"] = columns[2].selectbox(
            "Status da reserva", [None, *statuses],
            format_func=lambda status: STATUS_LABELS.get(status, "Todos"), key=f"{prefix}_status",
        )
    return filters


def dashboard_dates(context):
    today = date.fromisoformat(context["today"])
    first, last = st.columns(2)
    return {
        "start_date": first.date_input("Data inicial", value=today, format="DD/MM/YYYY", key="dashboard_start"),
        "end_date": last.date_input("Data final", value=None, format="DD/MM/YYYY", key="dashboard_end"),
    }

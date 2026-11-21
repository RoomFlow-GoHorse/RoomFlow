from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st

from config.constants import STATUS_LABELS


HISTORY_LABELS = {
    "criacao": "Solicitação criada", "avaliacao": "Avaliação", "edicao": "Edição",
    "cancelamento": "Cancelamento", "aprovacao_automatica": "Aprovação automática",
}


def render_reservation_history(events, timezone):
    if not events:
        st.info("Nenhuma operação registrada no histórico desta reserva.")
        return
    zone = ZoneInfo(timezone)
    for event in reversed(events):
        at = datetime.fromisoformat(event["occurred_at"]).astimezone(zone)
        label = HISTORY_LABELS[event["action"]]
        status = STATUS_LABELS[event["status"]]
        previous = event["previous_status"]
        change = f"{STATUS_LABELS[previous]} → {status}" if previous and previous != event["status"] else status
        actor = event["actor_name"] or "Sistema"
        st.caption(f"{at:%d/%m/%Y %H:%M} · {actor} · {label} · {change}")
        if event["reason"]:
            st.text(event["reason"])

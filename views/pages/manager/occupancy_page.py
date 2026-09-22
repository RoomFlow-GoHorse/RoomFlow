from datetime import date, datetime, timedelta
from html import escape

import streamlit as st

from controllers import mock_data_service
from controllers.app_state_service import set_toast
from views.components.ui_components import badge, page_header


START_HOUR, END_HOUR, SLOT_MINUTES = 7, 23, 30
COLORS = {"aprovada": "brand", "pendente": "warning", "em_analise": "warning", "conflito": "danger", "rejeitada": "muted", "cancelada": "muted"}


def _date(value):
    return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()


def _time(value):
    return datetime.strptime(value, "%H:%M").time()


def _minutes(value):
    parsed = _time(value)
    return parsed.hour * 60 + parsed.minute


def _shift(days):
    st.session_state.occupancy_date += timedelta(days=days)


def _timeline(spaces, reservations):
    duration = (END_HOUR - START_HOUR) * 60
    hours = "".join(f"<span>{hour:02d}:00</span>" for hour in range(START_HOUR, END_HOUR + 1))
    rows = []
    for space in spaces:
        blocks = []
        for item in [reservation for reservation in reservations if reservation["space"] == space["name"]]:
            start, end = max(_minutes(item["start"]), 420), min(_minutes(item["end"]), 1380)
            left, width = (start - 420) / duration * 100, max(end - start, SLOT_MINUTES) / duration * 100
            blocks.append(f'<div class="rf-occ-event rf-occ-{COLORS.get(item["status"], "brand")}" style="left:{left:.3f}%;width:{width:.3f}%" title="{escape(item["title"])}"><strong>{escape(item["title"])}</strong><span>{item["start"]}–{item["end"]}</span></div>')
        rows.append(f'<div class="rf-occ-row"><div class="rf-occ-room"><strong>{escape(space["name"])}</strong><span>{escape(space.get("location", ""))} · {space.get("capacity", 0)} pessoas</span></div><div class="rf-occ-track">{"".join(blocks)}</div></div>')
    style = """
    <style>
        .rf-occ { border: 1px solid var(--stroke); border-radius: 12px; background: #fff; overflow-x: auto; }
        .rf-occ-inner { min-width: 1050px; }
        .rf-occ-head, .rf-occ-row { display: grid; grid-template-columns: 170px 1fr; }
        .rf-occ-head { background: var(--surface-alt); border-bottom: 1px solid var(--stroke); }
        .rf-occ-room { padding: 14px 16px; border-right: 1px solid var(--stroke); display: flex; flex-direction: column; justify-content: center; gap: 4px; }
        .rf-occ-room span { font-size: 11px; color: var(--graphite-muted); }
        .rf-occ-times, .rf-occ-track { position: relative; background-image: repeating-linear-gradient(to right, transparent 0, transparent calc(6.25% - 1px), #e4e1db calc(6.25% - 1px), #e4e1db 6.25%); }
        .rf-occ-times { height: 48px; display: flex; justify-content: space-between; padding: 16px 8px 0; font-size: 11px; color: var(--graphite-muted); }
        .rf-occ-row { min-height: 76px; border-bottom: 1px solid var(--stroke); }
        .rf-occ-row:last-child { border: 0; }
        .rf-occ-track { min-height: 76px; }
        .rf-occ-event { position: absolute; top: 10px; bottom: 10px; border: 1px solid; border-radius: 7px; padding: 6px 8px; overflow: hidden; white-space: nowrap; font-size: 11px; }
        .rf-occ-event strong, .rf-occ-event span { display: block; overflow: hidden; text-overflow: ellipsis; }
        .rf-occ-event span { margin-top: 3px; opacity: .75; }
        .rf-occ-brand { background: #ede9fe; border-color: #c4b5fd; color: #5b21b6; }
        .rf-occ-warning { background: #fef3c7; border-color: #fcd34d; color: #92400e; }
        .rf-occ-danger { background: #fee2e2; border-color: #fca5a5; color: #b91c1c; }
        .rf-occ-muted { background: #f0eee9; border-color: #c8c4bc; color: #737373; }
    </style>
    """
    return f"{style}<div class=\"rf-occ\"><div class=\"rf-occ-inner\"><div class=\"rf-occ-head\"><div class=\"rf-occ-room\"><strong>Salas</strong></div><div class=\"rf-occ-times\">{hours}</div></div>{''.join(rows)}</div></div>"


@st.dialog("Detalhes da reserva", width="medium")
def _details(reservation):
    st.subheader(reservation["title"])
    left, right = st.columns(2)
    with left:
        st.caption("SALA"); st.write(reservation["space"])
        st.caption("SOLICITANTE"); st.write(reservation["requester"])
        st.caption("PARTICIPANTES"); st.write(reservation.get("participants", 0))
    with right:
        st.caption("DATA"); st.write(reservation["date"])
        st.caption("HORÁRIO"); st.write(f"{reservation['start']}–{reservation['end']}")
        st.caption("STATUS"); st.html(badge(reservation["status"]))
    st.caption("JUSTIFICATIVA"); st.write(reservation.get("justification") or "Sem justificativa informada.")
    if st.button("Editar reserva", type="primary", icon=":material/edit:", width="stretch"):
        st.session_state.occupancy_edit_id, st.session_state.occupancy_detail_id = reservation["id"], None
        st.rerun()


@st.dialog("Editar reserva", width="medium")
def _edit(reservation):
    with st.form(f"occupancy_edit_{reservation['id']}"):
        title = st.text_input("Título da reserva", value=reservation["title"])
        day = st.date_input("Data", value=_date(reservation["date"]))
        start_col, end_col = st.columns(2)
        with start_col: start = st.time_input("Início", value=_time(reservation["start"]))
        with end_col: end = st.time_input("Fim", value=_time(reservation["end"]))
        requester = st.text_input("Solicitante", value=reservation["requester"])
        participants = st.number_input("Participantes", min_value=0, value=int(reservation.get("participants", 0)))
        justification = st.text_area("Justificativa", value=reservation.get("justification", ""))
        cancel, save = st.columns(2)
        with cancel: cancelled = st.form_submit_button("Cancelar", width="stretch")
        with save: saved = st.form_submit_button("Salvar alterações", type="primary", width="stretch")
    if cancelled:
        st.session_state.occupancy_edit_id = None; st.rerun()
    if saved:
        if start >= end:
            st.error("O horário de término deve ser posterior ao início."); return
        mock_data_service.update_reservation(reservation["id"], {"title": title, "date": day.isoformat(), "start": start.strftime("%H:%M"), "end": end.strftime("%H:%M"), "requester": requester, "participants": participants, "justification": justification})
        st.session_state.occupancy_edit_id = None; set_toast("Reserva atualizada."); st.rerun()


def occupancy(user):
    st.session_state.setdefault("occupancy_date", _date(st.session_state.reservations[0]["date"]) if st.session_state.reservations else date.today())
    page_header("Ocupação", "Acompanhe as reservas dos espaços ao longo do dia.")
    previous, today, next_day, date_column = st.columns([1, 1, 1, 3], vertical_alignment="bottom")
    with previous: st.button("Dia anterior", icon=":material/chevron_left:", on_click=_shift, args=(-1,), width="stretch")
    with today:
        if st.button("Hoje", width="stretch"):
            st.session_state.occupancy_date = date.today(); st.rerun()
    with next_day: st.button("Próximo dia", icon=":material/chevron_right:", on_click=_shift, args=(1,), width="stretch")
    with date_column: selected_day = st.date_input("Data", key="occupancy_date")
    reservations = [item for item in st.session_state.reservations if _date(item["date"]) == selected_day]
    st.caption(f"{selected_day.strftime('%d/%m/%Y')} · {len(reservations)} {'reserva' if len(reservations) == 1 else 'reservas'} no dia")
    st.markdown(":violet-badge[Aprovada] :orange-badge[Pendente / em análise] :red-badge[Conflito]")
    st.html(_timeline(mock_data_service.spaces(), reservations))
    if not reservations:
        st.info("Não existem reservas cadastradas para este dia."); return
    choices = {f"{item['title']} · {item['space']} · {item['start']}–{item['end']}": item["id"] for item in reservations}
    label = st.selectbox("Consultar reserva", list(choices), key="occupancy_reservation_selector")
    if st.button("Ver detalhes", icon=":material/visibility:"):
        st.session_state.occupancy_detail_id = choices[label]
    item_id = st.session_state.get("occupancy_edit_id") or st.session_state.get("occupancy_detail_id")
    selected = next((item for item in st.session_state.reservations if item["id"] == item_id), None)
    if selected:
        _edit(selected) if st.session_state.get("occupancy_edit_id") else _details(selected)

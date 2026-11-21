from collections import defaultdict
from datetime import UTC, date, datetime, time, timedelta
from html import escape
from zoneinfo import ZoneInfo

import streamlit as st

from views.components.manager_operations import ROOM_STATUS_LABELS, operations_api, space_filters
from views.components.reservation_forms import RESERVATION_ERRORS, edit_reservation, local_times, reservation_api
from views.components.ui_components import badge, page_header


COLORS = {"aprovada": "brand", "pendente": "warning", "em_analise": "warning", "conflito": "danger", "rejeitada": "muted", "cancelada": "muted"}


def _change_day(today, shift=None):
    current = st.session_state.get("occupancy_date", today)
    st.session_state["occupancy_date"] = today if shift is None else current + timedelta(days=shift)
    st.session_state["occupancy_end"] = None


def _timeline(spaces, reservations, day, report, *, restricted=False):
    zone = ZoneInfo(report["timezone"])
    start, end = (
        datetime.combine(day, time.fromisoformat(report[key]), zone).astimezone(UTC)
        for key in ("opens_at", "closes_at")
    )
    if reservations and not restricted:
        midnight = datetime.combine(day, time.min, zone).astimezone(UTC)
        next_midnight = datetime.combine(day + timedelta(days=1), time.min, zone).astimezone(UTC)
        start = min(start, max(midnight, min(datetime.fromisoformat(item["start"]) for item in reservations)))
        end = max(end, min(next_midnight, max(datetime.fromisoformat(item["end"]) for item in reservations)))
    duration = (end - start).total_seconds()
    step = 3600 if duration <= 8 * 3600 else 7200
    ticks = range(step, int(duration), step)
    positions = (0, *ticks, duration)
    hours = "".join(
        f'<span style="--left:{seconds / duration:.3%}">'
        f'{(start + timedelta(seconds=seconds)).astimezone(zone):%H:%M}</span>'
        for seconds in positions
        if seconds in (0, duration) or seconds <= duration - step / 2
    )
    by_room = defaultdict(list)
    for item in reservations:
        by_room[item["space_id"]].append(item)
    rows = []
    for space in spaces:
        blocks = []
        lane_ends = []
        for item in by_room[space["id"]]:
            begins, finishes = local_times(item, report["timezone"])
            lo, hi = max(begins.astimezone(UTC), start), min(finishes.astimezone(UTC), end)
            if lo >= hi:
                continue
            lane = next((index for index, limit in enumerate(lane_ends) if limit <= lo), len(lane_ends))
            if lane == len(lane_ends):
                lane_ends.append(hi)
            else:
                lane_ends[lane] = hi
            left = (lo - start).total_seconds() / duration * 100
            width = (hi - lo).total_seconds() / duration * 100
            block_style = f"left:{left:.3f}%;width:{width:.3f}%;top:{10 + lane * 54}px"
            color = COLORS[item["status"]]
            title = escape(item["title"])
            blocks.append(
                f'<div class="rf-occ-event rf-occ-{color}" style="{block_style}" title="{title}">'
                f'<strong>{title}</strong><span>{begins:%H:%M}–{finishes:%H:%M}</span></div>'
            )
        height = max(76, 16 + 54 * len(lane_ends))
        rows.append(
            f'<div class="rf-occ-row"><div class="rf-occ-room"><strong>{escape(space["name"])}</strong>'
            f'<span>{escape(space["location"])} · {space["capacity"]} pessoas</span></div>'
            f'<div class="rf-occ-track" style="min-height:{height}px">{"".join(blocks)}</div></div>'
        )
    style = """
    <style>
        .rf-occ { border: 1px solid var(--stroke); border-radius: 12px; background: var(--surface-card); overflow-x: auto; }
        .rf-occ-inner { min-width: 1050px; }
        .rf-occ-head, .rf-occ-row { display: grid; grid-template-columns: 170px 1fr; }
        .rf-occ-head { background: var(--surface-alt); border-bottom: 1px solid var(--stroke); }
        .rf-occ-room { padding: 14px 16px; border-right: 1px solid var(--stroke); display: flex; flex-direction: column; justify-content: center; gap: 4px; }
        .rf-occ-room span { font-size: 11px; color: var(--graphite-muted); }
        .rf-occ-times, .rf-occ-track { position: relative; background-image: repeating-linear-gradient(to right, transparent 0, transparent calc(var(--tick) - 1px), var(--stroke) calc(var(--tick) - 1px), var(--stroke) var(--tick)); }
        .rf-occ-times { height: 48px; font-size: 11px; color: var(--graphite-muted); }
        .rf-occ-times span { position: absolute; top: 16px; left: var(--left); transform: translateX(-50%); }
        .rf-occ-times span:first-child { margin-left: 8px; transform: none; }
        .rf-occ-times span:last-child { margin-left: -8px; transform: translateX(-100%); }
        .rf-occ-row { min-height: 76px; border-bottom: 1px solid var(--stroke); }
        .rf-occ-row:last-child { border: 0; }
        .rf-occ-track { min-height: 76px; }
        .rf-occ-event { position: absolute; height: 48px; box-sizing: border-box; border: 1px solid; border-radius: 7px; padding: 6px 8px; overflow: hidden; white-space: nowrap; font-size: 11px; }
        .rf-occ-event strong, .rf-occ-event span { display: block; overflow: hidden; text-overflow: ellipsis; }
        .rf-occ-event span { margin-top: 3px; opacity: .75; }
        .rf-occ-brand { background: #ede9fe; border-color: #c4b5fd; color: #5b21b6; }
        .rf-occ-warning { background: #fef3c7; border-color: #fcd34d; color: #92400e; }
        .rf-occ-danger { background: #fee2e2; border-color: #fca5a5; color: #b91c1c; }
        .rf-occ-muted { background: #f0eee9; border-color: #c8c4bc; color: #737373; }
    </style>
    """
    return (
        f'{style}<div class="rf-occ" style="--tick:{step / duration:.4%}"><div class="rf-occ-inner">'
        f'<div class="rf-occ-head"><div class="rf-occ-room"><strong>Salas</strong></div>'
        f'<div class="rf-occ-times">{hours}</div></div>{"".join(rows)}</div></div>'
    )


def _close_details():
    st.session_state.pop("occupancy_detail_id", None)


@st.dialog("Detalhes da reserva", width="medium", on_dismiss=_close_details)
def _details(reservation, timezone):
    st.subheader(reservation["title"])
    start, end = local_times(reservation, timezone)
    left, right = st.columns(2)
    left.caption("Sala")
    left.text(reservation["space_name"])
    left.caption("Solicitante")
    left.text(reservation["requester_name"])
    left.caption("Participantes")
    left.text(str(reservation["participants"]))
    right.caption("Data e horário")
    right.text(f"{start:%d/%m/%Y %H:%M}–{end:%d/%m/%Y %H:%M}")
    right.caption("Status")
    right.html(badge(reservation["status"]))
    if reservation["justification"]:
        st.caption("Justificativa")
        st.text(reservation["justification"])
    if reservation["can_edit"] and st.button("Editar reserva", type="primary", icon=":material/edit:", width="stretch"):
        st.session_state["reservation_dialog"] = (reservation["id"], "edit")
        _close_details()
        st.rerun()


def _dates(context):
    current_day = date.fromisoformat(context["today"])
    previous, today, next_day, start, end = st.columns([1, 0.7, 1, 1.6, 1.6], vertical_alignment="bottom")
    previous.button("Dia anterior", icon=":material/chevron_left:", on_click=_change_day,
                    args=(current_day, -1), width="stretch")
    today.button("Hoje", on_click=_change_day, args=(current_day,), width="stretch")
    next_day.button("Próximo dia", icon=":material/chevron_right:", on_click=_change_day,
                    args=(current_day, 1), width="stretch")
    return {
        "start_date": start.date_input("Data inicial", value=current_day, key="occupancy_date", format="DD/MM/YYYY"),
        "end_date": end.date_input("Data final", value=None, key="occupancy_end", format="DD/MM/YYYY"),
    }


def _hours(context, dates):
    if dates["end_date"] not in (None, dates["start_date"]) or not st.checkbox("Consultar um horário específico"):
        return {}
    starts, ends = st.columns(2)
    return {
        "start_time": starts.time_input("Início", value=time.fromisoformat(context["opens_at"]), key="occupancy_open"),
        "end_time": ends.time_input("Fim", value=time.fromisoformat(context["closes_at"]), key="occupancy_close"),
    }


def _space_summary(report):
    counts = report["space_counts"]
    rate, available = st.columns(2)
    rate.metric("Taxa de ocupação no período", f"{report['occupancy_rate']:.1%}", border=True)
    available.metric("Salas disponíveis no período", counts["available"], border=True)
    if report["spaces"]:
        with st.expander("Ocupação e disponibilidade por sala"):
            only_available = st.checkbox("Mostrar apenas salas disponíveis", key="occupancy_only_available")
            rooms = [room for room in report["spaces"] if not only_available or room["status"] == "disponivel"]
            if not rooms:
                st.info("Nenhuma sala disponível para todo o período.")
                return
            st.dataframe([{
                "Sala": room["name"], "Prédio": room["building"], "Situação": ROOM_STATUS_LABELS[room["status"]],
                "Horas ocupadas": round(room["occupied_seconds"] / 3600, 2),
                "Horas utilizáveis": round(room["usable_seconds"] / 3600, 2),
                "Ocupação": f"{room['occupancy_rate']:.1%}",
            } for room in rooms], hide_index=True, width="stretch")


def _selected_day(report):
    start, end = (date.fromisoformat(report[key]) for key in ("start_date", "end_date"))
    if start == end:
        return start
    days = [start + timedelta(days=index) for index in range((end - start).days + 1)]
    return st.selectbox("Dia da linha do tempo", days, format_func=lambda day: f"{day:%d/%m/%Y}",
                        key="occupancy_timeline_day")


def _reservation_actions(reservations, timezone):
    choices = {item["id"]: item for item in reservations}

    def label(item_id):
        item = choices[item_id]
        start, end = local_times(item, timezone)
        return f"{item['title']} · {item['space_name']} · {start:%H:%M}–{end:%H:%M}"

    chosen = st.selectbox("Consultar reserva", list(choices), format_func=label, key="occupancy_reservation_selector")
    if st.button("Ver detalhes", icon=":material/visibility:"):
        st.session_state["occupancy_detail_id"] = chosen
    editing = st.session_state.get("reservation_dialog") == (chosen, "edit")
    if editing or st.session_state.get("occupancy_detail_id") == chosen:
        api = reservation_api()
        if api is None:
            return
        try:
            item = api.detail(chosen)
        except RESERVATION_ERRORS as error:
            st.error(str(error))
            return
        if editing and item["can_edit"]:
            edit_reservation(item)
        else:
            _details(item, timezone)


def occupancy(user):
    page_header("Ocupação", "Acompanhe as reservas dos espaços e consulte a disponibilidade.")
    api = operations_api()
    if api is None:
        return
    try:
        context = api.context()
        dates = _dates(context)
        filters = space_filters(context, "occupancy", include_status=True)
        hours = _hours(context, dates)
        report = api.report(**dates, **filters, **hours)
    except RESERVATION_ERRORS as error:
        st.error(str(error))
        return

    _space_summary(report)
    day = _selected_day(report)
    timezone = report["timezone"]
    zone = ZoneInfo(timezone)
    start = datetime.combine(day, time.min, zone)
    end = datetime.combine(day + timedelta(days=1), time.min, zone)
    reservations = [
        item for item in report["reservations"]
        if datetime.fromisoformat(item["start"]) < end and datetime.fromisoformat(item["end"]) > start
    ]
    st.caption(f"{day:%d/%m/%Y} · {len(reservations)} reservas no dia · {timezone}")
    st.markdown(":violet-badge[Aprovada] :orange-badge[Pendente / em análise] :red-badge[Conflito] :gray-badge[Rejeitada / cancelada]")
    if report["spaces"]:
        st.html(_timeline(report["spaces"], reservations, day, report, restricted=bool(hours)))
    if reservations:
        _reservation_actions(reservations, timezone)
    else:
        st.info("Nenhuma reserva encontrada para o dia e os filtros selecionados.")

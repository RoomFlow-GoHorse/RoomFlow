import calendar
from datetime import date, datetime, timedelta
import streamlit as st

from controllers.app_state_service import go
from views.components.ui_components import esc, page_header

# =========================================================
# CONSTANTES E CONFIGURAÇÕES
# =========================================================

PT_MONTHS = [
    "", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
]

PT_WEEKDAYS = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]

AGENDA_EVENTS = [
    {
        "id": "e1",
        "title": "Aula de Metodologia",
        "startTime": "08:00",
        "endTime": "10:00",
        "space": "Sala 101",
        "location": "Bloco A - 1º andar",
        "type": "Aula",
        "color": "#6D28D9",
        "date": date(2026, 8, 21),
    },
    {
        "id": "e2",
        "title": "Banca de TCC",
        "startTime": "09:30",
        "endTime": "11:00",
        "space": "Sala 204",
        "location": "Bloco B - 2º andar",
        "type": "Banca",
        "color": "#B45309",
        "date": date(2026, 8, 21),
    },
    {
        "id": "e3",
        "title": "Workshop de Pesquisa",
        "startTime": "14:00",
        "endTime": "17:00",
        "space": "Auditório Principal",
        "location": "Bloco Central",
        "type": "Workshop",
        "color": "#16A34A",
        "date": date(2026, 8, 22),
    },
    {
        "id": "e4",
        "title": "Reunião de Coordenação",
        "startTime": "10:00",
        "endTime": "11:30",
        "space": "Sala de Reuniões B",
        "location": "Administrativo",
        "type": "Reunião",
        "color": "#2563EB",
        "date": date(2026, 8, 24),
    },
]


# =========================================================
# ESTILOS CSS
# =========================================================

def _render_styles():
    st.markdown(
        """
        <style>
        .rf-calendar-card {
            background: #FFFFFF;
            border: 1px solid #E4E4E7;
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 12px;
        }
        
        .rf-event-card {
            background: #F8FAFC;
            border-left: 4px solid #6D28D9;
            border-radius: 8px;
            padding: 10px 14px;
            margin-bottom: 10px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }

        .rf-badge {
            display: inline-block;
            font-size: 11px;
            font-weight: 600;
            padding: 3px 8px;
            border-radius: 6px;
        }

        /* Estilos da Visão Mensal */
        .month-header-cell {
            text-align: center;
            font-weight: 600;
            font-size: 13px;
            color: #64748B;
            padding: 6px 0;
            background: #F1F5F9;
            border-radius: 6px;
            margin-bottom: 8px;
        }

        .month-day-cell {
            min-height: 95px;
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            padding: 6px;
            display: flex;
            flex-direction: column;
            gap: 4px;
            box-sizing: border-box;
            margin-bottom: 8px;
        }

        .month-day-cell.other-month {
            background: #F8FAFC;
            opacity: 0.4;
        }

        .month-day-cell.selected-day {
            border: 2px solid #6D28D9;
            background-color: #F3E8FF;
        }

        .month-day-num {
            font-size: 12px;
            font-weight: 700;
            color: #334155;
            margin-bottom: 2px;
        }

        .month-event-pill {
            font-size: 10px;
            padding: 2px 5px;
            border-radius: 4px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            color: #FFFFFF;
            font-weight: 500;
            margin-bottom: 2px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# HELPERS DE DATA & NAVEGAÇÃO
# =========================================================

def _get_current_selected_date() -> date:
    selected = st.session_state.get("agenda_selected_date")
    if not isinstance(selected, date):
        selected = date(2026, 8, 21)
        st.session_state.agenda_selected_date = selected
    return selected


def _change_date(direction: int):
    current_date = _get_current_selected_date()
    view = st.session_state.get("agenda_view_tab", "Semanal")

    if view == "Diário":
        st.session_state.agenda_selected_date = current_date + timedelta(days=direction)
    elif view == "Semanal":
        st.session_state.agenda_selected_date = current_date + timedelta(weeks=direction)
    elif view == "Mensal":
        month = current_date.month + direction
        year = current_date.year
        if month > 12:
            month = 1
            year += 1
        elif month < 1:
            month = 12
            year -= 1
        st.session_state.agenda_selected_date = date(year, month, min(current_date.day, 28))


def _set_today():
    st.session_state.agenda_selected_date = date(2026, 8, 21)


def _render_calendar_navigation(title: str):
    col_prev, col_title, col_next, col_today = st.columns([0.5, 4, 0.5, 1], vertical_alignment="center")

    with col_prev:
        st.button("‹", key="btn_prev", on_click=_change_date, args=(-1,), use_container_width=True)

    with col_title:
        st.markdown(
            f"<h4 style='text-align: center; margin: 0; color: #1E293B;'>{title}</h4>",
            unsafe_allow_html=True,
        )

    with col_next:
        st.button("›", key="btn_next", on_click=_change_date, args=(1,), use_container_width=True)

    with col_today:
        st.button("Hoje", key="btn_today", on_click=_set_today, type="secondary", use_container_width=True)


# =========================================================
# VISÕES (DIÁRIO, SEMANAL, MENSAL)
# =========================================================

def _render_daily_view(events: list, selected_date: date):
    weekday_str = PT_WEEKDAYS[selected_date.weekday()]
    month_str = PT_MONTHS[selected_date.month]
    formatted_header = f"{weekday_str}, {selected_date.day} de {month_str} de {selected_date.year}"

    _render_calendar_navigation(formatted_header)
    st.divider()

    day_events = [e for e in events if e["date"] == selected_date]
    day_events = sorted(day_events, key=lambda x: x["startTime"])

    col_stat1, col_stat2 = st.columns(2)
    with col_stat1:
        st.metric("Total de Compromissos", len(day_events))
    with col_stat2:
        next_event = day_events[0]["startTime"] if day_events else "Nenhum"
        st.metric("Primeiro Compromisso", next_event)

    st.markdown("<br>", unsafe_allow_html=True)

    if not day_events:
        st.info("Nenhuma atividade agendada para este dia.")
        return

    for event in day_events:
        color = event["color"]
        st.markdown(
            f"""
            <div class="rf-event-card" style="border-left-color: {color};">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                    <strong style="font-size: 15px; color: #0F172A;">{esc(event["title"])}</strong>
                    <span class="rf-badge" style="background-color: {color}1F; color: {color};">
                        {esc(event["type"])}
                    </span>
                </div>
                <div style="font-size: 13px; color: #475569;">
                    🕒 <strong>{esc(event["startTime"])} – {esc(event["endTime"])}</strong> &nbsp;|&nbsp; 📍 {esc(event["space"])} ({esc(event["location"])})
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_weekly_view(events: list, selected_date: date):
    start_of_week = selected_date - timedelta(days=selected_date.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    title = f"{start_of_week.day}/{start_of_week.month:02d} a {end_of_week.day}/{end_of_week.month:02d} de {end_of_week.year}"
    _render_calendar_navigation(title)
    st.divider()

    cols = st.columns(7)
    week_day_labels = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]

    for i, col in enumerate(cols):
        current_day = start_of_week + timedelta(days=i)
        is_selected = current_day == selected_date

        with col:
            header_bg = "#6D28D9" if is_selected else "#F1F5F9"
            header_color = "#FFFFFF" if is_selected else "#334155"

            st.markdown(
                f"""
                <div style="text-align: center; padding: 8px 4px; border-radius: 8px; background-color: {header_bg}; color: {header_color}; margin-bottom: 10px;">
                    <span style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px;">{week_day_labels[i]}</span><br>
                    <strong style="font-size: 16px;">{current_day.day}</strong>
                </div>
                """,
                unsafe_allow_html=True,
            )

            day_events = [e for e in events if e["date"] == current_day]
            day_events = sorted(day_events, key=lambda x: x["startTime"])

            if not day_events:
                st.markdown("<div style='text-align:center; color:#94A3B8; font-size:12px; margin-top:12px;'>—</div>", unsafe_allow_html=True)
            else:
                for event in day_events:
                    color = event["color"]
                    st.markdown(
                        f"""
                        <div style="background: #F8FAFC; border-left: 3px solid {color}; border-radius: 6px; padding: 6px 8px; margin-bottom: 6px; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
                            <div style="font-weight: 600; font-size: 12px; color: #1E293B; line-height: 1.2;">{esc(event['title'])}</div>
                            <div style="font-size: 10px; color: #64748B; margin-top: 4px;">🕒 {esc(event['startTime'])}</div>
                            <div style="font-size: 10px; color: #64748B;">📍 {esc(event['space'])}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )


def _render_monthly_view(events: list, selected_date: date):
    month_name = PT_MONTHS[selected_date.month]
    _render_calendar_navigation(f"{month_name} de {selected_date.year}")
    st.divider()

    # Mapeamento de eventos por data
    events_by_date = {}
    for e in events:
        events_by_date.setdefault(e["date"], []).append(e)

    # Matriz do mês
    cal = calendar.Calendar(firstweekday=0)
    month_days = cal.monthdatescalendar(selected_date.year, selected_date.month)

    # Cabeçalho dos dias da semana
    header_cols = st.columns(7)
    week_days = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
    for idx, day_name in enumerate(week_days):
        header_cols[idx].markdown(
            f'<div class="month-header-cell">{day_name}</div>',
            unsafe_allow_html=True
        )

    # Renderiza semana por semana usando as colunas nativas do Streamlit
    for week in month_days:
        cols = st.columns(7)
        for idx, day in enumerate(week):
            is_other_month = day.month != selected_date.month
            is_selected = day == selected_date

            classes = ["month-day-cell"]
            if is_other_month:
                classes.append("other-month")
            if is_selected:
                classes.append("selected-day")

            day_events = events_by_date.get(day, [])
            events_html = ""

            for ev in day_events[:3]:
                events_html += f"""
                <div class="month-event-pill" style="background-color: {ev['color']};" title="{esc(ev['title'])} ({ev['startTime']})">
                    {esc(ev['startTime'])} {esc(ev['title'])}
                </div>
                """

            if len(day_events) > 3:
                events_html += f"<div style='font-size: 9px; color: #64748B; text-align: right;'>+{len(day_events) - 3} mais</div>"

            cols[idx].markdown(
                f"""
                <div class="{" ".join(classes)}">
                    <div class="month-day-num">{day.day}</div>
                    {events_html}
                </div>
                """,
                unsafe_allow_html=True,
            )


# =========================================================
# PÁGINA PRINCIPAL
# =========================================================

def agenda(user: dict):
    _render_styles()

    if "agenda_view_tab" not in st.session_state:
        st.session_state.agenda_view_tab = "Semanal"

    selected_date = _get_current_selected_date()

    col_header, col_view = st.columns([2, 1], vertical_alignment="center")

    with col_header:
        page_header(
            "Agenda",
            "Visualize suas atividades, eventos e compromissos.",
        )

    with col_view:
        st.segmented_control(
            "Visualização",
            ["Diário", "Semanal", "Mensal"],
            key="agenda_view_tab",
        )

    active_view = st.session_state.agenda_view_tab

    with st.container():
        if active_view == "Diário":
            _render_daily_view(AGENDA_EVENTS, selected_date)
        elif active_view == "Mensal":
            _render_monthly_view(AGENDA_EVENTS, selected_date)
        else:
            _render_weekly_view(AGENDA_EVENTS, selected_date)
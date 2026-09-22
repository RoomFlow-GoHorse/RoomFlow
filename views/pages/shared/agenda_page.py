import streamlit as st

from controllers.app_state_service import go
from views.components.ui_components import esc, page_header


# =========================================================
# DADOS DA AGENDA
# =========================================================

WEEK_DAYS = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"]

WEEK_DATES = [
    {"day": "Dom", "date": 18, "month": "ago"},
    {"day": "Seg", "date": 19, "month": "ago"},
    {"day": "Ter", "date": 20, "month": "ago"},
    {"day": "Qua", "date": 21, "month": "ago"},
    {"day": "Qui", "date": 22, "month": "ago"},
    {"day": "Sex", "date": 23, "month": "ago"},
    {"day": "Sáb", "date": 24, "month": "ago"},
]

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
        "dayNumber": 21,
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
        "dayNumber": 21,
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
        "dayNumber": 22,
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
        "dayNumber": 24,
    },
]


# =========================================================
# ESTILOS
# =========================================================

def _render_styles():
    st.html(
        """
        <style>

        /* =================================================
           CONTAINER PRINCIPAL DO CALENDÁRIO
           ================================================= */

        .rf-calendar-card {
            background: #FFFFFF;
            border: 1px solid #E4E1DB;
            border-radius: 14px;
            overflow: hidden;
        }

        /* =================================================
           CABEÇALHO DOS DIAS
           ================================================= */

        .rf-week-header {
            display: grid;
            grid-template-columns: repeat(7, 1fr);
            border-bottom: 1px solid #E4E1DB;
        }

        .rf-week-day {
            min-height: 96px;
            padding: 18px 12px;
            text-align: center;
            border-right: 1px solid #E4E1DB;
        }

        .rf-week-day:last-child {
            border-right: none;
        }

        .rf-week-day-name {
            font-size: 11px;
            color: #71717A;
            margin-bottom: 8px;
        }

        .rf-week-day-number {
            font-size: 16px;
            font-weight: 600;
            color: #1C1C2E;
        }

        .rf-week-day-month {
            font-size: 10px;
            color: #A1A1AA;
            margin-top: 3px;
        }

        .rf-week-day.active {
            background: #6D28D9;
        }

        .rf-week-day.active .rf-week-day-name,
        .rf-week-day.active .rf-week-day-number,
        .rf-week-day.active .rf-week-day-month {
            color: #FFFFFF;
        }

        /* =================================================
           CORPO DA SEMANA
           ================================================= */

        .rf-week-body {
            display: grid;
            grid-template-columns: repeat(7, 1fr);
        }

        .rf-week-column {
            min-height: 210px;
            padding: 12px;
            border-right: 1px solid #E4E1DB;
        }

        .rf-week-column:last-child {
            border-right: none;
        }

        .rf-empty-day {
            height: 130px;
            border: 1px solid #E4E1DB;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #A1A1AA;
            font-size: 11px;
        }

        .rf-week-column.active {
            background: #FAF9FF;
        }

        .rf-event {
            border-radius: 7px;
            padding: 8px;
            margin-bottom: 8px;
            border-left: 3px solid;
        }

        .rf-event-title {
            font-size: 11px;
            font-weight: 600;
            color: #1C1C2E;
            margin: 0 0 3px 0;
        }

        .rf-event-time {
            font-size: 10px;
            color: #71717A;
            margin: 0;
        }

        /* =================================================
           CALENDÁRIO MENSAL
           ================================================= */

        .rf-month-grid {
            display: grid;
            grid-template-columns: repeat(7, 1fr);
        }

        .rf-month-weekday {
            padding: 14px 8px;
            text-align: center;
            font-size: 11px;
            font-weight: 600;
            color: #71717A;
            border-bottom: 1px solid #E4E1DB;
        }

        .rf-month-cell {
            min-height: 90px;
            padding: 10px;
            border-right: 1px solid #E4E1DB;
            border-bottom: 1px solid #E4E1DB;
        }

        .rf-month-cell:nth-child(7n) {
            border-right: none;
        }

        .rf-month-number {
            font-size: 12px;
            font-weight: 500;
            color: #52525B;
        }

        .rf-month-cell.active {
            background: #F5F3FF;
        }

        .rf-month-cell.active .rf-month-number {
            color: #6D28D9;
            font-weight: 700;
        }

        .rf-month-event {
            margin-top: 8px;
            padding: 5px 6px;
            border-radius: 5px;
            font-size: 9px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        /* =================================================
           CALENDÁRIO DIÁRIO
           ================================================= */

        .rf-daily-calendar {
            padding: 24px;
        }

        .rf-daily-date {
            display: flex;
            align-items: center;
            gap: 14px;
            padding-bottom: 20px;
            border-bottom: 1px solid #E4E1DB;
            margin-bottom: 20px;
        }

        .rf-daily-number {
            width: 52px;
            height: 52px;
            border-radius: 12px;
            background: #6D28D9;
            color: #FFFFFF;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }

        .rf-daily-number strong {
            font-size: 18px;
            line-height: 1;
        }

        .rf-daily-number span {
            font-size: 9px;
            margin-top: 3px;
        }

        .rf-daily-title {
            font-size: 15px;
            font-weight: 600;
            color: #1C1C2E;
            margin: 0;
        }

        .rf-daily-subtitle {
            font-size: 12px;
            color: #71717A;
            margin: 3px 0 0 0;
        }

        .rf-daily-event {
            display: flex;
            gap: 18px;
            margin-bottom: 12px;
        }

        .rf-daily-time {
            width: 55px;
            text-align: right;
            font-size: 11px;
            color: #71717A;
            padding-top: 10px;
        }

        .rf-daily-event-card {
            flex: 1;
            background: #F8F7F4;
            border: 1px solid #E4E1DB;
            border-radius: 10px;
            padding: 12px;
        }

        </style>
        """
    )


# =========================================================
# HELPERS
# =========================================================

def _navigate(page: str) -> None:
    go(page)
    st.rerun()


def _render_event(event: dict):
    color = event["color"]

    st.html(
        f"""
        <div
            class="rf-event"
            style="
                background: {color}12;
                border-left-color: {color};
            "
        >
            <p class="rf-event-title">
                {esc(event["title"])}
            </p>

            <p class="rf-event-time">
                🕒 {esc(event["startTime"])}
            </p>
        </div>
        """
    )


# =========================================================
# NAVEGAÇÃO DO CALENDÁRIO
# =========================================================

def _render_calendar_navigation(
    title: str,
    today_label: str = "Hoje",
):
    col_left, col_center, col_right = st.columns(
        [0.5, 5, 0.8],
        vertical_alignment="center",
    )

    with col_left:
        if st.button(
            "‹",
            key=f"calendar_prev_{title}",
        ):
            st.session_state.agenda_selected_date = max(
                1,
                st.session_state.agenda_selected_date - 1,
            )
            st.rerun()

    with col_center:
        st.markdown(
            f"""
            <div
                style="
                    font-size:14px;
                    font-weight:600;
                    color:#1C1C2E;
                    text-align:center;
                "
            >
                {title}
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_right:
        if st.button(
            today_label,
            key=f"calendar_today_{title}",
            type="tertiary",
        ):
            st.session_state.agenda_selected_date = 21
            st.rerun()


# =========================================================
# VISÃO SEMANAL
# =========================================================

def _render_weekly_view(events: list):
    selected_date = st.session_state.agenda_selected_date

    _render_calendar_navigation(
        "18–24 de agosto de 2026"
    )

    st.markdown(
        '<div style="height:16px;"></div>',
        unsafe_allow_html=True,
    )

    html = """
    <div class="rf-calendar-card">

        <div class="rf-week-header">
    """

    for item in WEEK_DATES:
        active = item["date"] == selected_date

        html += f"""
            <div class="rf-week-day {'active' if active else ''}">
                <div class="rf-week-day-name">
                    {item['day']}
                </div>

                <div class="rf-week-day-number">
                    {item['date']}
                </div>

                <div class="rf-week-day-month">
                    {item['month']}
                </div>
            </div>
        """

    html += """
        </div>

        <div class="rf-week-body">
    """

    for item in WEEK_DATES:
        active = item["date"] == selected_date

        day_events = [
            event
            for event in events
            if event["dayNumber"] == item["date"]
        ]

        html += f"""
            <div class="rf-week-column {'active' if active else ''}">
        """

        if not day_events:
            html += """
                <div class="rf-empty-day">
                    Sem eventos
                </div>
            """
        else:
            for event in day_events:
                color = event["color"]

                html += f"""
                    <div
                        class="rf-event"
                        style="
                            background:{color}12;
                            border-left-color:{color};
                        "
                    >
                        <p class="rf-event-title">
                            {esc(event["title"])}
                        </p>

                        <p class="rf-event-time">
                            🕒 {esc(event["startTime"])}
                        </p>
                    </div>
                """

        html += """
            </div>
        """

    html += """
        </div>
    </div>
    """

    st.html(html)


# =========================================================
# VISÃO DIÁRIA
# =========================================================

def _render_daily_view(events: list):
    selected_date = st.session_state.agenda_selected_date

    _render_calendar_navigation(
        "Quarta-feira, 21 de agosto de 2026"
    )

    st.markdown(
        '<div style="height:16px;"></div>',
        unsafe_allow_html=True,
    )

    day_events = [
        event
        for event in events
        if event["dayNumber"] == selected_date
    ]

    html = """
    <div class="rf-calendar-card">
        <div class="rf-daily-calendar">

            <div class="rf-daily-date">

                <div class="rf-daily-number">
                    <strong>21</strong>
                    <span>AGO</span>
                </div>

                <div>
                    <p class="rf-daily-title">
                        Quarta-feira
                    </p>

                    <p class="rf-daily-subtitle">
                        21 de agosto de 2026
                    </p>
                </div>

            </div>
    """

    if not day_events:
        html += """
            <div
                style="
                    text-align:center;
                    padding:50px 0;
                    color:#A1A1AA;
                    font-size:12px;
                "
            >
                Nenhuma atividade neste dia.
            </div>
        """

    else:
        for event in day_events:
            color = event["color"]

            html += f"""
                <div class="rf-daily-event">

                    <div class="rf-daily-time">
                        {esc(event["startTime"])}
                    </div>

                    <div
                        class="rf-daily-event-card"
                        style="
                            border-left:3px solid {color};
                        "
                    >
                        <p
                            style="
                                font-size:13px;
                                font-weight:600;
                                color:#1C1C2E;
                                margin:0 0 5px 0;
                            "
                        >
                            {esc(event["title"])}
                        </p>

                        <p
                            style="
                                font-size:11px;
                                color:#71717A;
                                margin:0;
                            "
                        >
                            🕒 {esc(event["startTime"])}
                            – {esc(event["endTime"])}
                            &nbsp;&nbsp;
                            📍 {esc(event["space"])}
                        </p>
                    </div>

                </div>
            """

    html += """
        </div>
    </div>
    """

    st.html(html)


# =========================================================
# VISÃO MENSAL
# =========================================================

def _render_monthly_view(events: list):
    selected_date = st.session_state.agenda_selected_date

    _render_calendar_navigation(
        "Agosto 2026"
    )

    st.markdown(
        '<div style="height:16px;"></div>',
        unsafe_allow_html=True,
    )

    days_with_events = {
        event["dayNumber"]
        for event in events
    }

    html = """
    <div class="rf-calendar-card">

        <div class="rf-month-grid">
    """

    # Cabeçalho
    for day in WEEK_DAYS:
        html += f"""
            <div class="rf-month-weekday">
                {day}
            </div>
        """

    # Espaços antes do dia 1
    for _ in range(5):
        html += """
            <div class="rf-month-cell"></div>
        """

    # Dias
    for day in range(1, 32):
        active = day == selected_date
        has_event = day in days_with_events

        html += f"""
            <div class="rf-month-cell {'active' if active else ''}">

                <div class="rf-month-number">
                    {day}
                </div>
        """

        day_events = [
            event
            for event in events
            if event["dayNumber"] == day
        ]

        for event in day_events:
            color = event["color"]

            html += f"""
                <div
                    class="rf-month-event"
                    style="
                        background:{color}15;
                        color:#1C1C2E;
                        border-left:2px solid {color};
                    "
                >
                    {esc(event["title"])}
                </div>
            """

        if has_event and not day_events:
            html += """
                <div
                    style="
                        width:5px;
                        height:5px;
                        background:#6D28D9;
                        border-radius:50%;
                        margin-top:8px;
                    "
                ></div>
            """

        html += """
            </div>
        """

    html += """
        </div>
    </div>
    """

    st.html(html)


# =========================================================
# PÁGINA PRINCIPAL
# =========================================================

def agenda(user: dict):
    _render_styles()

    # Estado inicial
    st.session_state.setdefault(
        "agenda_view_tab",
        "Semanal",
    )

    st.session_state.setdefault(
        "agenda_selected_date",
        21,
    )

    # =====================================================
    # CABEÇALHO
    # =====================================================

    col_header, col_view = st.columns(
        [2, 1],
        vertical_alignment="center",
    )

    with col_header:
        page_header(
            "Agenda",
            "Visualize suas atividades, eventos e compromissos.",
        )

    with col_view:
        view_tab = st.segmented_control(
            "Visualização",
            ["Diário", "Semanal", "Mensal"],
            key="agenda_view_control",
            default=st.session_state.agenda_view_tab,
        )

        if view_tab:
            st.session_state.agenda_view_tab = view_tab

    # =====================================================
    # CALENDÁRIO
    # =====================================================

    events = AGENDA_EVENTS

    active_view = st.session_state.agenda_view_tab

    if active_view == "Diário":
        _render_daily_view(events)

    elif active_view == "Mensal":
        _render_monthly_view(events)

    else:
        _render_weekly_view(events)
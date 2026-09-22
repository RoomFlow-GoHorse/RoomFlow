from datetime import date, datetime

import streamlit as st

from controllers import mock_data_service
from controllers.app_state_service import go
from views.components.ui_components import badge


_WEEKDAYS = (
    "segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
    "sexta-feira", "sábado", "domingo",
)
_MONTHS = (
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
)


def _today_label() -> str:
    today = date.today()
    return f"{_WEEKDAYS[today.weekday()].capitalize()}, {today.day} de {_MONTHS[today.month - 1]} de {today.year}"


def _reservation_date(value: str) -> str:
    try:
        return datetime.fromisoformat(value).strftime("%d/%m/%Y")
    except (TypeError, ValueError):
        return value


def _render_styles():
    st.html(
        """
        <style>
        [class*="st-key-rf_requester_notification_unread_"] {
            background: #F5F3FF !important;
            border-color: rgba(109, 40, 217, 0.25) !important;
        }
        </style>
        """
    )


def _render_metrics(upcoming: list[dict], pending: list[dict], conflicts: list[dict], unread: int):
    metrics = (
        (":material/calendar_month: Próximas reservas", len(upcoming), ""),
        (":material/schedule: Pendentes", len(pending), ""),
        (":material/warning: Conflitos", len(conflicts), ""),
        (":material/notifications: Notificações", unread, "não lidas"),
    )

    for column, (label, value, subtext) in zip(st.columns(4), metrics):
        with column:
            with st.container(border=True):
                st.caption(label)
                st.markdown(f"### {value}")
                if subtext:
                    st.caption(subtext)


def _render_reservations(reservations: list[dict]):
    with st.container(border=True):
        heading, action = st.columns([4, 1], vertical_alignment="center")
        with heading:
            st.markdown("**Minhas reservas**")
            st.caption("Acompanhe suas solicitações e reservas")
        with action:
            if st.button("Ver todas →", key="requester_all_reservations", type="tertiary"):
                go("minhas_reservas")
                st.rerun()

        if not reservations:
            st.info("Nenhuma reserva encontrada.")
            if st.button("Solicitar uma reserva →", key="requester_empty_reservations", type="tertiary"):
                go("nova_reserva")
                st.rerun()
            return

        for reservation in reservations[:4]:
            with st.container(border=True, key=f"rf_requester_reservation_{reservation['id']}"):
                details, status = st.columns([4, 1], vertical_alignment="center")
                with details:
                    st.markdown(f"**{reservation['type']} — {reservation['space']}**")
                    st.caption(
                        f"{_reservation_date(reservation['date'])} · "
                        f"{reservation['start']}–{reservation['end']}"
                    )
                with status:
                    st.html(badge(reservation["status"]))


def _render_notifications(notifications: list[dict]):
    with st.container(border=True):
        heading, action = st.columns([4, 1], vertical_alignment="center")
        with heading:
            st.markdown("**Notificações**")
            st.caption("Atualizações recentes")
        with action:
            if st.button("Ver todas →", key="requester_all_notifications", type="tertiary"):
                go("notificacoes")
                st.rerun()

        if not notifications:
            st.success("Tudo em dia!")
            st.caption("Você não possui novas notificações.")
            return

        for notification in notifications[:4]:
            key_prefix = "rf_requester_notification_unread" if not notification.get("read", False) else "rf_requester_notification"
            with st.container(border=True, key=f"{key_prefix}_{notification['id']}"):
                title, unread_marker = st.columns([20, 1], vertical_alignment="center")
                with title:
                    st.markdown(f"**{notification['title']}**")
                with unread_marker:
                    if not notification.get("read", False):
                        st.markdown(":violet[●]")
                st.caption(notification["message"])
                st.caption(notification["date"])


def dashboard(user):
    _render_styles()

    reservations = mock_data_service.reservations(requester_id=user["id"])
    upcoming = [item for item in reservations if item["status"] == "aprovada"]
    pending = [item for item in reservations if item["status"] in {"pendente", "em_analise"}]
    conflicts = [item for item in reservations if item["status"] == "conflito"]
    notifications = [
        item
        for item in mock_data_service.notifications_for(user["role"])
        if item.get("category") != "sistema"
    ]
    unread = sum(not item.get("read", False) for item in notifications)

    header, action = st.columns([4, 1], vertical_alignment="center")
    with header:
        first_name = user.get("name", "Usuário").split()[0]
        st.title(f"Olá, {first_name}!")
        st.caption(_today_label())
    with action:
        if st.button("Solicitar reserva", key="requester_new_reservation", icon=":material/add:", type="primary"):
            go("nova_reserva")
            st.rerun()

    _render_metrics(upcoming, pending, conflicts, unread)

    reservations_column, notifications_column = st.columns([2, 1], gap="medium")
    with reservations_column:
        _render_reservations(reservations)
    with notifications_column:
        _render_notifications(notifications)

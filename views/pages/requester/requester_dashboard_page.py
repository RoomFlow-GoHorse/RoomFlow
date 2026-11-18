from datetime import date, datetime
import streamlit as st

from controllers import mock_data_service
from controllers.app_state_service import go
from views.components.ui_components import badge, page_header

# ============================================================
# CONSTANTES E HELPERS DE DATA
# ============================================================

_WEEKDAYS = (
    "segunda-feira",
    "terça-feira",
    "quarta-feira",
    "quinta-feira",
    "sexta-feira",
    "sábado",
    "domingo",
)

_MONTHS = (
    "janeiro",
    "fevereiro",
    "março",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
)


def _today_label() -> str:
    today = date.today()
    weekday = _WEEKDAYS[today.weekday()].capitalize()
    month = _MONTHS[today.month - 1]
    return f"{weekday}, {today.day} de {month} de {today.year}"


def _format_date(iso_date_str: str) -> str:
    try:
        return datetime.fromisoformat(iso_date_str).strftime("%d/%m/%Y")
    except (TypeError, ValueError):
        return iso_date_str

# ============================================================
# SUBCOMPONENTES DE RENDERIZAÇÃO
# ============================================================

def _render_metrics(upcoming_count: int, pending_count: int, conflicts_count: int, unread_count: int):
    col1, col2, col3, col4 = st.columns(4)

    metrics_data = [
        (col1, "Próximas reservas", upcoming_count, ":material/calendar_month:"),
        (col2, "Pendentes", pending_count, ":material/schedule:"),
        (col3, "Conflitos", conflicts_count, ":material/warning:"),
        (col4, "Notificações", unread_count, ":material/notifications:"),
    ]

    for col, label, value, icon in metrics_data:
        with col:
            with st.container(border=True):
                st.caption(f"{icon} {label}")
                st.metric(label=label, value=value, label_visibility="collapsed")


def _render_reservations_section(reservations: list[dict]):
    with st.container(border=True):
        header_col, action_col = st.columns([4, 1], vertical_alignment="center")

        with header_col:
            st.markdown("**Minhas reservas**")
            st.caption("Acompanhe suas solicitações recentes")

        with action_col:
            if st.button("Ver todas", key="btn_go_my_reservations", type="tertiary", use_container_width=True):
                go("minhas_reservas")
                st.rerun()

        st.divider()

        if not reservations:
            st.info("Você ainda não possui solicitações ou reservas cadastradas.", icon=":material/info:")
            if st.button("Criar primeira reserva", key="btn_empty_new_reservation", icon=":material/add:", type="secondary"):
                go("nova_reserva")
                st.rerun()
            return

        for reservation in reservations[:4]:
            with st.container(border=True):
                details_col, status_col = st.columns([4, 1], vertical_alignment="center")

                with details_col:
                    st.markdown(f"**{reservation.get('type', 'Reserva')} — {reservation.get('space', 'Espaço')}**")
                    st.caption(
                        f"{_format_date(reservation.get('date', ''))} · "
                        f"{reservation.get('start', '')}–{reservation.get('end', '')}"
                    )

                with status_col:
                    st.html(badge(reservation.get("status", "pendente")))


def _render_notifications_section(notifications: list[dict]):
    with st.container(border=True):
        header_col, action_col = st.columns([3, 1], vertical_alignment="center")

        with header_col:
            st.markdown("**Notificações**")
            st.caption("Atualizações recentes")

        with action_col:
            if st.button("Ver todas", key="btn_go_notifications", type="tertiary", use_container_width=True):
                go("notificacoes")
                st.rerun()

        st.divider()

        if not notifications:
            st.success("Tudo em dia!", icon=":material/check_circle:")
            st.caption("Você não possui novas notificações no momento.")
            return

        for notification in notifications[:4]:
            is_unread = not notification.get("read", False)
            with st.container(border=True):
                title_col, marker_col = st.columns([12, 1], vertical_alignment="center")

                with title_col:
                    st.markdown(f"**{notification.get('title', 'Notificação')}**")

                with marker_col:
                    if is_unread:
                        st.caption(":violet[:material/circle:]")

                st.caption(notification.get("message", ""))
                st.caption(f":material/schedule: {notification.get('date', '')}")

# ============================================================
# MAIN DASHBOARD VIEW
# ============================================================

def dashboard(user: dict):
    user_name = user.get("name", "Usuário").split()[0]
    
    col_header, col_action = st.columns([3, 1], vertical_alignment="bottom")
    with col_header:
        page_header(f"Olá, {user_name}!", _today_label())
    with col_action:
        if st.button("Nova reserva", key="btn_dashboard_new_reservation", icon=":material/add:", type="primary", use_container_width=True):
            go("nova_reserva")
            st.rerun()

    # Busca de dados do usuário
    user_id = user.get("id")
    reservations = mock_data_service.reservations(requester_id=user_id) if user_id else []

    upcoming = [r for r in reservations if r.get("status") == "aprovada"]
    pending = [r for r in reservations if r.get("status") in {"pendente", "em_analise"}]
    conflicts = [r for r in reservations if r.get("status") == "conflito"]

    user_role = user.get("role", "solicitante")
    all_notifications = mock_data_service.notifications_for(user_role)
    notifications = [n for n in all_notifications if n.get("category") != "sistema"]
    unread_count = sum(not n.get("read", False) for n in notifications)

    # Métricas
    _render_metrics(
        upcoming_count=len(upcoming),
        pending_count=len(pending),
        conflicts_count=len(conflicts),
        unread_count=unread_count,
    )

    st.write("")

    # Grid principal
    res_col, notif_col = st.columns([2, 1], gap="medium")

    with res_col:
        _render_reservations_section(reservations)

    with notif_col:
        _render_notifications_section(notifications)
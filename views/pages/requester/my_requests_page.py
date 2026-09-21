"""Página de acompanhamento e gestão das solicitações do solicitante."""

from datetime import date, datetime

import streamlit as st

from controllers import mock_data_service
from controllers.app_state_service import go, set_toast
from views.components.ui_components import badge, page_header


_PENDING_STATUSES = {"pendente", "em_analise"}


def _date_label(value: str) -> str:
    try:
        return datetime.fromisoformat(value).strftime("%d/%m/%Y")
    except (TypeError, ValueError):
        return value


def _resources_for(reservation: dict) -> list[str]:
    if reservation.get("resources"):
        return reservation["resources"]
    room = next((space for space in st.session_state.spaces if space["name"] == reservation["space"]), None)
    return room.get("resources", []) if room else []


def _remove_reservation(reservation_id: str):
    st.session_state.reservations = [item for item in st.session_state.reservations if item["id"] != reservation_id]
    set_toast("Reserva cancelada. O espaço foi liberado.")


def _update_reservation(reservation_id: str, room: dict, day: date, start, end):
    for item in st.session_state.reservations:
        if item["id"] == reservation_id:
            item.update(status="em_analise", space=room["name"], date=day.isoformat(), start=start.strftime("%H:%M"), end=end.strftime("%H:%M"))
            break
    set_toast("Alteração enviada para análise.")


@st.dialog("Cancelar reserva")
def _cancel_dialog(reservation: dict):
    st.markdown(f"**{reservation['type']}**")
    st.caption(f"{reservation['space']} · {_date_label(reservation['date'])} · {reservation['start']}–{reservation['end']}")
    st.warning("Deseja realmente cancelar? O espaço será liberado e os participantes poderão ser notificados.", icon=":material/warning:")
    st.text_area("Motivo do cancelamento (opcional)", placeholder="Ex.: A atividade foi remarcada.")
    keep, cancel = st.columns(2)
    if keep.button("Manter reserva", width="stretch"):
        st.rerun()
    if cancel.button("Cancelar reserva", key=f"confirm_cancel_{reservation['id']}", type="primary", width="stretch"):
        _remove_reservation(reservation["id"])
        st.rerun()


@st.dialog("Solicitar alteração", width="large")
def _alter_dialog(reservation: dict):
    required_resources = _resources_for(reservation)
    st.info("Escolha uma nova data, horário e sala. Serão exibidos somente espaços compatíveis com os recursos da atividade.", icon=":material/sync:")
    with st.container(border=True):
        st.caption("SOLICITAÇÃO ATUAL")
        activity, room, participants = st.columns([2, 2, 1])
        activity.markdown(f"**Atividade**\n\n{reservation['type']}")
        room.markdown(f"**Sala atual**\n\n{reservation['space']}")
        participants.markdown(f"**Participantes**\n\n{reservation.get('participants', 'Não informado')}")

    st.markdown("**Recursos definidos**")
    if required_resources:
        st.markdown(" · ".join(f":violet-badge[{resource}]" for resource in required_resources))
    else:
        st.caption("Nenhum recurso específico foi informado para esta solicitação.")

    st.markdown("**Novo período**")
    st.caption("Defina quando deseja realizar a atividade.")
    with st.form(f"alter_reservation_{reservation['id']}"):
        new_day, new_start, new_end = st.columns(3)
        with new_day:
            selected_day = st.date_input("Nova data", value=date.fromisoformat(reservation["date"]))
        with new_start:
            selected_start = st.time_input("Horário de início", value=datetime.strptime(reservation["start"], "%H:%M").time())
        with new_end:
            selected_end = st.time_input("Horário de término", value=datetime.strptime(reservation["end"], "%H:%M").time())

        compatible_rooms = [space for space in st.session_state.spaces if space["status"] != "bloqueado" and all(resource in space.get("resources", []) for resource in required_resources)]
        st.markdown("**Salas disponíveis**")
        st.caption(f"{len(compatible_rooms)} sala(s) compatível(is) com os recursos solicitados.")
        room_names = [space["name"] for space in compatible_rooms]
        selected_name = st.selectbox("Escolha uma sala", room_names, index=None, placeholder="Selecione uma sala")
        st.info("Ao enviar a alteração, a solicitação será novamente analisada pelo administrador.", icon=":material/info:")
        submitted = st.form_submit_button("Enviar alteração", type="primary", width="stretch")

    if submitted:
        if not selected_name:
            st.error("Selecione uma sala compatível antes de enviar a alteração.")
        elif selected_start >= selected_end:
            st.error("O horário de término deve ser posterior ao horário de início.")
        else:
            selected_room = next(space for space in compatible_rooms if space["name"] == selected_name)
            _update_reservation(reservation["id"], selected_room, selected_day, selected_start, selected_end)
            st.rerun()


def _render_summary(items: list[dict]):
    counts = (("Total", len(items)), ("Pendentes", sum(item["status"] in _PENDING_STATUSES for item in items)), ("Aprovadas", sum(item["status"] == "aprovada" for item in items)), ("Reprovadas", sum(item["status"] == "rejeitada" for item in items)))
    for column, (label, count) in zip(st.columns(4), counts):
        with column:
            with st.container(border=True):
                st.caption(label)
                st.markdown(f"### {count}")


def _render_card(reservation: dict):
    with st.container(border=True):
        content, status = st.columns([5, 1], vertical_alignment="top")
        with content:
            st.markdown(f"**{reservation['title']}**")
            st.caption(f":material/meeting_room: {reservation['space']}  ·  :material/calendar_today: {_date_label(reservation['date'])}  ·  :material/schedule: {reservation['start']}–{reservation['end']}")
            if reservation.get("participants"):
                st.caption(f":material/groups: {reservation['participants']} participantes")
        with status:
            st.html(badge(reservation["status"]))
        if reservation.get("justification"):
            st.caption(reservation["justification"])
        with st.container(horizontal=True):
            if st.button("Solicitar alteração", key=f"alter_{reservation['id']}", icon=":material/edit_calendar:"):
                _alter_dialog(reservation)
            if st.button("Cancelar", key=f"cancel_{reservation['id']}", icon=":material/cancel:"):
                _cancel_dialog(reservation)


def minhas_reservas(user):
    """Reimplementa a experiência Figma de 'Minhas solicitações'."""
    items = mock_data_service.reservations(requester_id=user["id"])
    header, action = st.columns([4, 1], vertical_alignment="center")
    with header:
        page_header("Minhas solicitações", "Acompanhe suas reservas e gerencie alterações.")
    with action:
        if st.button("Nova solicitação", icon=":material/add:", type="primary", width="stretch"):
            go("nova_reserva")
            st.rerun()

    _render_summary(items)
    filters = {
        "Todas": lambda item: True,
        "Pendentes": lambda item: item["status"] in _PENDING_STATUSES,
        "Aprovadas": lambda item: item["status"] == "aprovada",
        "Reprovadas": lambda item: item["status"] == "rejeitada",
        "Conflitos": lambda item: item["status"] == "conflito",
    }
    selected_tab = st.segmented_control("Filtrar solicitações", list(filters), default="Todas", label_visibility="collapsed")
    filtered = [item for item in items if filters[selected_tab](item)]
    if not filtered:
        with st.container(border=True):
            st.markdown("### :material/calendar_month: Nenhuma solicitação encontrada")
            st.caption("Não existem solicitações nessa categoria.")
            if st.button("Nova solicitação", key="empty_new_request", icon=":material/add:", type="primary"):
                go("nova_reserva")
                st.rerun()
        return
    for reservation in filtered:
        _render_card(reservation)

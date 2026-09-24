from datetime import date, datetime
from typing import Any, Dict, List, Optional

import streamlit as st

from controllers import mock_data_service
from controllers.app_state_service import go, set_toast
from views.components.ui_components import badge, page_header

_PENDING_STATUSES = {"pendente", "em_analise"}


def _render_styles() -> None:
    """Aplica estilos customizados para os cards de solicitação."""
    st.html(
        """
        <style>
        [class*="st-key-rf_request_card_"] div[data-testid="stVerticalBlockBorderWrapper"] {
            background: var(--surface-card);
            border-color: var(--stroke);
            border-radius: 10px;
        }
        </style>
        """
    )


def _date_label(value: str) -> str:
    """Formata datas no padrão brasileiro DD/MM/AAAA."""
    try:
        return datetime.fromisoformat(value).strftime("%d/%m/%Y")
    except (TypeError, ValueError):
        return value or "N/A"


def _resources_for(reservation: Dict[str, Any]) -> List[str]:
    """Recupera os recursos associados a uma reserva."""
    if reservation.get("resources"):
        return reservation["resources"]

    spaces = st.session_state.get("spaces", [])
    room = next(
        (space for space in spaces if space.get("name") == reservation.get("space")),
        None,
    )

    return room.get("resources", []) if room else []


def _remove_reservation(reservation_id: str) -> None:
    """Remove a reserva do estado da sessão."""
    if "reservations" in st.session_state:
        st.session_state.reservations = [
            item
            for item in st.session_state.reservations
            if item.get("id") != reservation_id
        ]
    set_toast("Reserva cancelada. O espaço foi liberado.")


def _update_reservation(
    reservation_id: str,
    room: Dict[str, Any],
    day: date,
    start: datetime.time,
    end: datetime.time,
) -> None:
    """Atualiza as informações de uma reserva e altera o status para análise."""
    reservations = st.session_state.get("reservations", [])
    for item in reservations:
        if item.get("id") == reservation_id:
            item.update(
                status="em_analise",
                space=room.get("name"),
                date=day.isoformat(),
                start=start.strftime("%H:%M"),
                end=end.strftime("%H:%M"),
            )
            break

    set_toast("Alteração enviada para análise.")


@st.dialog("Cancelar reserva")
def _cancel_dialog(reservation: Dict[str, Any]) -> None:
    """Modal de confirmação de cancelamento da reserva."""
    title = reservation.get("title") or reservation.get("type", "Reserva")
    space = reservation.get("space", "N/A")
    res_date = _date_label(reservation.get("date", ""))
    start = reservation.get("start", "")
    end = reservation.get("end", "")

    st.markdown(f"### {title}")
    st.caption(f"{space} · {res_date} · {start}–{end}")

    st.warning(
        "Deseja realmente cancelar? O espaço será liberado e os participantes poderão ser notificados.",
        icon=":material/warning:",
    )

    st.text_area(
        "Motivo do cancelamento (opcional)",
        placeholder="Ex.: A atividade foi remarcada.",
        key=f"cancel_reason_{reservation['id']}",
    )

    keep_col, cancel_col = st.columns(2)

    with keep_col:
        if st.button("Manter reserva", use_container_width=True):
            st.rerun()

    with cancel_col:
        if st.button(
            "Cancelar reserva",
            key=f"confirm_cancel_{reservation['id']}",
            type="primary",
            use_container_width=True,
        ):
            _remove_reservation(reservation["id"])
            st.rerun()


@st.dialog("Solicitar alteração", width="large")
def _alter_dialog(reservation: Dict[str, Any]) -> None:
    """Modal para edição e solicitação de mudança de data/hora/sala."""
    required_resources = _resources_for(reservation)

    st.info(
        "Escolha uma nova data, horário e sala. Serão exibidos somente espaços compatíveis com os recursos da atividade.",
        icon=":material/sync:",
    )

    with st.container(border=True):
        st.caption("SOLICITAÇÃO ATUAL")

        activity_col, room_col, participants_col = st.columns([2, 2, 1])

        with activity_col:
            st.markdown("**Atividade**")
            st.write(reservation.get("type", "N/A"))

        with room_col:
            st.markdown("**Sala atual**")
            st.write(reservation.get("space", "N/A"))

        with participants_col:
            st.markdown("**Participantes**")
            st.write(reservation.get("participants", "Não informado"))

    st.markdown("### Recursos definidos")

    if required_resources:
        badges_str = " · ".join(f":violet-badge[{res}]" for res in required_resources)
        st.markdown(badges_str)
    else:
        st.caption("Nenhum recurso específico foi informado para esta solicitação.")

    st.markdown("### Novo período")
    st.caption("Defina quando deseja realizar a atividade.")

    with st.form(f"alter_reservation_{reservation['id']}"):
        new_day, new_start, new_end = st.columns(3)

        curr_date = (
            date.fromisoformat(reservation["date"])
            if reservation.get("date")
            else date.today()
        )
        curr_start = (
            datetime.strptime(reservation["start"], "%H:%M").time()
            if reservation.get("start")
            else datetime.now().time()
        )
        curr_end = (
            datetime.strptime(reservation["end"], "%H:%M").time()
            if reservation.get("end")
            else datetime.now().time()
        )

        with new_day:
            selected_day = st.date_input("Nova data", value=curr_date)

        with new_start:
            selected_start = st.time_input("Horário de início", value=curr_start)

        with new_end:
            selected_end = st.time_input("Horário de término", value=curr_end)

        spaces = st.session_state.get("spaces", [])
        compatible_rooms = [
            space
            for space in spaces
            if space.get("status") != "bloqueado"
            and all(
                res in space.get("resources", []) for res in required_resources
            )
        ]

        st.markdown("### Salas disponíveis")
        st.caption(
            f"{len(compatible_rooms)} sala(s) compatível(is) com os recursos solicitados."
        )

        room_names = [space["name"] for space in compatible_rooms if "name" in space]

        selected_name = st.selectbox(
            "Escolha uma sala",
            options=room_names,
            index=None,
            placeholder="Selecione uma sala",
        )

        st.info(
            "Ao enviar a alteração, a solicitação será novamente analisada pelo gerente.",
            icon=":material/info:",
        )

        submitted = st.form_submit_button(
            "Enviar alteração",
            type="primary",
            use_container_width=True,
        )

    if submitted:
        if not selected_name:
            st.error("Selecione uma sala compatível antes de enviar a alteração.")
        elif selected_start >= selected_end:
            st.error("O horário de término deve ser posterior ao horário de início.")
        else:
            selected_room = next(
                space for space in compatible_rooms if space["name"] == selected_name
            )

            _update_reservation(
                reservation["id"],
                selected_room,
                selected_day,
                selected_start,
                selected_end,
            )
            st.rerun()


def _render_summary(items: List[Dict[str, Any]]) -> None:
    """Exibe os cards de métricas/resumo das solicitações."""
    total = len(items)
    pending = sum(1 for item in items if item.get("status") in _PENDING_STATUSES)
    approved = sum(1 for item in items if item.get("status") == "aprovada")
    rejected = sum(1 for item in items if item.get("status") == "rejeitada")

    cols = st.columns(4)
    metrics = [
        ("Total", total),
        ("Pendentes", pending),
        ("Aprovadas", approved),
        ("Reprovadas", rejected),
    ]

    for col, (label, value) in zip(cols, metrics):
        with col:
            with st.container(border=True):
                st.metric(label=label, value=value)


def _render_card(reservation: Dict[str, Any]) -> None:
    """Renderiza um card individual de solicitação estilizado."""
    res_id = reservation.get("id", "unknown")

    with st.container(border=True, key=f"rf_request_card_{res_id}"):
        header_col, status_col = st.columns([5, 1], vertical_alignment="top")

        with header_col:
            st.subheader(reservation.get("title", "Sem título"))

            space_name = reservation.get("space", "N/A")
            date_str = _date_label(reservation.get("date", ""))
            start_time = reservation.get("start", "")
            end_time = reservation.get("end", "")

            st.caption(
                f":material/meeting_room: {space_name}  ·  "
                f":material/calendar_today: {date_str}  ·  "
                f":material/schedule: {start_time}–{end_time}"
            )

            if reservation.get("participants"):
                st.caption(
                    f":material/groups: {reservation['participants']} participantes"
                )

        with status_col:
            st.html(badge(reservation.get("status", "pendente")))

        # Exibição de Justificativa (se existir)
        justification = reservation.get("justification")
        if justification:
            with st.container(border=True):
                st.caption("**Justificativa**")
                st.write(justification)

        st.divider()

        # Ações do Card
        _, action_col1, action_col2 = st.columns([2, 1, 1])

        with action_col1:
            if st.button(
                "Solicitar alteração",
                key=f"alter_{res_id}",
                icon=":material/edit_calendar:",
                use_container_width=True,
            ):
                _alter_dialog(reservation)

        with action_col2:
            if st.button(
                "Cancelar",
                key=f"cancel_{res_id}",
                icon=":material/cancel:",
                type="primary",
                use_container_width=True,
            ):
                _cancel_dialog(reservation)


def minhas_reservas(user: Dict[str, Any]) -> None:
    """Página de acompanhamento de solicitações do solicitante."""
    _render_styles()

    items = mock_data_service.reservations(requester_id=user["id"])

    # Cabeçalho da Página
    header_col, action_col = st.columns([4, 1], vertical_alignment="center")

    with header_col:
        page_header(
            "Minhas solicitações",
            "Acompanhe suas reservas e gerencie alterações.",
        )

    with action_col:
        if st.button(
            "Nova solicitação",
            icon=":material/add:",
            type="primary",
            use_container_width=True,
        ):
            go("nova_reserva")
            st.rerun()

    # Resumo / Métricas
    _render_summary(items)

    # Filtros
    filters = {
        "Todas": lambda item: True,
        "Pendentes": lambda item: item.get("status") in _PENDING_STATUSES,
        "Aprovadas": lambda item: item.get("status") == "aprovada",
        "Reprovadas": lambda item: item.get("status") == "rejeitada",
        "Conflitos": lambda item: item.get("status") == "conflito",
    }

    selected_tab = st.segmented_control(
        "Filtrar solicitações",
        options=list(filters.keys()),
        default="Todas",
        label_visibility="collapsed",
    )

    filtered = [item for item in items if filters[selected_tab](item)]

    # Estado Vazio
    if not filtered:
        with st.container(border=True):
            st.markdown("### :material/calendar_month: Nenhuma solicitação encontrada")
            st.caption("Não existem solicitações nessa categoria.")

            if st.button(
                "Nova solicitação",
                key="empty_new_request",
                icon=":material/add:",
                type="primary",
            ):
                go("nova_reserva")
                st.rerun()
        return

    # Lista de Cards
    for reservation in filtered:
        _render_card(reservation)
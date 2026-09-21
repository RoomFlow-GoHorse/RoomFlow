from datetime import date, datetime

import streamlit as st

from controllers import mock_data_service
from controllers.app_state_service import go, set_toast
from views.components.ui_components import badge, page_header


_PENDING_STATUSES = {"pendente", "em_analise"}


def _render_styles():
    """Aplica estilos somente aos cards de solicitações."""
    st.html(
        """
        <style>
        [class*="st-key-rf_request_card_"]
        div[data-testid="stVerticalBlockBorderWrapper"] {
            background: #FFFFFF;
            border-color: #E4E1DB;
            border-radius: 10px;
        }
        </style>
        """
    )


def _date_label(value: str) -> str:
    try:
        return datetime.fromisoformat(value).strftime("%d/%m/%Y")
    except (TypeError, ValueError):
        return value


def _resources_for(reservation: dict) -> list[str]:
    if reservation.get("resources"):
        return reservation["resources"]

    room = next(
        (
            space
            for space in st.session_state.spaces
            if space["name"] == reservation["space"]
        ),
        None,
    )

    return room.get("resources", []) if room else []


def _remove_reservation(reservation_id: str):
    st.session_state.reservations = [
        item
        for item in st.session_state.reservations
        if item["id"] != reservation_id
    ]

    set_toast(
        "Reserva cancelada. O espaço foi liberado."
    )


def _update_reservation(
    reservation_id: str,
    room: dict,
    day: date,
    start,
    end,
):
    for item in st.session_state.reservations:
        if item["id"] == reservation_id:
            item.update(
                status="em_analise",
                space=room["name"],
                date=day.isoformat(),
                start=start.strftime("%H:%M"),
                end=end.strftime("%H:%M"),
            )
            break

    set_toast(
        "Alteração enviada para análise."
    )


@st.dialog("Cancelar reserva")
def _cancel_dialog(reservation: dict):
    st.markdown(
        f"### {reservation['type']}"
    )

    st.caption(
        f"{reservation['space']} · "
        f"{_date_label(reservation['date'])} · "
        f"{reservation['start']}–{reservation['end']}"
    )

    st.warning(
        "Deseja realmente cancelar? "
        "O espaço será liberado e os participantes "
        "poderão ser notificados.",
        icon=":material/warning:",
    )

    st.text_area(
        "Motivo do cancelamento (opcional)",
        placeholder="Ex.: A atividade foi remarcada.",
    )

    keep, cancel = st.columns(2)

    with keep:
        if st.button(
            "Manter reserva",
            width="stretch",
        ):
            st.rerun()

    with cancel:
        if st.button(
            "Cancelar reserva",
            key=f"confirm_cancel_{reservation['id']}",
            type="primary",
            width="stretch",
        ):
            _remove_reservation(
                reservation["id"]
            )
            st.rerun()


@st.dialog("Solicitar alteração", width="large")
def _alter_dialog(reservation: dict):
    required_resources = _resources_for(
        reservation
    )

    st.info(
        "Escolha uma nova data, horário e sala. "
        "Serão exibidos somente espaços compatíveis "
        "com os recursos da atividade.",
        icon=":material/sync:",
    )

    with st.container(
        border=True,
    ):
        st.caption("SOLICITAÇÃO ATUAL")

        activity, room, participants = st.columns(
            [2, 2, 1]
        )

        with activity:
            st.markdown("**Atividade**")
            st.write(reservation["type"])

        with room:
            st.markdown("**Sala atual**")
            st.write(reservation["space"])

        with participants:
            st.markdown("**Participantes**")
            st.write(
                reservation.get(
                    "participants",
                    "Não informado",
                )
            )

    st.markdown("### Recursos definidos")

    if required_resources:
        st.markdown(
            " · ".join(
                f":violet-badge[{resource}]"
                for resource in required_resources
            )
        )
    else:
        st.caption(
            "Nenhum recurso específico foi informado "
            "para esta solicitação."
        )

    st.markdown("### Novo período")

    st.caption(
        "Defina quando deseja realizar a atividade."
    )

    with st.form(
        f"alter_reservation_{reservation['id']}"
    ):
        new_day, new_start, new_end = st.columns(3)

        with new_day:
            selected_day = st.date_input(
                "Nova data",
                value=date.fromisoformat(
                    reservation["date"]
                ),
            )

        with new_start:
            selected_start = st.time_input(
                "Horário de início",
                value=datetime.strptime(
                    reservation["start"],
                    "%H:%M",
                ).time(),
            )

        with new_end:
            selected_end = st.time_input(
                "Horário de término",
                value=datetime.strptime(
                    reservation["end"],
                    "%H:%M",
                ).time(),
            )

        compatible_rooms = [
            space
            for space in st.session_state.spaces
            if space["status"] != "bloqueado"
            and all(
                resource in space.get(
                    "resources",
                    [],
                )
                for resource in required_resources
            )
        ]

        st.markdown("### Salas disponíveis")

        st.caption(
            f"{len(compatible_rooms)} sala(s) "
            "compatível(is) com os recursos solicitados."
        )

        room_names = [
            space["name"]
            for space in compatible_rooms
        ]

        selected_name = st.selectbox(
            "Escolha uma sala",
            room_names,
            index=None,
            placeholder="Selecione uma sala",
        )

        st.info(
            "Ao enviar a alteração, a solicitação "
            "será novamente analisada pelo gerente.",
            icon=":material/info:",
        )

        submitted = st.form_submit_button(
            "Enviar alteração",
            type="primary",
            width="stretch",
        )

    if submitted:
        if not selected_name:
            st.error(
                "Selecione uma sala compatível "
                "antes de enviar a alteração."
            )

        elif selected_start >= selected_end:
            st.error(
                "O horário de término deve ser posterior "
                "ao horário de início."
            )

        else:
            selected_room = next(
                space
                for space in compatible_rooms
                if space["name"] == selected_name
            )

            _update_reservation(
                reservation["id"],
                selected_room,
                selected_day,
                selected_start,
                selected_end,
            )

            st.rerun()


def _render_summary(items: list[dict]):
    """Exibe os indicadores resumidos das solicitações."""

    counts = (
        (
            "Total",
            len(items),
        ),
        (
            "Pendentes",
            sum(
                item["status"] in _PENDING_STATUSES
                for item in items
            ),
        ),
        (
            "Aprovadas",
            sum(
                item["status"] == "aprovada"
                for item in items
            ),
        ),
        (
            "Reprovadas",
            sum(
                item["status"] == "rejeitada"
                for item in items
            ),
        ),
    )

    columns = st.columns(4)

    for column, (label, count) in zip(
        columns,
        counts,
    ):
        with column:
            with st.container(
                border=True,
            ):
                st.caption(label)

                st.markdown(
                    f"<div style='"
                    f"font-size:28px;"
                    f"font-weight:700;"
                    f"color:#27272a;"
                    f"margin-top:2px;"
                    f"'>"
                    f"{count}"
                    f"</div>",
                    unsafe_allow_html=True,
                )


def _render_card(reservation: dict):
    """Renderiza um card individual de solicitação."""

    with st.container(
        border=True,
        key=f"rf_request_card_{reservation['id']}",
    ):
        # -----------------------------------------------------
        # CABEÇALHO
        # -----------------------------------------------------

        content, status = st.columns(
            [5, 1],
            vertical_alignment="top",
        )

        with content:
            st.markdown(
                f"<div style='"
                f"font-size:17px;"
                f"font-weight:650;"
                f"color:#27272a;"
                f"margin-bottom:6px;"
                f"'>"
                f"{reservation['title']}"
                f"</div>",
                unsafe_allow_html=True,
            )

            st.caption(
                f":material/meeting_room: "
                f"{reservation['space']}  ·  "
                f":material/calendar_today: "
                f"{_date_label(reservation['date'])}  ·  "
                f":material/schedule: "
                f"{reservation['start']}–"
                f"{reservation['end']}"
            )

            if reservation.get("participants"):
                st.caption(
                    f":material/groups: "
                    f"{reservation['participants']} "
                    f"participantes"
                )

        with status:
            st.html(
                badge(
                    reservation["status"]
                )
            )

        # -----------------------------------------------------
        # JUSTIFICATIVA
        # -----------------------------------------------------

        if reservation.get("justification"):
            st.markdown(
                "<div style='"
                "margin-top:14px;"
                "padding:12px 14px;"
                "border-radius:10px;"
                "background:#F5F3FF;"
                "border:1px solid #EDE9FE;"
                "'>"
                "<div style='"
                "font-size:11px;"
                "font-weight:600;"
                "color:#52525B;"
                "margin-bottom:4px;"
                "'>"
                "Justificativa"
                "</div>"
                f"<div style='"
                "font-size:14px;"
                "line-height:1.5;"
                "color:#3F3F46;"
                "'>"
                f"{reservation['justification']}"
                "</div>"
                "</div>",
                unsafe_allow_html=True,
            )

        # -----------------------------------------------------
        # AÇÕES
        # -----------------------------------------------------

        st.markdown(
            "<div style='margin-top:16px;'>"
            "</div>",
            unsafe_allow_html=True,
        )

        with st.container(
            horizontal=True,
            horizontal_alignment="right",
        ):
            if st.button(
                "Solicitar alteração",
                key=f"alter_{reservation['id']}",
                icon=":material/edit_calendar:",
            ):
                _alter_dialog(
                    reservation
                )

            if st.button(
                "Cancelar",
                key=f"cancel_{reservation['id']}",
                icon=":material/cancel:",
                type="primary",
            ):
                _cancel_dialog(
                    reservation
                )


def minhas_reservas(user):
    """Página de acompanhamento das solicitações do solicitante."""

    _render_styles()

    items = mock_data_service.reservations(
        requester_id=user["id"]
    )

    # ---------------------------------------------------------
    # CABEÇALHO
    # ---------------------------------------------------------

    header, action = st.columns(
        [4, 1],
        vertical_alignment="center",
    )

    with header:
        page_header(
            "Minhas solicitações",
            "Acompanhe suas reservas e gerencie alterações.",
        )

    with action:
        if st.button(
            "Nova solicitação",
            icon=":material/add:",
            type="primary",
            width="stretch",
        ):
            go("nova_reserva")
            st.rerun()

    # ---------------------------------------------------------
    # RESUMO
    # ---------------------------------------------------------

    _render_summary(items)

    # ---------------------------------------------------------
    # FILTROS
    # ---------------------------------------------------------

    filters = {
        "Todas": lambda item: True,
        "Pendentes": lambda item: (
            item["status"] in _PENDING_STATUSES
        ),
        "Aprovadas": lambda item: (
            item["status"] == "aprovada"
        ),
        "Reprovadas": lambda item: (
            item["status"] == "rejeitada"
        ),
        "Conflitos": lambda item: (
            item["status"] == "conflito"
        ),
    }

    selected_tab = st.segmented_control(
        "Filtrar solicitações",
        list(filters),
        default="Todas",
        label_visibility="collapsed",
    )

    filtered = [
        item
        for item in items
        if filters[selected_tab](item)
    ]

    # ---------------------------------------------------------
    # ESTADO VAZIO
    # ---------------------------------------------------------

    if not filtered:
        with st.container(
            border=True,
        ):
            st.markdown(
                "### :material/calendar_month: "
                "Nenhuma solicitação encontrada"
            )

            st.caption(
                "Não existem solicitações nessa categoria."
            )

            if st.button(
                "Nova solicitação",
                key="empty_new_request",
                icon=":material/add:",
                type="primary",
            ):
                go("nova_reserva")
                st.rerun()

        return

    # ---------------------------------------------------------
    # CARDS
    # ---------------------------------------------------------

    for reservation in filtered:
        _render_card(reservation)

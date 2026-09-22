import streamlit as st

from controllers import mock_data_service
from controllers.app_state_service import set_toast
from views.components.ui_components import badge, page_header


def _reservations_for(conflict):
    """Retorna todas as reservas envolvidas no conflito."""
    identifiers = conflict.get("affected_reservations")

    if not identifiers:
        identifiers = [
            conflict.get("reservation_a"),
            conflict.get("reservation_b"),
        ]

    identifiers = [identifier for identifier in identifiers if identifier]

    by_id = {
        reservation["id"]: reservation
        for reservation in st.session_state.reservations
    }

    return [
        by_id[identifier]
        for identifier in identifiers
        if identifier in by_id
    ]


def _conflict_schedule(conflict, reservations):
    if reservations:
        first = reservations[0]
        return f"{first['date']} · {first['start']}–{first['end']}"

    return conflict.get("reason", "Horário não disponível")


@st.dialog("Resolver conflito", width="medium")
def resolve_conflict_dialog(conflict, reservations):
    st.caption(
        f"{conflict['space']} · "
        f"{_conflict_schedule(conflict, reservations)}"
    )

    if reservations:
        st.markdown("**Reservas envolvidas**")

        for start in range(0, len(reservations), 2):
            row_reservations = reservations[start:start + 2]
            reservation_columns = st.columns(len(row_reservations))

            for offset, reservation in enumerate(row_reservations):
                index = start + offset
                with reservation_columns[offset]:
                    with st.container(border=True):
                        st.caption(f"Reserva {chr(65 + index)}")
                        st.markdown(f"**{reservation['requester']}**")
                        st.caption(f"{reservation['title']} · {reservation['type']}")
                        st.caption(f"{reservation.get('participants', 0)} pessoas")
                        st.caption(
                            f"Justificativa: "
                            f"{reservation.get('justification') or 'Sem justificativa informada.'}"
                        )

    else:
        st.info(
            "As reservas originais não estão disponíveis "
            "no ambiente atual."
        )

    outcomes = {}

    if reservations:
        reservation_a = reservations[0]["requester"]

        outcomes[
            f"Manter reserva A ({reservation_a})"
        ] = "manteve_a"

    if len(reservations) > 1:
        reservation_b = reservations[1]["requester"]

        outcomes[
            f"Manter reserva B ({reservation_b})"
        ] = "manteve_b"

    outcomes["Sugerir espaço alternativo"] = "alterou"

    with st.form(key=f"resolve_conflict_form_{conflict['id']}"):
        selected_label = st.selectbox(
            "Resultado",
            list(outcomes),
            key=f"conflict_outcome_{conflict['id']}",
        )

        justification = st.text_area(
            "Decisão / justificativa *",
            placeholder=(
                "Descreva a decisão tomada e o motivo..."
            ),
            key=f"conflict_justification_{conflict['id']}",
        )

        cancel_column, resolve_column = st.columns(2)

        with cancel_column:
            cancelled = st.form_submit_button(
                "Cancelar",
                width="stretch",
            )

        with resolve_column:
            resolved = st.form_submit_button(
                "Marcar como resolvido",
                type="primary",
                icon=":material/check:",
                width="stretch",
            )

    if cancelled:
        st.rerun()

    if resolved:
        if not justification.strip():
            st.error("Descreva a decisão tomada.")
            return

        mock_data_service.resolve_conflict(
            conflict["id"],
            justification.strip(),
            outcome=outcomes[selected_label],
        )

        set_toast("Conflito resolvido.")
        st.rerun()


def _reservation_card(reservation, label):
    with st.container(border=True):
        st.caption(label)

        st.markdown(
            f"**{reservation['requester']}**"
        )

        st.caption(
            f"{reservation['title']} · "
            f"{reservation['type']} · "
            f"{reservation.get('participants', 0)} pessoas"
        )

        st.caption(
            f"Justificativa: "
            f"{reservation.get('justification') or 'Sem justificativa informada.'}"
        )


def conflicts(user):
    all_conflicts = st.session_state.conflicts

    page_header(
        "Conflitos",
        "Resolva conflitos de reservas e bloqueios de espaços.",
    )

    if not all_conflicts:
        st.info("Nenhum conflito registrado.")
        return

    status_filter = st.selectbox(
        "Filtrar por status",
        ["Todos", "Em aberto", "Em análise", "Resolvidos"],
        key="conflict_status_filter",
    )
    statuses_by_filter = {
        "Todos": {"nao_resolvido", "em_analise", "resolvido"},
        "Em aberto": {"nao_resolvido"},
        "Em análise": {"em_analise"},
        "Resolvidos": {"resolvido"},
    }
    filtered_conflicts = [
        conflict
        for conflict in all_conflicts
        if conflict["status"] in statuses_by_filter[status_filter]
    ]

    if not filtered_conflicts:
        st.info("Nenhum conflito encontrado para este filtro.")
        return

    for conflict in filtered_conflicts:
        reservations = _reservations_for(conflict)

        with st.container(border=True):
            # Cabeçalho
            identifier_column, status_column, detected_column = st.columns(
                [2, 2, 3],
                vertical_alignment="center",
            )

            with identifier_column:
                st.caption(
                    f"CONFLITO · {conflict['id'].upper()}"
                )

            with status_column:
                st.html(
                    badge(conflict["status"])
                )

            with detected_column:
                st.caption(
                    f"Detectado: "
                    f"{conflict.get('detected_at', 'agora')}"
                )

            # Sala e horário
            st.markdown(
                f"**{conflict['space']}**"
            )

            st.caption(
                _conflict_schedule(
                    conflict,
                    reservations,
                )
            )

            # Reservas envolvidas
            if reservations:
                st.markdown("**Reservas envolvidas**")

                # Duas por linha.
                # Se houver 3, 4, 5..., continua criando novas linhas.
                for start in range(0, len(reservations), 2):
                    row_reservations = reservations[start:start + 2]

                    reservation_columns = st.columns(
                        len(row_reservations)
                    )

                    for offset, reservation in enumerate(
                        row_reservations
                    ):
                        index = start + offset

                        with reservation_columns[offset]:
                            _reservation_card(
                                reservation,
                                f"Reserva {chr(65 + index)}",
                            )

            else:
                st.info(
                    "As reservas envolvidas não estão "
                    "disponíveis no ambiente atual."
                )

            # Decisão já tomada
            if conflict.get("decision"):
                st.success(
                    f"Decisão: {conflict['decision']}"
                )

            # Ação
            if (
                conflict["status"] != "resolvido"
                and st.button(
                    "Resolver conflito",
                    key=f"resolve_conflict_{conflict['id']}",
                    type="primary",
                    icon=":material/check:",
                )
            ):
                resolve_conflict_dialog(
                    conflict,
                    reservations,
                )

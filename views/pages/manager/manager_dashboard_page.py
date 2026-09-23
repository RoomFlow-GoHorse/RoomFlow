import streamlit as st

from controllers import mock_data_service
from controllers.app_state_service import go
from views.components.ui_components import badge, page_header


def _stat_card(label, value, tone="default"):
    """Renderiza um card de indicador."""

    colors = {
        "default": "#231F20",
        "success": "#15803D",
        "warning": "#B45309",
        "danger": "#B91C1C",
    }

    value_color = colors.get(
        tone,
        colors["default"],
    )

    card_key = (
        f"manager_stat_{label.lower().replace(' ', '_')}"
    )

    st.markdown(
        f"""
        <style>
            .st-key-{card_key} {{
                background: var(--surface-card);
                border: 1px solid var(--stroke);
                border-radius: 14px;
                padding: 18px;
                min-height: 128px;
            }}

            .st-key-{card_key} [data-testid="stMetricLabel"] {{
                color: var(--graphite-muted);
                font-size: 11px;
                font-weight: 600;
                letter-spacing: 0.06em;
                text-transform: uppercase;
            }}

            .st-key-{card_key} [data-testid="stMetricValue"] {{
                color: {value_color};
                font-size: 28px;
                font-weight: 650;
            }}

            .st-key-{card_key} [data-testid="stMetricDelta"] {{
                display: none;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.container(
        key=card_key,
        border=True,
    ):
        st.metric(
            label=label,
            value=value,
        )


def _quick_action(icon, title, description, key, target):
    """Renderiza uma ação rápida."""

    with st.container(border=True):
        columns = st.columns(
            [0.8, 4.2, 0.5],
            vertical_alignment="center",
        )

        with columns[0]:
            st.write(icon)

        with columns[1]:
            st.write(f"**{title}**")
            st.caption(description)

        with columns[2]:
            if st.button(
                "",
                key=key,
                icon=":material/arrow_forward:",
                help=f"Acessar {title.lower()}",
            ):
                go(target)


def _reservation_row(reservation, key):
    """Renderiza uma solicitação de reserva."""

    with st.container(border=True):
        columns = st.columns(
            [0.7, 3.4, 1.5, 1.1],
            vertical_alignment="center",
        )

        with columns[0]:
            st.write(":material/meeting_room:")

        with columns[1]:
            title = reservation.get(
                "title",
                "Reserva",
            )

            space = reservation.get(
                "space",
                "Espaço não informado",
            )

            st.write(f"**{title}**")
            st.caption(space)

        with columns[2]:
            date = reservation.get("date", "")
            start = reservation.get("start", "")
            end = reservation.get("end", "")

            st.caption(f"**{date}**")
            st.caption(f"{start} – {end}")

        with columns[3]:
            st.html(
                badge(
                    reservation.get("status", "")
                )
            )


def _space_row(space):
    """Renderiza uma linha de status de espaço."""

    with st.container():
        columns = st.columns(
            [3.5, 1.3],
            vertical_alignment="center",
        )

        with columns[0]:
            name = space.get(
                "name",
                "Espaço",
            )

            location = space.get(
                "location",
                "",
            )

            st.write(f"**{name}**")

            if location:
                st.caption(location)

        with columns[1]:
            st.html(
                badge(
                    space.get("status", "")
                )
            )


def _occupancy_bar(label, count, total):
    """Renderiza uma barra de ocupação."""

    percentage = (
        count / total
        if total
        else 0
    )

    columns = st.columns(
        [1.1, 3.8, 0.4],
        vertical_alignment="center",
    )

    with columns[0]:
        st.caption(label)

    with columns[1]:
        st.progress(
            percentage,
            text=None,
        )

    with columns[2]:
        st.write(f"**{count}**")


def dashboard(user):
    reservations = mock_data_service.reservations()
    spaces = mock_data_service.spaces()
    conflicts = st.session_state.get(
        "conflicts",
        [],
    )

    pending_reservations = [
        item
        for item in reservations
        if item.get("status")
        in {"pendente", "em_analise"}
    ]

    approved_reservations = [
        item
        for item in reservations
        if item.get("status") == "aprovada"
    ]

    available_spaces = [
        item
        for item in spaces
        if item.get("status") == "disponivel"
    ]

    occupied_spaces = [
        item
        for item in spaces
        if item.get("status") == "ocupado"
    ]

    blocked_spaces = [
        item
        for item in spaces
        if item.get("status") == "bloqueado"
    ]

    open_conflicts = [
        item
        for item in conflicts
        if item.get("status")
        in {"nao_resolvido", "em_analise"}
    ]

    page_header(
        "Painel operacional",
        "Visão geral das reservas, espaços e conflitos do dia.",
    )

    # ------------------------------------------------------------------
    # Indicadores principais
    # ------------------------------------------------------------------

    metric_columns = st.columns(4)

    with metric_columns[0]:
        _stat_card(
            "Pendentes",
            len(pending_reservations),
            "warning",
        )

    with metric_columns[1]:
        _stat_card(
            "Aprovadas",
            len(approved_reservations),
            "success",
        )

    with metric_columns[2]:
        _stat_card(
            "Salas livres",
            len(available_spaces),
            "default",
        )

    with metric_columns[3]:
        _stat_card(
            "Conflitos abertos",
            len(open_conflicts),
            "danger",
        )

    st.write("")

    # ------------------------------------------------------------------
    # Acesso rápido + solicitações
    # ------------------------------------------------------------------

    main_columns = st.columns(
        [1, 2],
        gap="large",
    )

    with main_columns[0]:
        st.subheader("Acesso rápido")

        _quick_action(
            ":material/meeting_room:",
            "Reservas",
            "Analisar e decidir sobre solicitações",
            "manager_dashboard_reservas",
            "reservas",
        )

        _quick_action(
            ":material/home_work:",
            "Espaços",
            "Gerenciar capacidade e recursos das salas",
            "manager_dashboard_espacos",
            "espacos",
        )

        _quick_action(
            ":material/warning:",
            "Conflitos",
            "Resolver conflitos de reservas e horários",
            "manager_dashboard_conflitos",
            "conflitos",
        )

    with main_columns[1]:
        with st.container(border=True):
            header_columns = st.columns(
                [1, 0.25],
                vertical_alignment="center",
            )

            with header_columns[0]:
                st.subheader(
                    "Solicitações pendentes"
                )

                if pending_reservations:
                    st.caption(
                        f"{len(pending_reservations)} "
                        "solicitação(ões) aguardando análise."
                    )

            with header_columns[1]:
                if st.button(
                    "Ver todas",
                    key="manager_dashboard_ver_reservas",
                    icon=":material/arrow_forward:",
                ):
                    go("reservas")

            if not pending_reservations:
                st.info(
                    "Nenhuma solicitação pendente."
                )
            else:
                for index, reservation in enumerate(
                    pending_reservations[:4]
                ):
                    _reservation_row(
                        reservation,
                        f"pending_reservation_{index}",
                    )

    st.write("")

    # ------------------------------------------------------------------
    # Status dos espaços + ocupação
    # ------------------------------------------------------------------

    bottom_columns = st.columns(
        2,
        gap="large",
    )

    with bottom_columns[0]:
        with st.container(border=True):
            header_columns = st.columns(
                [1, 0.25],
                vertical_alignment="center",
            )

            with header_columns[0]:
                st.subheader(
                    "Status dos espaços"
                )

            with header_columns[1]:
                if st.button(
                    "Gerenciar",
                    key="manager_dashboard_gerenciar_espacos",
                    icon=":material/arrow_forward:",
                ):
                    go("espacos")

            if not spaces:
                st.caption(
                    "Nenhum espaço cadastrado."
                )
            else:
                for space in spaces[:5]:
                    _space_row(space)

    with bottom_columns[1]:
        with st.container(border=True):
            header_columns = st.columns(
                [1, 0.25],
                vertical_alignment="center",
            )

            with header_columns[0]:
                st.subheader(
                    "Ocupação dos espaços"
                )

            with header_columns[1]:
                if st.button(
                    "Ver mais",
                    key="manager_dashboard_ver_ocupacao",
                    icon=":material/arrow_forward:",
                ):
                    go("ocupacao")

            total_spaces = len(spaces)

            _occupancy_bar(
                "Disponíveis",
                len(available_spaces),
                total_spaces,
            )

            _occupancy_bar(
                "Ocupadas",
                len(occupied_spaces),
                total_spaces,
            )

            _occupancy_bar(
                "Bloqueadas",
                len(blocked_spaces),
                total_spaces,
            )

            occupancy_rate = (
                round(
                    (
                        len(occupied_spaces)
                        / total_spaces
                    )
                    * 100
                )
                if total_spaces
                else 0
            )

            st.divider()

            st.caption(
                f"Taxa de ocupação atual: "
                f"**{occupancy_rate}%**"
            )
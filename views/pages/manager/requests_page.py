import streamlit as st

from controllers import mock_data_service
from controllers.app_state_service import go, set_toast
from views.components.reservation_cards import reservation_cards
from views.components.ui_components import badge, page_header


STATUS_OPTIONS = [
    ("Todos os status", "Todas"),
    ("Pendente", "pendente"),
    ("Em análise", "em_analise"),
    ("Aprovada", "aprovada"),
    ("Rejeitada", "rejeitada"),
    ("Conflito", "conflito"),
]

ACTION_STATUSES = {"pendente", "em_analise"}


# ============================================================
# ESTILO DA TABELA
# ============================================================

def _load_reservations_table_style():
    st.markdown(
        """
        <style>
            /* Área geral da tabela */
            .st-key-manager_reservations_table {
                border: 1px solid var(--stroke);
                border-radius: 12px;
                overflow: hidden;
                background: var(--surface-card);
            }

            /* Cabeçalho */
            .st-key-manager_reservation_header {
                background: var(--surface-alt);
                border-bottom: 1px solid var(--stroke);
                min-height: 42px;
            }

            .st-key-manager_reservation_header [data-testid="stMarkdownContainer"] p {
                color: var(--graphite-muted);
                font-size: 11px;
                font-weight: 600;
                letter-spacing: 0.04em;
                margin: 0;
            }

            /* Linhas */
            [class*="manager_reservation_row_"] {
                min-height: 68px;
                border-bottom: 1px solid var(--stroke);
                background: var(--surface-card);
                transition: background-color 0.15s ease;
            }

            [class*="manager_reservation_row_"]:hover {
                background: var(--surface-alt);
            }

            [class*="manager_reservation_row_"]:last-child {
                border-bottom: none;
            }

            /* Textos principais */
            [class*="manager_reservation_row_"] [data-testid="stMarkdownContainer"] p {
                margin: 0;
            }

            /* Nome do solicitante */
            .reservation-requester {
                color: var(--graphite);
                font-size: 13px;
                font-weight: 600;
                line-height: 1.35;
            }

            /* Textos secundários */
            .reservation-secondary {
                color: var(--graphite-muted);
                font-size: 12px;
                line-height: 1.4;
            }

            .reservation-date {
                color: var(--graphite-soft);
                font-size: 12px;
                line-height: 1.4;
            }

            /* Botão Ver */
            [class*="manager_reservation_row_"] [data-testid="stButton"] button {
                height: 32px;
                min-height: 32px;
                padding: 0 13px;
                border: 1px solid var(--stroke-strong);
                border-radius: 7px;
                background: var(--surface-card);
                color: var(--graphite-soft);
                font-size: 12px;
                font-weight: 600;
                box-shadow: none;
            }

            [class*="manager_reservation_row_"] [data-testid="stButton"] button:hover {
                border-color: var(--brand);
                color: var(--brand);
                background: var(--brand-lighter);
            }

            /* Espaçamento interno das células */
            .reservation-cell {
                padding-top: 4px;
            }

            /* Estado vazio */
            .reservation-empty {
                padding: 42px 20px;
                text-align: center;
                color: var(--graphite-muted);
                font-size: 13px;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# HELPERS
# ============================================================

def _parse_date(value):
    from datetime import date

    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        try:
            day, month, year = value.split("/")
            return date(int(year), int(month), int(day))
        except (TypeError, ValueError):
            return date.today()


def _parse_time(value):
    from datetime import time

    try:
        hour, minute = value.split(":")[:2]
        return time(int(hour), int(minute))
    except (TypeError, ValueError):
        return time(8, 0)


def _reservation_matches_search(item, search):
    if not search:
        return True

    search = search.lower().strip()

    requester = item.get("requester", "").lower()
    space = item.get("space", "").lower()

    return search in requester or search in space


def _can_act(status):
    return status in ACTION_STATUSES


# ============================================================
# DETALHES
# ============================================================

@st.dialog("Detalhes da reserva", width="medium")
def reservation_details_dialog(reservation):
    st.subheader(reservation["title"])

    st.html(
        f"""
        <div style="
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 18px 28px;
            margin: 18px 0;
        ">
            <div>
                <div style="
                    color: #73706A;
                    font-size: 11px;
                    margin-bottom: 4px;
                ">SOLICITANTE</div>
                <div style="
                    color: #231F20;
                    font-size: 14px;
                    font-weight: 600;
                ">{reservation["requester"]}</div>
            </div>

            <div>
                <div style="
                    color: #73706A;
                    font-size: 11px;
                    margin-bottom: 4px;
                ">ESPAÇO</div>
                <div style="
                    color: #231F20;
                    font-size: 14px;
                    font-weight: 600;
                ">{reservation["space"]}</div>
            </div>

            <div>
                <div style="
                    color: #73706A;
                    font-size: 11px;
                    margin-bottom: 4px;
                ">TIPO</div>
                <div style="
                    color: #231F20;
                    font-size: 14px;
                    font-weight: 600;
                ">{reservation["type"]}</div>
            </div>

            <div>
                <div style="
                    color: #73706A;
                    font-size: 11px;
                    margin-bottom: 4px;
                ">PARTICIPANTES</div>
                <div style="
                    color: #231F20;
                    font-size: 14px;
                    font-weight: 600;
                ">{reservation.get("participants", 0)}</div>
            </div>

            <div>
                <div style="
                    color: #73706A;
                    font-size: 11px;
                    margin-bottom: 4px;
                ">DATA</div>
                <div style="
                    color: #231F20;
                    font-size: 14px;
                    font-weight: 600;
                ">{reservation["date"]}</div>
            </div>

            <div>
                <div style="
                    color: #73706A;
                    font-size: 11px;
                    margin-bottom: 4px;
                ">HORÁRIO</div>
                <div style="
                    color: #231F20;
                    font-size: 14px;
                    font-weight: 600;
                ">{reservation["start"]} – {reservation["end"]}</div>
            </div>
        </div>
        """
    )

    st.caption("JUSTIFICATIVA")

    st.markdown(
        f"""
        <div style="
            background: #F8F7F4;
            border: 1px solid #E7E5E0;
            border-radius: 8px;
            padding: 12px;
            color: #4A4742;
            font-size: 13px;
            line-height: 1.5;
            margin-bottom: 18px;
        ">
            {reservation.get(
                "justification",
                "Sem justificativa informada."
            )}
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.html(badge(reservation["status"]))

    st.divider()

    can_act = _can_act(reservation["status"])

    if can_act:
        edit_column, reject_column, approve_column = st.columns(
            3,
            gap="small",
        )

        with edit_column:
            if st.button(
                "Editar",
                key=f"details_edit_{reservation['id']}",
                use_container_width=True,
                icon=":material/edit:",
            ):
                st.session_state["edit_reservation_id"] = reservation["id"]
                st.session_state["detail_reservation_id"] = None
                st.rerun()

        with reject_column:
            if st.button(
                "Rejeitar",
                key=f"details_reject_{reservation['id']}",
                use_container_width=True,
                icon=":material/close:",
            ):
                st.session_state["reject_reservation_id"] = reservation["id"]
                st.session_state["detail_reservation_id"] = None
                st.rerun()

        with approve_column:
            if st.button(
                "Aprovar",
                key=f"details_approve_{reservation['id']}",
                type="primary",
                use_container_width=True,
                icon=":material/check:",
            ):
                mock_data_service.update_reservation_status(
                    reservation["id"],
                    "aprovada",
                )
                set_toast("Reserva aprovada.")
                st.session_state["detail_reservation_id"] = None
                st.rerun()

    else:
        if st.button(
            "Editar",
            key=f"details_edit_{reservation['id']}",
            use_container_width=True,
            icon=":material/edit:",
        ):
            st.session_state["edit_reservation_id"] = reservation["id"]
            st.session_state["detail_reservation_id"] = None
            st.rerun()


# ============================================================
# EDITAR
# ============================================================

@st.dialog("Editar reserva", width="medium")
def edit_reservation_dialog(reservation):
    st.caption(
        f"{reservation['requester']} · "
        f"{reservation['date']} · "
        f"{reservation['start']}–{reservation['end']}"
    )

    with st.form(f"edit_reservation_{reservation['id']}"):
        space_options = [
            space["name"]
            for space in st.session_state.spaces
            if space["status"] != "bloqueado"
        ]

        current_space = reservation["space"]

        if current_space not in space_options:
            space_options.insert(0, current_space)

        space = st.selectbox(
            "Espaço",
            space_options,
            index=space_options.index(current_space),
        )

        type_options = [
            "Aula",
            "Banca",
            "Workshop",
            "Reunião",
            "Monitoria",
        ]

        current_type = reservation["type"]

        if current_type not in type_options:
            type_options.insert(0, current_type)

        kind = st.selectbox(
            "Tipo",
            type_options,
            index=type_options.index(current_type),
        )

        date_value = st.date_input(
            "Data",
            value=_parse_date(reservation["date"]),
        )

        time_column_1, time_column_2 = st.columns(2)

        with time_column_1:
            start_value = st.time_input(
                "Início",
                value=_parse_time(reservation["start"]),
            )

        with time_column_2:
            end_value = st.time_input(
                "Fim",
                value=_parse_time(reservation["end"]),
            )

        participants = st.number_input(
            "Participantes",
            min_value=1,
            value=int(reservation.get("participants", 1)),
        )

        justification = st.text_area(
            "Justificativa",
            value=reservation.get("justification", ""),
        )

        st.divider()

        cancel_column, save_column = st.columns(2)

        with cancel_column:
            cancel = st.form_submit_button(
                "Cancelar",
                use_container_width=True,
            )

        with save_column:
            save = st.form_submit_button(
                "Salvar alterações",
                type="primary",
                use_container_width=True,
            )

    if cancel:
        st.session_state["edit_reservation_id"] = None
        st.rerun()

    if save:
        mock_data_service.update_reservation(
            reservation["id"],
            {
                "space": space,
                "type": kind,
                "date": date_value.isoformat(),
                "start": start_value.strftime("%H:%M"),
                "end": end_value.strftime("%H:%M"),
                "participants": participants,
                "justification": justification,
            },
        )

        st.session_state["edit_reservation_id"] = None
        set_toast("Reserva atualizada.")
        st.rerun()


# ============================================================
# REJEITAR
# ============================================================

@st.dialog("Rejeitar reserva", width="small")
def reject_reservation_dialog(reservation):
    st.caption(
        f"{reservation['requester']} · "
        f"{reservation['space']} · "
        f"{reservation['date']}"
    )

    reason = st.text_area(
        "Motivo da rejeição",
        placeholder="Informe o motivo para o solicitante...",
        height=110,
    )

    if st.button(
        "Confirmar rejeição",
        type="primary",
        use_container_width=True,
        disabled=not reason.strip(),
    ):
        mock_data_service.update_reservation_status(
            reservation["id"],
            "rejeitada",
        )

        set_toast("Reserva rejeitada.")
        st.session_state["reject_reservation_id"] = None
        st.rerun()


# ============================================================
# TABELA
# ============================================================

def _reservation_table(items):
    _load_reservations_table_style()

    with st.container(
        key="manager_reservations_table",
        border=False,
    ):
        # Cabeçalho
        with st.container(key="manager_reservation_header"):
            columns = st.columns(
                [2.1, 1.7, 1.25, 1.7, 1.3, 0.8],
                vertical_alignment="center",
            )

            headers = [
                "Solicitante",
                "Espaço",
                "Tipo",
                "Data / Horário",
                "Status",
                "Ações",
            ]

            for column, header in zip(columns, headers):
                with column:
                    st.markdown(header)

        # Linhas
        for item in items:
            row_key = f"manager_reservation_row_{item['id']}"

            with st.container(key=row_key):
                columns = st.columns(
                    [2.1, 1.7, 1.25, 1.7, 1.3, 0.8],
                    vertical_alignment="center",
                )

                with columns[0]:
                    st.markdown(
                        f"""
                        <div class="reservation-cell">
                            <div class="reservation-requester">
                                {item["requester"]}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                with columns[1]:
                    st.markdown(
                        f"""
                        <div class="reservation-cell">
                            <div class="reservation-secondary">
                                {item["space"]}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                with columns[2]:
                    st.markdown(
                        f"""
                        <div class="reservation-cell">
                            <div class="reservation-secondary">
                                {item["type"]}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                with columns[3]:
                    st.markdown(
                        f"""
                        <div class="reservation-cell">
                            <div class="reservation-date">
                                {item["date"]}
                            </div>
                            <div class="reservation-secondary">
                                {item["start"]} – {item["end"]}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                with columns[4]:
                    st.html(badge(item["status"]))

                with columns[5]:
                    if st.button(
                        "Ver",
                        key=f"view_reservation_{item['id']}",
                    ):
                        st.session_state["detail_reservation_id"] = item["id"]
                        st.rerun()

    if not items:
        st.markdown(
            """
            <div class="reservation-empty">
                Nenhuma reserva encontrada.
            </div>
            """,
            unsafe_allow_html=True,
        )


# ============================================================
# RESERVAS DO GERENTE
# ============================================================

def manager_reservations(user):
    page_header(
        "Reservas",
        "Analise e decida sobre as solicitações de reserva.",
    )

    # --------------------------------------------------------
    # Filtros
    # --------------------------------------------------------

    search_column, status_column = st.columns(
        [3, 1],
        vertical_alignment="bottom",
    )

    with search_column:
        search = st.text_input(
            "Buscar",
            placeholder="Buscar por solicitante ou espaço...",
            label_visibility="collapsed",
            icon=":material/search:",
        )

    with status_column:
        status = st.selectbox(
            "Status",
            STATUS_OPTIONS,
            format_func=lambda option: option[0],
        )

    status_value = status[1]

    items = mock_data_service.reservations()

    filtered_items = [
        item
        for item in items
        if _reservation_matches_search(item, search)
        and (
            status_value == "Todas"
            or item["status"] == status_value
        )
    ]

    st.write("")

    _reservation_table(filtered_items)

    # --------------------------------------------------------
    # Dialog de detalhes
    # --------------------------------------------------------

    detail_id = st.session_state.get("detail_reservation_id")

    if detail_id:
        detail = next(
            (
                item
                for item in items
                if item["id"] == detail_id
            ),
            None,
        )

        if detail:
            reservation_details_dialog(detail)

    # --------------------------------------------------------
    # Dialog de edição
    # --------------------------------------------------------

    edit_id = st.session_state.get("edit_reservation_id")

    if edit_id:
        edit_target = next(
            (
                item
                for item in items
                if item["id"] == edit_id
            ),
            None,
        )

        if edit_target:
            edit_reservation_dialog(edit_target)

    # --------------------------------------------------------
    # Dialog de rejeição
    # --------------------------------------------------------

    reject_id = st.session_state.get("reject_reservation_id")

    if reject_id:
        reject_target = next(
            (
                item
                for item in items
                if item["id"] == reject_id
            ),
            None,
        )

        if reject_target:
            reject_reservation_dialog(reject_target)


# ============================================================
# ADMIN
# ============================================================

def reservations_admin(user):
    page_header(
        "Reservas e solicitações",
        "Consulte as solicitações e acompanhe seus status.",
    )

    status = st.selectbox(
        "Status",
        [
            "Todas",
            "pendente",
            "em_analise",
            "aprovada",
            "rejeitada",
            "conflito",
        ],
    )

    items = mock_data_service.reservations(status=status)

    if not items:
        st.info("Nenhuma reserva encontrada.")
        return

    rows = [
        [
            item["requester"],
            item["type"],
            item["space"],
            item["date"],
            f"{item['start']}-{item['end']}",
            badge(item["status"]),
        ]
        for item in items
    ]

    from views.components.ui_components import table

    table(
        [
            "Solicitante",
            "Tipo",
            "Espaço",
            "Data",
            "Horário",
            "Status",
        ],
        rows,
    )


# ============================================================
# NOVA RESERVA
# ============================================================

def new_reservation(user):
    page_header(
        "Nova reserva",
        "Solicite um espaço disponível.",
    )

    with st.form("new_reservation"):
        title = st.text_input("Título")

        space = st.selectbox(
            "Espaço",
            [
                space["name"]
                for space in st.session_state.spaces
                if space["status"] != "bloqueado"
            ],
        )

        day = st.date_input("Data")

        start_column, end_column = st.columns(2)

        with start_column:
            start = st.time_input("Início")

        with end_column:
            end = st.time_input("Fim")

        kind = st.selectbox(
            "Tipo",
            [
                "Aula",
                "Banca",
                "Workshop",
                "Reunião",
                "Monitoria",
            ],
        )

        participants = st.number_input(
            "Participantes",
            min_value=1,
            value=12,
        )

        justification = st.text_area(
            "Justificativa",
        )

        submitted = st.form_submit_button(
            "Solicitar reserva",
            type="primary",
        )

    if submitted:
        mock_data_service.create_reservation(
            {
                "requester": user["name"],
                "requester_id": user["id"],
                "title": title,
                "space": space,
                "date": day.isoformat(),
                "start": start.strftime("%H:%M"),
                "end": end.strftime("%H:%M"),
                "type": kind,
                "participants": participants,
                "justification": justification,
            }
        )

        set_toast("Reserva enviada para análise.")
        go("minhas_reservas")


# ============================================================
# MINHAS RESERVAS
# ============================================================

def minhas_reservas(user):
    page_header(
        "Minhas reservas",
        "Acompanhe suas solicitações.",
    )

    items = mock_data_service.reservations(
        requester_id=user["id"],
    )

    reservation_cards(items)

    for item in items:
        if item["status"] in {"pendente", "aprovada"}:
            if st.button(
                f"Cancelar {item['title']}",
                key=f"cancel_{item['id']}",
            ):
                mock_data_service.update_reservation_status(
                    item["id"],
                    "rejeitada",
                )

                set_toast("Reserva cancelada no mock.")
                st.rerun()
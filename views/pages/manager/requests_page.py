import pandas as pd
import streamlit as st

from controllers import mock_data_service
from controllers.app_state_service import go, set_toast
from views.components.reservation_cards import reservation_cards
from views.components.ui_components import badge, page_header, table


STATUS_OPTIONS = [
    ("Todos os status", "Todas"),
    ("Pendente", "pendente"),
    ("Em análise", "em_analise"),
    ("Aprovada", "aprovada"),
    ("Rejeitada", "rejeitada"),
    ("Conflito", "conflito"),
]

STATUS_LABELS = {
    "pendente": "Pendente",
    "em_analise": "Em análise",
    "aprovada": "Aprovada",
    "rejeitada": "Rejeitada",
    "conflito": "Conflito",
}

ACTION_STATUSES = {"pendente", "em_analise"}


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


def _reservations_dataframe(items_list: list) -> pd.DataFrame:
    """Converte a lista de reservas no DataFrame padronizado para exibição no st.dataframe."""
    return pd.DataFrame(
        [
            {
                "Solicitante": item["requester"],
                "Espaço": item["space"],
                "Tipo": item["type"],
                "Data": item["date"],
                "Horário": f"{item['start']} – {item['end']}",
                "Status": STATUS_LABELS.get(item["status"], item["status"].capitalize()),
            }
            for item in items_list
        ]
    )


# ============================================================
# DETALHES DIALOG
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
                <div style="color: #73706A; font-size: 11px; margin-bottom: 4px;">SOLICITANTE</div>
                <div style="color: #231F20; font-size: 14px; font-weight: 600;">{reservation["requester"]}</div>
            </div>

            <div>
                <div style="color: #73706A; font-size: 11px; margin-bottom: 4px;">ESPAÇO</div>
                <div style="color: #231F20; font-size: 14px; font-weight: 600;">{reservation["space"]}</div>
            </div>

            <div>
                <div style="color: #73706A; font-size: 11px; margin-bottom: 4px;">TIPO</div>
                <div style="color: #231F20; font-size: 14px; font-weight: 600;">{reservation["type"]}</div>
            </div>

            <div>
                <div style="color: #73706A; font-size: 11px; margin-bottom: 4px;">PARTICIPANTES</div>
                <div style="color: #231F20; font-size: 14px; font-weight: 600;">{reservation.get("participants", 0)}</div>
            </div>

            <div>
                <div style="color: #73706A; font-size: 11px; margin-bottom: 4px;">DATA</div>
                <div style="color: #231F20; font-size: 14px; font-weight: 600;">{reservation["date"]}</div>
            </div>

            <div>
                <div style="color: #73706A; font-size: 11px; margin-bottom: 4px;">HORÁRIO</div>
                <div style="color: #231F20; font-size: 14px; font-weight: 600;">{reservation["start"]} – {reservation["end"]}</div>
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
            {reservation.get("justification", "Sem justificativa informada.")}
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.html(badge(reservation["status"]))

    st.divider()

    can_act = _can_act(reservation["status"])

    if can_act:
        edit_column, reject_column, approve_column = st.columns(3, gap="small")

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
# EDITAR DIALOG (COM SELEÇÃO DE STATUS / DECISÃO)
# ============================================================

@st.dialog("Editar reserva", width="medium")
def edit_reservation_dialog(reservation):
    st.caption(
        f"{reservation['requester']} · "
        f"{reservation['date']} · "
        f"{reservation['start']}–{reservation['end']}"
    )

    with st.form(f"edit_reservation_{reservation['id']}"):
        # Opções de status editáveis pelo gestor
        status_options = [
            ("Pendente", "pendente"),
            ("Em análise", "em_analise"),
            ("Aprovada", "aprovada"),
            ("Rejeitada", "rejeitada"),
            ("Conflito", "conflito"),
        ]

        # Encontra o índice do status atual para deixar selecionado por padrão
        current_status = reservation.get("status", "pendente")
        status_keys = [opt[1] for opt in status_options]
        default_index = status_keys.index(current_status) if current_status in status_keys else 0

        new_status_tuple = st.selectbox(
            "Decisão / Status",
            options=status_options,
            format_func=lambda opt: opt[0],
            index=default_index,
            help="Altere a decisão ou o estado atual da solicitação",
        )
        new_status = new_status_tuple[1]

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
                "status": new_status,
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
        set_toast("Reserva atualizada com sucesso.")
        st.rerun()


# ============================================================
# REJEITAR DIALOG
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
# RESERVAS DO GERENTE
# ============================================================

def manager_reservations(user=None):
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
            key="manager_search",
        )

    with status_column:
        status = st.selectbox(
            "Status",
            STATUS_OPTIONS,
            format_func=lambda option: option[0],
            label_visibility="collapsed",
            key="manager_status_filter",
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

    if not filtered_items:
        st.info("Nenhuma reserva encontrada.")
        return

    # --------------------------------------------------------
    # Container Informativo
    # --------------------------------------------------------
    with st.container(border=True):
        st.caption(
            ":material/info: Selecione uma solicitação abaixo no menu de ações para analisar detalhes, editar dados ou alterar o status."
        )

    # --------------------------------------------------------
    # Tabela (Estilo padronizado com st.dataframe)
    # --------------------------------------------------------
    df_reservations = _reservations_dataframe(filtered_items)
    st.dataframe(
        df_reservations,
        column_config={
            "Solicitante": st.column_config.TextColumn("Solicitante", width="medium", pinned=True),
            "Espaço": st.column_config.TextColumn("Espaço", width="medium"),
            "Tipo": st.column_config.TextColumn("Tipo", width="small"),
            "Data": st.column_config.TextColumn("Data", width="small"),
            "Horário": st.column_config.TextColumn("Horário", width="medium"),
            "Status": st.column_config.TextColumn("Status", width="small"),
        },
        hide_index=True,
        use_container_width=True,
    )

    # --------------------------------------------------------
    # Painel de Ações Operacionais sobre a Seleção
    # --------------------------------------------------------
    res_map = {
        f"{item['requester']} - {item['space']} ({item['date']} às {item['start']})": item
        for item in filtered_items
    }

    col_select, col_details, col_edit, col_reject, col_approve = st.columns(
        [3, 1, 1, 1, 1],
        vertical_alignment="bottom",
    )

    with col_select:
        selected_label = st.selectbox(
            "Ações da reserva",
            options=list(res_map.keys()),
            help="Selecione uma reserva para ver detalhes ou tomar ações",
        )
        selected_res = res_map[selected_label]

    can_act = _can_act(selected_res["status"])

    with col_details:
        if st.button("Ver", icon=":material/visibility:", use_container_width=True):
            st.session_state["detail_reservation_id"] = selected_res["id"]
            st.rerun()

    with col_edit:
        if st.button("Editar", icon=":material/edit:", use_container_width=True):
            st.session_state["edit_reservation_id"] = selected_res["id"]
            st.rerun()

    with col_reject:
        if st.button(
            "Rejeitar",
            icon=":material/close:",
            use_container_width=True,
            disabled=not can_act,
        ):
            st.session_state["reject_reservation_id"] = selected_res["id"]
            st.rerun()

    with col_approve:
        if st.button(
            "Aprovar",
            type="primary",
            icon=":material/check:",
            use_container_width=True,
            disabled=not can_act,
        ):
            mock_data_service.update_reservation_status(selected_res["id"], "aprovada")
            set_toast(f"Reserva de {selected_res['requester']} aprovada com sucesso.")
            st.rerun()

    # --------------------------------------------------------
    # Dialogs (Renderização condicional baseada no Session State)
    # --------------------------------------------------------
    detail_id = st.session_state.get("detail_reservation_id")
    if detail_id:
        detail = next((item for item in items if item["id"] == detail_id), None)
        if detail:
            reservation_details_dialog(detail)

    edit_id = st.session_state.get("edit_reservation_id")
    if edit_id:
        edit_target = next((item for item in items if item["id"] == edit_id), None)
        if edit_target:
            edit_reservation_dialog(edit_target)

    reject_id = st.session_state.get("reject_reservation_id")
    if reject_id:
        reject_target = next((item for item in items if item["id"] == reject_id), None)
        if reject_target:
            reject_reservation_dialog(reject_target)


# ============================================================
# ALIASES DE COMPATIBILIDADE
# ============================================================

reservations_admin = manager_reservations
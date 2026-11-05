import pandas as pd
import streamlit as st

from controllers import mock_data_service
from controllers.app_state_service import go
from views.components.ui_components import badge, page_header


QUICK_ACTIONS = [
    ("Reservas", "Analisar e decidir sobre solicitações", "reservas", ":material/meeting_room:"),
    ("Espaços", "Gerenciar capacidade e recursos das salas", "espacos", ":material/home_work:"),
    ("Conflitos", "Resolver conflitos de reservas e horários", "conflitos", ":material/warning:"),
]


def _navigate(page: str) -> None:
    go(page)
    st.rerun()


def _render_stats(pending: int, approved: int, available: int, conflicts: int) -> None:
    """Renderiza os cards de indicadores no mesmo padrão de métricas do admin."""
    metrics_data = (
        ("Pendentes", pending, "Aguardando análise", "normal" if pending == 0 else "inverse"),
        ("Aprovadas", approved, "Reservas ativas", "normal"),
        ("Salas livres", available, "Disponíveis hoje", "normal"),
        ("Conflitos abertos", conflicts, "Requer atenção", "off" if conflicts == 0 else "inverse"),
    )

    for column, (label, value, delta, delta_color) in zip(
        st.columns(4, gap="small"),
        metrics_data,
    ):
        with column.container(border=True):
            st.metric(label, value, delta=delta, delta_color=delta_color)


def _render_quick_actions() -> None:
    """Renderiza as ações rápidas com padrão idêntico ao dashboard admin."""
    st.subheader("Acesso rápido")
    for label, description, page, icon in QUICK_ACTIONS:
        with st.container(border=True):
            col_info, col_btn = st.columns([3, 1], vertical_alignment="center")
            with col_info:
                st.markdown(f"{icon} **{label}**")
            with col_btn:
                if st.button("Abrir", key=f"quick_action_{page}", icon=":material/arrow_forward:", use_container_width=True):
                    _navigate(page)
            st.caption(description)


def _render_pending_reservations(pending_reservations: list[dict]) -> None:
    """Renderiza a seção de solicitações pendentes com botão no topo alinhado à direita."""
    header_columns = st.columns([1, 0.3], vertical_alignment="center")

    with header_columns[0]:
        st.subheader("Solicitações pendentes")

    with header_columns[1]:
        if st.button("Ver todas", key="manager_dashboard_ver_reservas", icon=":material/arrow_forward:", use_container_width=True):
            _navigate("reservas")

    with st.container(border=True):
        if not pending_reservations:
            st.info("Nenhuma solicitação pendente.")
        else:
            rows = [
                {
                    "Título": res.get("title", "Reserva"),
                    "Espaço": res.get("space", "Espaço não informado"),
                    "Data": res.get("date", ""),
                    "Horário": f"{res.get('start', '')} – {res.get('end', '')}",
                    "Status": res.get("status", "").capitalize(),
                }
                for res in pending_reservations[:4]
            ]
            st.dataframe(
                pd.DataFrame(rows),
                column_config={
                    "Título": st.column_config.TextColumn("Título", width="medium"),
                    "Espaço": st.column_config.TextColumn("Espaço", width="medium"),
                    "Data": st.column_config.TextColumn("Data", width="small"),
                    "Horário": st.column_config.TextColumn("Horário", width="medium"),
                    "Status": st.column_config.TextColumn("Status", width="small"),
                },
                hide_index=True,
                width="stretch",
            )


def _occupancy_bar(label: str, count: int, total: int) -> None:
    """Renderiza uma linha de barra de progresso no mesmo layout visual da distribuição por perfil."""
    percentage = count / total if total else 0.0

    columns = st.columns(
        [1.5, 3.5, 0.4],
        vertical_alignment="center",
    )

    with columns[0]:
        st.caption(label)

    with columns[1]:
        st.progress(percentage, text=None)

    with columns[2]:
        st.write(f"**{count}**")


def _render_space_status_and_occupancy(spaces: list[dict]) -> None:
    """Renderiza lado a lado os painéis de status e ocupação dos espaços."""
    col_status, col_occupancy = st.columns(2, gap="medium")

    # --- PAINEL: STATUS DOS ESPAÇOS ---
    with col_status:
        header_columns = st.columns([1, 0.3], vertical_alignment="center")
        with header_columns[0]:
            st.subheader("Status dos espaços")
        with header_columns[1]:
            if st.button("Gerenciar", key="manager_dashboard_gerenciar_espacos", icon=":material/home_work:", use_container_width=True):
                _navigate("espacos")

        with st.container(border=True):
            if not spaces:
                st.caption("Nenhum espaço cadastrado.")
            else:
                rows = [
                    {
                        "Espaço": space.get("name", "Espaço"),
                        "Localização": space.get("location", "N/I"),
                        "Status": space.get("status", "").capitalize(),
                    }
                    for space in spaces[:5]
                ]
                st.dataframe(
                    pd.DataFrame(rows),
                    column_config={
                        "Espaço": st.column_config.TextColumn("Espaço", width="medium"),
                        "Localização": st.column_config.TextColumn("Localização", width="medium"),
                        "Status": st.column_config.TextColumn("Status", width="small"),
                    },
                    hide_index=True,
                    width="stretch",
                )

    # --- PAINEL: OCUPAÇÃO DOS ESPAÇOS ---
    with col_occupancy:
        header_columns = st.columns([1, 0.3], vertical_alignment="center")
        with header_columns[0]:
            st.subheader("Ocupação dos espaços")
        with header_columns[1]:
            if st.button("Ver mais", key="manager_dashboard_ver_ocupacao", icon=":material/arrow_forward:", use_container_width=True):
                _navigate("ocupacao")

        available_count = sum(1 for s in spaces if s.get("status") == "disponivel")
        occupied_count = sum(1 for s in spaces if s.get("status") == "ocupado")
        blocked_count = sum(1 for s in spaces if s.get("status") == "bloqueado")
        total_spaces = len(spaces)

        with st.container(border=True):
            _occupancy_bar("Disponíveis", available_count, total_spaces)
            _occupancy_bar("Ocupadas", occupied_count, total_spaces)
            _occupancy_bar("Bloqueadas", blocked_count, total_spaces)

            occupancy_rate = round((occupied_count / total_spaces) * 100) if total_spaces else 0

            st.divider()

            st.caption(f"Taxa de ocupação atual: **{occupancy_rate}%**")


def dashboard(user):
    page_header("Painel operacional", "Visão geral das reservas, espaços e conflitos do dia.")

    reservations = mock_data_service.reservations()
    spaces = mock_data_service.spaces()
    conflicts = st.session_state.get("conflicts", [])

    pending_reservations = [item for item in reservations if item.get("status") in {"pendente", "em_analise"}]
    approved_reservations = [item for item in reservations if item.get("status") == "aprovada"]
    available_spaces = [item for item in spaces if item.get("status") == "disponivel"]
    open_conflicts = [item for item in conflicts if item.get("status") in {"nao_resolvido", "em_analise"}]

    # 1. Indicadores Superiores
    _render_stats(
        pending=len(pending_reservations),
        approved=len(approved_reservations),
        available=len(available_spaces),
        conflicts=len(open_conflicts),
    )
    st.space("small")

    # 2. Ações Rápidas + Solicitações Pendentes
    actions, pending_panel = st.columns([1, 2], gap="medium")
    with actions:
        _render_quick_actions()
    with pending_panel:
        _render_pending_reservations(pending_reservations)

    st.space("small")

    # 3. Status dos Espaços + Ocupação
    _render_space_status_and_occupancy(spaces)
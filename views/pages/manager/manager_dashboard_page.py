import pandas as pd
import streamlit as st

from config.constants import STATUS_LABELS
from controllers.app_state_service import set_page
from views.components.manager_operations import ROOM_STATUS_LABELS, dashboard_dates, operations_api, space_filters
from views.components.reservation_forms import RESERVATION_ERRORS, local_times
from views.components.ui_components import page_header


QUICK_ACTIONS = [
    ("Reservas", "Analisar e decidir sobre solicitações", "gerente_reservas", ":material/meeting_room:"),
    ("Espaços", "Gerenciar capacidade e recursos das salas", "espacos", ":material/home_work:"),
    ("Conflitos", "Resolver conflitos de reservas e horários", "gerente_conflitos", ":material/warning:"),
]


def _render_stats(report: dict) -> None:
    """Renderiza os cards de indicadores no mesmo padrão de métricas do admin."""
    metrics = report["metrics"]
    for columns, items in (
        (st.columns(4, gap="small"), (
            ("Pendentes", metrics["pending"]), ("Aprovadas", metrics["approved"]),
            ("Salas livres", report["space_counts"]["available"]), ("Conflitos abertos", metrics["conflicts"]),
        )),
        (st.columns(2, gap="small"), (("Rejeitadas", metrics["rejected"]), ("Canceladas", metrics["cancelled"]))),
    ):
        for column, (label, value) in zip(columns, items, strict=True):
            column.metric(label, value, border=True)


def _render_quick_actions() -> None:
    """Renderiza as ações rápidas com padrão idêntico ao dashboard admin."""
    st.subheader("Acesso rápido")
    for label, description, page, icon in QUICK_ACTIONS:
        with st.container(border=True):
            col_info, col_btn = st.columns([3, 1], vertical_alignment="center")
            with col_info:
                st.markdown(f"{icon} **{label}**")
            with col_btn:
                st.button(
                    "Abrir", key=f"quick_action_{page}", icon=":material/arrow_forward:", width="stretch",
                    on_click=set_page, args=(page,),
                )
            st.caption(description)


def _render_reservations(reservations: list[dict], timezone: str, status: str | None) -> None:
    header_columns = st.columns([1, 0.3], vertical_alignment="center")

    with header_columns[0]:
        st.subheader(f"Solicitações · {STATUS_LABELS[status]}" if status else "Solicitações pendentes")

    with header_columns[1]:
        st.button(
            "Ver todas", key="manager_dashboard_ver_reservas", icon=":material/arrow_forward:", width="stretch",
            on_click=set_page, args=("gerente_reservas",),
        )

    with st.container(border=True):
        if not reservations:
            st.info("Nenhuma solicitação para os filtros selecionados.")
        else:
            rows = []
            for reservation in reservations[:4]:
                start, end = local_times(reservation, timezone)
                rows.append({
                    "Título": reservation["title"], "Espaço": reservation["space_name"], "Data": f"{start:%d/%m/%Y}",
                    "Horário": f"{start:%H:%M}–{end:%H:%M}", "Status": STATUS_LABELS[reservation["status"]],
                })
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


def _render_space_status_and_occupancy(report: dict) -> None:
    """Renderiza lado a lado os painéis de status e ocupação dos espaços."""
    col_status, col_occupancy = st.columns(2, gap="medium")
    spaces = report["spaces"]
    counts = report["space_counts"]

    # --- PAINEL: STATUS DOS ESPAÇOS ---
    with col_status:
        header_columns = st.columns([1, 0.3], vertical_alignment="center")
        with header_columns[0]:
            st.subheader("Status dos espaços")
        with header_columns[1]:
            st.button(
                "Gerenciar", key="manager_dashboard_gerenciar_espacos", icon=":material/home_work:", width="stretch",
                on_click=set_page, args=("espacos",),
            )

        with st.container(border=True):
            if not spaces:
                st.caption("Nenhum espaço cadastrado.")
            else:
                rows = [
                    {
                        "Espaço": space["name"],
                        "Localização": space["location"],
                        "Status": ROOM_STATUS_LABELS[space["status"]],
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
            st.button(
                "Ver mais", key="manager_dashboard_ver_ocupacao", icon=":material/arrow_forward:", width="stretch",
                on_click=set_page, args=("ocupacao",),
            )

        with st.container(border=True):
            _occupancy_bar("Disponíveis", counts["available"], counts["total"])
            _occupancy_bar("Ocupadas", counts["occupied"], counts["total"])
            _occupancy_bar("Com bloqueio", counts["blocked"], counts["total"])
            if counts["inactive"] or counts["unavailable"]:
                _occupancy_bar("Indisponíveis", counts["inactive"] + counts["unavailable"], counts["total"])
            st.divider()
            st.caption(f"Taxa de ocupação no período **{report['occupancy_rate']:.1%}**")


def dashboard(user):
    page_header("Painel operacional", "Visão geral das reservas, espaços e conflitos no período.")
    api = operations_api()
    if api is None:
        return
    try:
        context = api.context()
        dates = dashboard_dates(context)
        filters = space_filters(context, "dashboard", include_status=True)
        report = api.report(**dates, **filters)
    except RESERVATION_ERRORS as error:
        st.error(str(error))
        return
    status = filters["status"]
    reservations = report["reservations"]
    if status is None:
        reservations = [item for item in reservations if item["status"] in {"pendente", "em_analise"}]
    _render_stats(report)
    st.space("small")

    actions, pending_panel = st.columns([1, 2], gap="medium")
    with actions:
        _render_quick_actions()
    with pending_panel:
        _render_reservations(reservations, report["timezone"], status)

    st.space("small")

    _render_space_status_and_occupancy(report)

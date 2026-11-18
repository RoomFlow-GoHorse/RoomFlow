import pandas as pd
import streamlit as st

from controllers import mock_data_service
from controllers.app_state_service import set_toast
from views.components.ui_components import badge, page_header

# ============================================================
# HELPERS
# ============================================================

def _reservations_for(conflict: dict) -> list:
    """Retorna a lista de objetos de reserva envolvidos em um conflito."""
    identifiers = conflict.get("affected_reservations") or [
        conflict.get("reservation_a"),
        conflict.get("reservation_b"),
    ]

    by_id = {res["id"]: res for res in st.session_state.get("reservations", [])}
    return [by_id[res_id] for res_id in identifiers if res_id in by_id]


def _conflict_schedule(conflict: dict, reservations: list) -> str:
    """Gera o texto de data e horário do conflito."""
    if reservations:
        first = reservations[0]
        return f"{first.get('date', '')} · {first.get('start', '')}–{first.get('end', '')}"
    return conflict.get("reason", "Horário não informado")


def _conflicts_dataframe(conflicts_list: list) -> pd.DataFrame:
    """Transforma a lista de conflitos em um DataFrame estruturado."""
    status_map = {
        "nao_resolvido": "Em aberto",
        "em_analise": "Em análise",
        "resolvido": "Resolvido",
    }

    rows = []
    for conflict in conflicts_list:
        reservations = _reservations_for(conflict)
        requesters = [r["requester"] for r in reservations] if reservations else []
        envolved = " x ".join(requesters) if requesters else "Reservas indisponíveis"

        rows.append(
            {
                "ID": conflict["id"].upper(),
                "Espaço": conflict.get("space", "N/A"),
                "Data / Horário": _conflict_schedule(conflict, reservations),
                "Solicitantes Envolvidos": envolved,
                "Status": status_map.get(conflict.get("status"), conflict.get("status", "").capitalize()),
                "Detectado": conflict.get("detected_at", "N/A"),
            }
        )

    return pd.DataFrame(rows)

# ============================================================
# DIALOGS
# ============================================================

@st.dialog("Resolver conflito", width="medium")
def resolve_conflict_dialog(conflict: dict, reservations: list):
    st.caption(f"{conflict.get('space', '')} · {_conflict_schedule(conflict, reservations)}")

    if reservations:
        st.markdown("**Reservas envolvidas**")
        cols = st.columns(min(len(reservations), 2))
        
        for idx, res in enumerate(reservations):
            col_target = cols[idx % len(cols)]
            with col_target:
                with st.container(border=True):
                    st.caption(f"Reserva {chr(65 + idx)}")
                    st.markdown(f"**{res.get('requester', 'N/A')}**")
                    st.caption(f"{res.get('title', '')} · {res.get('type', '')}")
                    st.caption(f"{res.get('participants', 0)} pessoas")
                    st.caption(
                        f"Justificativa: {res.get('justification') or 'Sem justificativa informada.'}"
                    )
    else:
        st.info("As reservas originais não estão disponíveis no ambiente atual.")

    outcomes = {}
    if reservations:
        outcomes[f"Manter reserva A ({reservations[0]['requester']})"] = "manteve_a"
    if len(reservations) > 1:
        outcomes[f"Manter reserva B ({reservations[1]['requester']})"] = "manteve_b"
    outcomes["Sugerir espaço alternativo"] = "alterou"

    with st.form(key=f"resolve_conflict_form_{conflict['id']}"):
        selected_label = st.selectbox(
            "Resultado da análise",
            options=list(outcomes.keys()),
            key=f"conflict_outcome_{conflict['id']}",
        )

        justification = st.text_area(
            "Decisão / Justificativa *",
            placeholder="Descreva a decisão tomada e o motivo...",
            key=f"conflict_justification_{conflict['id']}",
        )

        cancel_col, resolve_col = st.columns(2)
        with cancel_col:
            cancelled = st.form_submit_button("Cancelar", use_container_width=True)
        with resolve_col:
            resolved = st.form_submit_button(
                "Marcar como resolvido",
                type="primary",
                icon=":material/check:",
                use_container_width=True,
            )

    if cancelled:
        st.session_state["resolve_conflict_id"] = None
        st.rerun()

    if resolved:
        if not justification.strip():
            st.error("Informe a justificativa para a decisão.")
            return

        mock_data_service.resolve_conflict(
            conflict["id"],
            justification.strip(),
            outcome=outcomes[selected_label],
        )

        st.session_state["resolve_conflict_id"] = None
        set_toast("Conflito resolvido com sucesso.")
        st.rerun()

# ============================================================
# COMPONENTE DE TABELA E AÇÕES
# ============================================================

def _conflict_table_and_actions(conflicts_list: list):
    with st.container(border=True):
        st.caption(
            ":material/info: Selecione um conflito abaixo no menu de ações para analisar os detalhes e tomar uma decisão."
        )

    df_conflicts = _conflicts_dataframe(conflicts_list)

    st.dataframe(
        df_conflicts,
        column_config={
            "ID": st.column_config.TextColumn("ID", width="small", pinned=True),
            "Espaço": st.column_config.TextColumn("Espaço", width="medium"),
            "Data / Horário": st.column_config.TextColumn("Data / Horário", width="medium"),
            "Solicitantes Envolvidos": st.column_config.TextColumn("Solicitantes", width="large"),
            "Status": st.column_config.TextColumn("Status", width="small"),
            "Detectado": st.column_config.TextColumn("Detectado", width="small"),
        },
        hide_index=True,
        use_container_width=True,
    )

    conflict_map = {
        f"{c['id'].upper()} - {c.get('space', 'Espaço')} ({c.get('status', '').replace('_', ' ').title()})": c
        for c in conflicts_list
    }

    col_select, col_action = st.columns([4, 1], vertical_alignment="bottom")

    with col_select:
        selected_label = st.selectbox(
            "Ações do conflito",
            options=list(conflict_map.keys()),
            help="Selecione um conflito para solucionar",
            key="select_conflict_action",
        )
        selected_conflict = conflict_map.get(selected_label, conflicts_list[0])

    is_resolved = selected_conflict.get("status") == "resolvido"

    with col_action:
        if st.button(
            "Resolver conflito",
            icon=":material/check:",
            type="primary",
            use_container_width=True,
            disabled=is_resolved,
            key="btn_resolve_conflict",
        ):
            st.session_state["resolve_conflict_id"] = selected_conflict["id"]
            st.rerun()


def _render_dialogs(all_conflicts: list):
    target_id = st.session_state.get("resolve_conflict_id")
    if target_id:
        target = next((c for c in all_conflicts if c["id"] == target_id), None)
        if target:
            reservations = _reservations_for(target)
            resolve_conflict_dialog(target, reservations)

# ============================================================
# MAIN VIEW
# ============================================================

def conflicts(user=None):
    page_header(
        "Conflitos",
        "Resolva conflitos de reservas e bloqueios de espaços.",
    )

    all_conflicts = st.session_state.get("conflicts", [])

    if not all_conflicts:
        st.info("Nenhum conflito registrado.", icon=":material/check_circle:")
        return

    search_col, status_col = st.columns([3, 1], vertical_alignment="bottom")

    query = search_col.text_input(
        "Buscar conflito",
        placeholder="Buscar por ID ou espaço...",
        icon=":material/search:",
        label_visibility="collapsed",
        key="conflict_search_query",
    )

    status_filter = status_col.selectbox(
        "Filtrar por status",
        ["Todos", "Em aberto", "Em análise", "Resolvidos"],
        label_visibility="collapsed",
        key="conflict_status_filter",
    )

    statuses_by_filter = {
        "Todos": {"nao_resolvido", "em_analise", "resolvido"},
        "Em aberto": {"nao_resolvido"},
        "Em análise": {"em_analise"},
        "Resolvidos": {"resolvido"},
    }

    filtered_conflicts = [
        c for c in all_conflicts
        if c.get("status") in statuses_by_filter[status_filter]
        and (not query or query.lower() in c.get("id", "").lower() or query.lower() in c.get("space", "").lower())
    ]

    st.write("")

    if not filtered_conflicts:
        st.info("Nenhum conflito encontrado para o filtro selecionado.", icon=":material/search_off:")
        return

    _conflict_table_and_actions(filtered_conflicts)
    _render_dialogs(all_conflicts)
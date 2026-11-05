from typing import Any, Dict, List, Optional

import streamlit as st

from views.components.ui_components import esc, page_header

# =========================================================
# CONFIGURAÇÕES DE FILTROS E TIPOS
# =========================================================

FILTERS_BY_ROLE: Dict[str, List[Dict[str, str]]] = {
    "solicitante": [
        {"id": "nao-lidas", "label": "Não lidas"},
        {"id": "todas", "label": "Todas"},
        {"id": "reservas", "label": "Reservas"},
        {"id": "alteracoes", "label": "Alterações"},
        {"id": "conflitos", "label": "Conflitos"},
    ],
    "participante": [
        {"id": "nao-lidas", "label": "Não lidas"},
        {"id": "todas", "label": "Todas"},
        {"id": "alteracoes", "label": "Alterações"},
    ],
    "admin": [
        {"id": "nao-lidas", "label": "Não lidas"},
        {"id": "todas", "label": "Todas"},
        {"id": "reservas", "label": "Reservas"},
        {"id": "conflitos", "label": "Conflitos"},
    ],
    "gerente": [
        {"id": "nao-lidas", "label": "Não lidas"},
        {"id": "todas", "label": "Todas"},
        {"id": "reservas", "label": "Reservas"},
        {"id": "conflitos", "label": "Conflitos"},
    ],
}

CATEGORY_CONFIG: Dict[str, str] = {
    "reserva": "Reserva",
    "alteracao": "Alteração",
    "conflito": "Conflito",
}


# =========================================================
# ESTILOS VISUAIS DA PÁGINA
# =========================================================

def _render_styles() -> None:
    """Aplica ajustes finos de CSS para os cards de notificação."""
    st.html(
        """
        <style>
        [class*="st-key-rf_notif_card_"],
        [class*="st-key-rf_notif_unread_"] {
            background-color: var(--surface-card);
            border: 1px solid var(--stroke);
            border-radius: 10px;
        }

        [class*="st-key-rf_notif_unread_"] {
            border-left: 4px solid var(--brand, #6D28D9);
        }
        </style>
        """
    )


# =========================================================
# FUNÇÕES AUXILIARES DE ESTADO
# =========================================================

def _mark_read(notif_id: str) -> None:
    """Marca uma notificação específica como lida."""
    if "notifications" in st.session_state:
        for item in st.session_state.notifications:
            if item.get("id") == notif_id:
                item["read"] = True
                break


def _mark_all_read(user_notifs: List[Dict[str, Any]]) -> None:
    """Marca todas as notificações visíveis como lidas."""
    ids_to_mark = {n.get("id") for n in user_notifs if "id" in n}
    if "notifications" in st.session_state:
        for item in st.session_state.notifications:
            if item.get("id") in ids_to_mark:
                item["read"] = True


def _delete_notification(notif_id: str) -> None:
    """Remove a notificação da lista mantida na sessão."""
    if "notifications" in st.session_state:
        st.session_state.notifications = [
            item
            for item in st.session_state.notifications
            if item.get("id") != notif_id
        ]


def _render_notification_card(n: Dict[str, Any]) -> None:
    """Renderiza individualmente cada card de notificação."""
    nid = n.get("id", "unknown")
    is_read = n.get("read", False)
    title = n.get("title", "Notificação")
    message = n.get("message") or n.get("body", "")
    date_str = n.get("date", "")
    ncat = n.get("category", "reserva")

    category_label = CATEGORY_CONFIG.get(ncat, "Notificação")
    card_key = f"rf_notif_unread_{nid}" if not is_read else f"rf_notif_card_{nid}"

    with st.container(border=True, key=card_key):
        # Cabeçalho do Card
        meta_col, date_col = st.columns([3, 1], vertical_alignment="center")

        with meta_col:
            unread_badge = " :violet[● Não lida]" if not is_read else ""
            st.caption(f"**{category_label.upper()}**{unread_badge}")

        with date_col:
            st.caption(f":material/schedule: {date_str}")

        # Conteúdo do Card
        st.markdown(f"#### {esc(title)}")
        st.write(esc(message))

        st.divider()

        # Ações do Card
        act_col1, act_col2 = st.columns([4, 1], vertical_alignment="center")

        with act_col1:
            if not is_read:
                if st.button(
                    "Marcar como lida",
                    key=f"btn_read_{nid}",
                    icon=":material/check_circle:",
                    type="secondary",
                ):
                    _mark_read(nid)
                    st.rerun()

        with act_col2:
            if st.button(
                "Excluir",
                key=f"btn_del_{nid}",
                icon=":material/delete:",
                type="tertiary",
            ):
                _delete_notification(nid)
                st.rerun()


# =========================================================
# PÁGINA PRINCIPAL DE NOTIFICAÇÕES
# =========================================================

def notifications(user: Optional[Dict[str, Any]] = None) -> None:
    """Página de listagem e gerenciamento de notificações."""
    _render_styles()

    # Validação de Usuário
    if not user:
        page_header(
            title="Notificações",
            subtitle="Nenhum usuário autenticado",
        )
        with st.container(border=True):
            st.markdown("### :material/lock: Autenticação necessária")
            st.caption("Faça login para visualizar suas notificações personalizadas.")
        return

    role = user.get("role", "participante")

    # 1. Obtenção dos filtros pelo perfil do usuário
    available_filters = FILTERS_BY_ROLE.get(role, FILTERS_BY_ROLE["participante"])
    filter_labels_map = {f["id"]: f["label"] for f in available_filters}
    filter_options = list(filter_labels_map.values())

    # 2. Filtrar notificações destinadas ao usuário (ignorando categoria "sistema")
    all_notifications = st.session_state.get("notifications", [])
    user_notifications = [
        item
        for item in all_notifications
        if item.get("category") != "sistema" and role in item.get("audiences", [])
    ]

    # Regra de negócio: Ocultar visualmente reserva + info
    user_notifications = [
        item
        for item in user_notifications
        if not (item.get("category") == "reserva" and item.get("type") == "info")
    ]

    # Contagem de Não Lidas
    unread_count = sum(not n.get("read", False) for n in user_notifications)

    # 3. Cabeçalho Dinâmico
    subtitle = (
        f"{unread_count} não lida{'s' if unread_count != 1 else ''}"
        if unread_count > 0
        else "Todas as notificações estão lidas"
    )

    col_title, col_action = st.columns([3, 1], vertical_alignment="center")

    with col_title:
        page_header(title="Notificações", subtitle=subtitle)

    with col_action:
        if unread_count > 0:
            if st.button(
                "Marcar todas como lidas",
                key="btn_mark_all_read",
                icon=":material/done_all:",
                use_container_width=True,
            ):
                _mark_all_read(user_notifications)
                st.rerun()

    # 4. Controle de Filtro com Segmented Control
    selected_label = st.segmented_control(
        "Filtrar notificações",
        options=filter_options,
        default=filter_options[0] if filter_options else None,
        label_visibility="collapsed",
    )

    # Identifica o ID do filtro selecionado
    selected_id = next(
        (fid for fid, label in filter_labels_map.items() if label == selected_label),
        "todas",
    )

    # 5. Aplicação do Filtro na Lista
    filter_map = {
        "nao-lidas": lambda n: not n.get("read", False),
        "reservas": lambda n: n.get("category") == "reserva",
        "alteracoes": lambda n: n.get("category") == "alteracao",
        "conflitos": lambda n: n.get("category") == "conflito",
        "todas": lambda n: True,
    }

    filter_fn = filter_map.get(selected_id, lambda n: True)
    filtered = [n for n in user_notifications if filter_fn(n)]

    # 6. Exibição da Lista de Notificações ou Estado Vazio
    if not filtered:
        with st.container(border=True):
            st.markdown("### :material/notifications_off: Nenhuma notificação")
            st.caption("Não existem notificações para o filtro selecionado.")
        return

    # Renderiza a lista de cards
    for n in filtered:
        _render_notification_card(n)
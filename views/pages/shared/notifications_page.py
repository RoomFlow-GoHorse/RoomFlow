import streamlit as st

from views.components.ui_components import esc, page_header

# =========================================================
# CONFIGURAÇÕES DE FILTROS E TIPOS
# =========================================================

FILTERS_BY_ROLE = {
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

TYPE_CONFIG = {
    "success": {
        "badge_bg": "#DCFCE7",
        "badge_color": "#15803D",
        "badge_label": "Sucesso",
    },
    "danger": {
        "badge_bg": "#FEE2E2",
        "badge_color": "#B91C1C",
        "badge_label": "Alerta",
    },
    "warning": {
        "badge_bg": "#FEF3C7",
        "badge_color": "#B45309",
        "badge_label": "Atenção",
    },
    "info": {
        "badge_bg": "#E0F2FE",
        "badge_color": "#0369A1",
        "badge_label": "Informação",
    },
}

CATEGORY_CONFIG = {
    "reserva": {"label": "Reserva"},
    "alteracao": {"label": "Alteração"},
    "conflito": {"label": "Conflito"},
}


# =========================================================
# ESTILOS VISUAIS DA PÁGINA
# =========================================================

def _render_styles():
    st.markdown(
        """
        <style>
            [class*="st-key-rf_notif_card_"],
            [class*="st-key-rf_notif_unread_"] {
                border-radius: 12px !important;
                padding: 16px !important;
                margin-bottom: 12px !important;
                transition: all 0.2s ease;
            }

            [class*="st-key-rf_notif_card_"] {
                background-color: var(--surface-card) !important;
                border: 1px solid var(--stroke) !important;
            }

            [class*="st-key-rf_notif_unread_"] {
                background-color: var(--brand-lighter) !important;
                border: 1px solid rgba(109, 40, 217, 0.25) !important;
            }

            .rf-notif-title {
                font-size: 14px;
                font-weight: 600;
                color: var(--graphite);
                margin-bottom: 2px;
            }

            .rf-notif-message {
                font-size: 13.5px;
                line-height: 1.5;
                color: var(--graphite-soft);
                margin-bottom: 4px;
            }

            .rf-notif-dot {
                width: 6px;
                height: 6px;
                border-radius: 50%;
                background-color: var(--brand);
                display: inline-block;
                margin-top: 6px;
            }

            .rf-notif-badge {
                display: inline-block;
                padding: 2px 8px;
                border-radius: 999px;
                font-size: 11px;
                font-weight: 600;
            }

            [class*="st-key-rf_notif_card_"] hr,
            [class*="st-key-rf_notif_unread_"] hr {
                margin: 8px 0 !important;
                border-color: var(--stroke) !important;
            }

            [class*="st-key-rf_notif_card_"] button[kind="tertiary"],
            [class*="st-key-rf_notif_unread_"] button[kind="tertiary"] {
                padding: 0 !important;
                background: transparent !important;
                border: none !important;
                font-size: 12px !important;
                font-weight: 500 !important;
                color: #52525B !important;
                box-shadow: none !important;
            }

            [class*="st-key-rf_notif_card_"] button[kind="tertiary"]:hover,
            [class*="st-key-rf_notif_unread_"] button[kind="tertiary"]:hover {
                color: #6D28D9 !important;
                text-decoration: underline !important;
            }

            .st-key-rf_mark_all_btn button {
                color: #6D28D9 !important;
                font-size: 13px !important;
                font-weight: 600 !important;
                background: transparent !important;
                border: none !important;
                box-shadow: none !important;
            }

            .st-key-rf_mark_all_btn button:hover {
                text-decoration: underline !important;
            }

            /* Card de filtros */
            .st-key-rf_notif_filters {
                background: var(--surface-card) !important;
                border: 1px solid var(--stroke) !important;
                border-radius: 12px !important;
                padding: 16px !important;
                margin-bottom: 20px !important;
            }

            .rf-filter-label {
                font-size: 11px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.06em;
                color: var(--graphite-muted);
                margin-bottom: 10px;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# FUNÇÕES AUXILIARES DE ESTADO
# =========================================================

def _mark_read(notif_id: str):
    if "notifications" in st.session_state:
        for item in st.session_state.notifications:
            if item["id"] == notif_id:
                item["read"] = True
                break


def _mark_all_read(user_notifs: list):
    ids_to_mark = {n["id"] for n in user_notifs}
    if "notifications" in st.session_state:
        for item in st.session_state.notifications:
            if item["id"] in ids_to_mark:
                item["read"] = True


def _delete_notification(notif_id: str):
    if "notifications" in st.session_state:
        st.session_state.notifications = [
            item for item in st.session_state.notifications if item["id"] != notif_id
        ]


# =========================================================
# PÁGINA PRINCIPAL DE NOTIFICAÇÕES
# =========================================================

def notifications(user: dict = None):
    _render_styles()

    # Caso não exista usuário autenticado
    if not user:
        page_header(
            title="Notificações",
            subtitle="Nenhum usuário autenticado",
        )
        with st.container(border=True):
            st.markdown(
                """
                <div style="text-align: center; padding: 32px 16px;">
                    <p style="font-size: 14px; font-weight: 600; color: #1C1C2E; margin-bottom: 4px;">
                        Faça login para visualizar suas notificações
                    </p>
                    <p style="font-size: 12px; color: #71717A; margin: 0;">
                        As notificações são específicas para cada perfil.
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        return

    role = user.get("role", "participante")

    # 1. Filtros disponíveis para o perfil
    available_filters = FILTERS_BY_ROLE.get(role, FILTERS_BY_ROLE["participante"])
    available_filter_ids = {f["id"] for f in available_filters}

    if "notifications_filter" not in st.session_state or st.session_state.notifications_filter not in available_filter_ids:
        st.session_state.notifications_filter = "todas"

    current_filter = st.session_state.notifications_filter

    # 2. Filtrar notificações destinadas ao usuário (ignorando categoria "sistema")
    all_notifications = st.session_state.get("notifications", [])
    user_notifications = [
        item
        for item in all_notifications
        if item.get("category") != "sistema" and role in item.get("audiences", [])
    ]

    # 3. Aplicar regra existente: ocultar de forma visual notificações com category == "reserva" E type == "info"
    user_notifications = [
        item
        for item in user_notifications
        if not (item.get("category") == "reserva" and item.get("type") == "info")
    ]

    # Contagem de não lidas
    unread_count = sum(not n.get("read", False) for n in user_notifications)

    # 4. Cabeçalho dinâmico
    if unread_count > 0:
        desc_text = f"{unread_count} não lida{'s' if unread_count != 1 else ''}"
    else:
        desc_text = "Todas as notificações lidas"

    col_title, col_action = st.columns([3, 1], vertical_alignment="center")

    with col_title:
        page_header(title="Notificações", subtitle=desc_text)

    with col_action:
        if unread_count > 0:
            with st.container(key="rf_mark_all_btn"):
                if st.button("✓ Marcar todas como lidas", key="btn_mark_all_read"):
                    _mark_all_read(user_notifications)
                    st.rerun()

    # 5. Cálculo dos contadores por filtro
    counts = {
        "todas": len(user_notifications),
        "nao-lidas": sum(not n.get("read", False) for n in user_notifications),
        "reservas": sum(n.get("category") == "reserva" for n in user_notifications),
        "alteracoes": sum(n.get("category") == "alteracao" for n in user_notifications),
        "conflitos": sum(n.get("category") == "conflito" for n in user_notifications),
    }

    # Renderizar card de filtros com botões nativos do Streamlit
    with st.container(border=True, key="rf_notif_filters"):
        st.markdown('<div class="rf-filter-label">Filtrar notificações</div>', unsafe_allow_html=True)
        filter_cols = st.columns(len(available_filters))
        for idx, f in enumerate(available_filters):
            fid = f["id"]
            flabel = f["label"]
            fcount = counts.get(fid, 0)
            is_selected = current_filter == fid

            btn_label = f"{flabel} ({fcount})" if fcount > 0 else flabel
            btn_type = "primary" if is_selected else "secondary"

            with filter_cols[idx]:
                if st.button(
                    btn_label,
                    key=f"filter_btn_{fid}",
                    type=btn_type,
                    use_container_width=True,
                ):
                    st.session_state.notifications_filter = fid
                    st.rerun()

    # 6. Filtrar notificações pelo filtro selecionado
    if current_filter == "nao-lidas":
        filtered = [n for n in user_notifications if not n.get("read", False)]
    elif current_filter == "reservas":
        filtered = [n for n in user_notifications if n.get("category") == "reserva"]
    elif current_filter == "alteracoes":
        filtered = [n for n in user_notifications if n.get("category") == "alteracao"]
    elif current_filter == "conflitos":
        filtered = [n for n in user_notifications if n.get("category") == "conflito"]
    else:
        filtered = user_notifications

    # 7. Exibição da Lista ou Estado Vazio
    if not filtered:
        with st.container(border=True):
            st.markdown(
                """
                <div style="text-align: center; padding: 48px 16px;">
                    <p style="font-size: 14px; font-weight: 600; color: #1C1C2E; margin-bottom: 4px;">
                        Nenhuma notificação encontrada
                    </p>
                    <p style="font-size: 12px; color: #71717A; margin: 0;">
                        Não há notificações para o filtro selecionado.
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        if current_filter != "todas":
            st.write("")
            col_reset_center = st.columns([1, 2, 1])
            with col_reset_center[1]:
                if st.button("Ver todas as notificações", key="btn_reset_filter", type="tertiary", use_container_width=True):
                    st.session_state.notifications_filter = "todas"
                    st.rerun()
        return

    # 8. Renderizar cards de notificação usando st.container(border=True)
    for n in filtered:
        nid = n["id"]
        ntype = n.get("type", "info")
        ncat = n.get("category", "reserva")
        is_read = n.get("read", False)
        title = n.get("title", "")
        message = n.get("message", n.get("body", ""))
        date_str = n.get("date", "")

        t_config = TYPE_CONFIG.get(ntype, TYPE_CONFIG["info"])
        c_config = CATEGORY_CONFIG.get(ncat, CATEGORY_CONFIG["reserva"])

        card_key = f"rf_notif_unread_{nid}" if not is_read else f"rf_notif_card_{nid}"

        with st.container(border=True, key=card_key):
            if not is_read:
                col_t, col_d = st.columns([0.97, 0.03], vertical_alignment="center")
                with col_t:
                    st.markdown(f'<div class="rf-notif-title">{esc(title)}</div>', unsafe_allow_html=True)
                with col_d:
                    st.markdown('<div class="rf-notif-dot"></div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="rf-notif-title">{esc(title)}</div>', unsafe_allow_html=True)

            st.markdown(f'<div class="rf-notif-message">{esc(message)}</div>', unsafe_allow_html=True)
            st.caption(date_str)

            st.divider()

            # Botões de Ação DENTRO do card
            col_act_left, col_act_right = st.columns([4, 1], vertical_alignment="center")

            with col_act_left:
                if not is_read:
                    if st.button("✓ Marcar como lida", key=f"btn_read_{nid}", type="tertiary"):
                        _mark_read(nid)
                        st.rerun()

            with col_act_right:
                if st.button("🗑 Excluir", key=f"btn_del_{nid}", type="tertiary"):
                    _delete_notification(nid)
                    st.rerun()

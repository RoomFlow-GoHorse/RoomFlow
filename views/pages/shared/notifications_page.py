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
        "svg": """<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#16A34A" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>""",
        "bg": "#DCFCE7",
        "badge_bg": "#DCFCE7",
        "badge_color": "#15803D",
        "badge_label": "Sucesso",
    },
    "danger": {
        "svg": """<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#DC2626" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>""",
        "bg": "#FEE2E2",
        "badge_bg": "#FEE2E2",
        "badge_color": "#B91C1C",
        "badge_label": "Alerta",
    },
    "warning": {
        "svg": """<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#D97706" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>""",
        "bg": "#FEF3C7",
        "badge_bg": "#FEF3C7",
        "badge_color": "#B45309",
        "badge_label": "Atenção",
    },
    "info": {
        "svg": """<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#0284C7" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>""",
        "bg": "#E0F2FE",
        "badge_bg": "#E0F2FE",
        "badge_color": "#0369A1",
        "badge_label": "Informação",
    },
}

CATEGORY_CONFIG = {
    "reserva": {
        "label": "Reserva",
        "svg": """<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>""",
    },
    "alteracao": {
        "label": "Alteração",
        "svg": """<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 17H4M4 17l4-4M4 17l4 4M4 7h16M20 7l-4-4M20 7l-4 4"/></svg>""",
    },
    "conflito": {
        "label": "Conflito",
        "svg": """<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>""",
    },
}


# =========================================================
# ESTILOS VISUAIS DA PÁGINA
# =========================================================

def _render_styles():
    st.html(
        """
        <style>
            .rf-notif-container {
                max-width: 768px;
                margin: 0 auto;
            }

            .rf-notif-item {
                position: relative;
                display: flex;
                align-items: flex-start;
                gap: 16px;
                border-radius: 12px;
                padding: 16px;
                margin-bottom: 12px;
                transition: all 0.2s ease;
            }

            .rf-notif-item.unread {
                border: 1px solid rgba(109, 40, 217, 0.25);
                background-color: #F5F3FF;
            }

            .rf-notif-item.read {
                border: 1px solid #E4E1DB;
                background-color: #FFFFFF;
            }

            .rf-notif-unread-bar {
                position: absolute;
                left: 0;
                top: 12px;
                bottom: 12px;
                width: 4px;
                border-radius: 0 4px 4px 0;
                background-color: #6D28D9;
            }

            .rf-notif-icon-box {
                width: 40px;
                height: 40px;
                border-radius: 10px;
                display: flex;
                align-items: center;
                justify-content: center;
                flex-shrink: 0;
            }

            .rf-notif-content {
                flex: 1;
                min-width: 0;
            }

            .rf-notif-header {
                display: flex;
                flex-direction: column;
                gap: 6px;
            }

            @media (min-width: 640px) {
                .rf-notif-header {
                    flex-direction: row;
                    align-items: flex-start;
                    justify-content: space-between;
                }
            }

            .rf-notif-title-group {
                display: flex;
                align-items: center;
                gap: 8px;
                min-width: 0;
            }

            .rf-notif-title {
                font-size: 14px;
                font-weight: 600;
                color: #1C1C2E;
                margin: 0;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }

            .rf-notif-dot {
                width: 6px;
                height: 6px;
                border-radius: 50%;
                background-color: #6D28D9;
                flex-shrink: 0;
            }

            .rf-notif-meta {
                display: flex;
                align-items: center;
                gap: 8px;
                flex-shrink: 0;
            }

            .rf-notif-category {
                display: flex;
                align-items: center;
                gap: 4px;
                font-size: 11px;
                color: #71717A;
            }

            .rf-notif-badge {
                display: inline-flex;
                align-items: center;
                padding: 2px 8px;
                border-radius: 999px;
                font-size: 11px;
                font-weight: 600;
            }

            .rf-notif-message {
                margin: 6px 0 0 0;
                font-size: 13.5px;
                line-height: 1.5;
                color: #52525B;
            }

            .rf-notif-date {
                margin: 8px 0 0 0;
                font-size: 11px;
                color: #A1A1AA;
            }

            /* Container de Ações dentro do Streamlit */
            .st-key-rf_notif_actions {
                margin-top: 10px !important;
            }

            .st-key-rf_notif_actions button {
                padding: 0 !important;
                background: transparent !important;
                border: none !important;
                font-size: 12px !important;
                font-weight: 500 !important;
                box-shadow: none !important;
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
        </style>
        """
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
        st.html(
            """
            <div style="padding: 64px 20px; text-align: center; background: #FFFFFF; border: 1px solid #E4E1DB; border-radius: 12px; margin-top: 16px;">
                <div style="width: 48px; height: 48px; border-radius: 50%; background: #F4F4F5; display: flex; align-items: center; justify-content: center; margin: 0 auto 12px auto;">
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#71717A" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path><path d="M13.73 21a2 2 0 0 1-3.46 0"></path></svg>
                </div>
                <p style="font-size: 14px; font-weight: 600; color: #1C1C2E; margin: 0 0 4px 0;">
                    Faça login para visualizar suas notificações
                </p>
                <p style="font-size: 12px; color: #71717A; margin: 0;">
                    As notificações são específicas para cada perfil.
                </p>
            </div>
            """
        )
        return

    role = user.get("role", "participante")

    # 1. Filtros disponíveis para o perfil
    available_filters = FILTERS_BY_ROLE.get(role, FILTERS_BY_ROLE["participante"])
    available_filter_ids = {f["id"] for f in available_filters}

    # Controle do filtro no session_state
    if "notifications_filter" not in st.session_state or st.session_state.notifications_filter not in available_filter_ids:
        st.session_state.notifications_filter = "todas"

    current_filter = st.session_state.notifications_filter

    # 2. Filtrar notificações destinadas ao usuário (ignorando a categoria "sistema")
    all_notifications = st.session_state.get("notifications", [])
    user_notifications = [
        item
        for item in all_notifications
        if item.get("category") != "sistema" and role in item.get("audiences", [])
    ]

    # Contagem de não lidas
    unread_count = sum(not n.get("read", False) for n in user_notifications)

    # 3. Cabeçalho dinâmico
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

    # 4. Cálculo dos contadores por filtro
    counts = {
        "todas": len(user_notifications),
        "nao-lidas": sum(not n.get("read", False) for n in user_notifications),
        "reservas": sum(n.get("category") == "reserva" for n in user_notifications),
        "alteracoes": sum(n.get("category") == "alteracao" for n in user_notifications),
        "conflitos": sum(n.get("category") == "conflito" for n in user_notifications),
    }

    # Renderizar barra de filtros
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

    st.write("")

    # 5. Filtrar notificações pelo filtro selecionado
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

    # 6. Exibição da Lista ou Estado Vazio
    if not filtered:
        st.html(
            f"""
            <div style="padding: 64px 20px; text-align: center; background: #FFFFFF; border: 1px solid #E4E1DB; border-radius: 12px; margin-top: 12px;">
                <div style="width: 48px; height: 48px; border-radius: 50%; background: #F4F4F5; display: flex; align-items: center; justify-content: center; margin: 0 auto 12px auto;">
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#71717A" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path><path d="M13.73 21a2 2 0 0 1-3.46 0"></path></svg>
                </div>
                <p style="font-size: 14px; font-weight: 600; color: #1C1C2E; margin: 0 0 4px 0;">
                    Nenhuma notificação encontrada
                </p>
                <p style="font-size: 12px; color: #71717A; margin: 0;">
                    Não há notificações para o filtro selecionado.
                </p>
            </div>
            """
        )
        if current_filter != "todas":
            st.write("")
            col_reset_center = st.columns([1, 2, 1])
            with col_reset_center[1]:
                if st.button("Ver todas as notificações", key="btn_reset_filter", type="tertiary", use_container_width=True):
                    st.session_state.notifications_filter = "todas"
                    st.rerun()
        return

    # Renderizar itens de notificação
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

        card_class = "read" if is_read else "unread"
        unread_bar_html = '<div class="rf-notif-unread-bar"></div>' if not is_read else ''
        unread_dot_html = '<span class="rf-notif-dot"></span>' if not is_read else ''

        # Card HTML visual
        st.html(
            f"""
            <div class="rf-notif-item {card_class}">
                {unread_bar_html}
                <div class="rf-notif-icon-box" style="background-color: {t_config['bg']};">
                    {t_config['svg']}
                </div>
                <div class="rf-notif-content">
                    <div class="rf-notif-header">
                        <div class="rf-notif-title-group">
                            <h3 class="rf-notif-title">{esc(title)}</h3>
                            {unread_dot_html}
                        </div>
                        <div class="rf-notif-meta">
                            <span class="rf-notif-category">
                                {c_config['svg']}
                                {esc(c_config['label'])}
                            </span>
                            <span class="rf-notif-badge" style="background-color: {t_config['badge_bg']}; color: {t_config['badge_color']};">
                                {esc(t_config['badge_label'])}
                            </span>
                        </div>
                    </div>
                    <p class="rf-notif-message">{esc(message)}</p>
                    <p class="rf-notif-date">{esc(date_str)}</p>
                </div>
            </div>
            """
        )

        # Botões de Ação para o item (Marcar como lida / Excluir)
        col_actions_left, col_actions_right = st.columns([4, 1])

        with col_actions_left:
            if not is_read:
                if st.button("✓ Marcar como lida", key=f"btn_read_{nid}", type="tertiary"):
                    _mark_read(nid)
                    st.rerun()

        with col_actions_right:
            if st.button("🗑 Excluir", key=f"btn_del_{nid}", type="tertiary"):
                _delete_notification(nid)
                st.rerun()

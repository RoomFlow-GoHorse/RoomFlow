import streamlit as st

from views.components.ui_components import esc, page_header


# =========================================================
# MOCK DE DADOS - HISTÓRICO DE ALTERAÇÕES
# =========================================================

CHANGES_LOG_DATA = [
    {
        "id": "chg1",
        "type": "espaco",
        "event": "Aula de Metodologia",
        "date": "21 de agosto de 2026",
        "time": "08:30",
        "from": "Sala 204",
        "to": "Sala 101",
        "reason": "Ajuste na alocação de turmas para comportar maior capacidade de alunos.",
    },
    {
        "id": "chg2",
        "type": "horario",
        "event": "Workshop de Pesquisa",
        "date": "20 de agosto de 2026",
        "time": "14:15",
        "from": "13:30 – 16:30",
        "to": "14:00 – 17:00",
        "reason": "Solicitação do palestrante convidado para adequação de horário de chegada.",
    },
    {
        "id": "chg3",
        "type": "cancelamento",
        "event": "Monitoria de Programação",
        "date": "19 de agosto de 2026",
        "time": "11:00",
        "from": "Sessão agendada no Laboratório de Informática 1.",
        "to": "—",
        "reason": "Manutenção preventiva emergencial nos equipamentos do laboratório.",
    },
    {
        "id": "chg4",
        "type": "espaco",
        "event": "Banca de TCC",
        "date": "18 de agosto de 2026",
        "time": "16:00",
        "from": "Auditório A",
        "to": "Sala de Reuniões B",
        "reason": "Remanejamento para espaço com equipamento de videoconferência dedicado.",
    },
]

TYPE_STYLES = {
    "espaco": {
        "label": "Alteração de espaço",
        "icon_symbol": "📍",
        "border_color": "#6D28D9",
        "icon_bg": "#EDE9FE",
        "icon_color": "#6D28D9",
        "badge_bg": "#EDE9FE",
        "badge_color": "#6D28D9",
    },
    "horario": {
        "label": "Alteração de horário",
        "icon_symbol": "🕒",
        "border_color": "#B45309",
        "icon_bg": "#FEF3C7",
        "icon_color": "#B45309",
        "badge_bg": "#FEF3C7",
        "badge_color": "#B45309",
    },
    "cancelamento": {
        "label": "Cancelamento",
        "icon_symbol": "❌",
        "border_color": "#DC2626",
        "icon_bg": "#FEE2E2",
        "icon_color": "#DC2626",
        "badge_bg": "#FEE2E2",
        "badge_color": "#DC2626",
    },
}


# =========================================================
# ESTILOS DA PÁGINA ALTERAÇÕES
# =========================================================

def _render_styles():
    st.html(
        """
        <style>
            .rf-summary-card {
                background: #FFFFFF;
                border: 1px solid #E4E1DB;
                border-radius: 12px;
                padding: 16px;
                display: flex;
                align-items: center;
                gap: 14px;
            }

            .rf-summary-icon {
                width: 42px;
                height: 42px;
                border-radius: 12px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 18px;
                flex-shrink: 0;
            }

            .rf-change-card {
                background: #FFFFFF;
                border: 1px solid #E4E1DB;
                border-radius: 12px;
                padding: 20px;
                margin-bottom: 14px;
                transition: transform 0.15s ease, box-shadow 0.15s ease;
            }

            .rf-change-card:hover {
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
            }

            .rf-comp-box {
                background: #F8F7F4;
                border: 1px solid #E4E1DB;
                border-radius: 10px;
                padding: 12px;
            }

            .rf-comp-box.new-brand {
                background: #F5F3FF;
                border-color: rgba(109, 40, 217, 0.3);
            }

            .rf-comp-box.new-mustard {
                background: #FEF3C7;
                border-color: rgba(180, 83, 9, 0.3);
            }
        </style>
        """
    )


# =========================================================
# PÁGINA PRINCIPAL
# =========================================================

def alteracoes(user: dict):
    _render_styles()

    # 1. Cabeçalho da Página
    page_header(
        "Alterações",
        "Acompanhe mudanças recentes nas suas reservas e na sua agenda.",
    )

    changes = CHANGES_LOG_DATA
    total_count = len(changes)
    time_count = len([c for c in changes if c.get("type") == "horario"])
    cancel_count = len([c for c in changes if c.get("type") == "cancelamento"])

    # 2. Resumo de Métricas (3 Cards)
    c_m1, c_m2, c_m3 = st.columns(3)

    with c_m1:
        st.html(
            f"""
            <div class="rf-summary-card">
                <div class="rf-summary-icon" style="background:#EDE9FE; color:#6D28D9;">
                    ⚠️
                </div>
                <div>
                    <p style="font-size:12px; color:#71717A; margin:0;">Alterações recentes</p>
                    <p style="font-size:20px; font-weight:700; color:#1C1C2E; margin:2px 0 0 0;">{total_count}</p>
                </div>
            </div>
            """
        )

    with c_m2:
        st.html(
            f"""
            <div class="rf-summary-card">
                <div class="rf-summary-icon" style="background:#FEF3C7; color:#B45309;">
                    🕒
                </div>
                <div>
                    <p style="font-size:12px; color:#71717A; margin:0;">Mudanças de horário</p>
                    <p style="font-size:20px; font-weight:700; color:#1C1C2E; margin:2px 0 0 0;">{time_count}</p>
                </div>
            </div>
            """
        )

    with c_m3:
        st.html(
            f"""
            <div class="rf-summary-card">
                <div class="rf-summary-icon" style="background:#FEE2E2; color:#DC2626;">
                    ❌
                </div>
                <div>
                    <p style="font-size:12px; color:#71717A; margin:0;">Cancelamentos</p>
                    <p style="font-size:20px; font-weight:700; color:#1C1C2E; margin:2px 0 0 0;">{cancel_count}</p>
                </div>
            </div>
            """
        )

    st.markdown('<div style="height:24px;"></div>', unsafe_allow_html=True)

    # 3. Cabeçalho da Lista
    col_hdr_left, col_hdr_right = st.columns([3, 1], vertical_alignment="center")

    with col_hdr_left:
        st.html(
            """
            <div>
                <h2 style="font-size:15px; font-weight:600; color:#1C1C2E; margin:0 0 2px 0;">Histórico de alterações</h2>
                <p style="font-size:12px; color:#71717A; margin:0;">Confira os detalhes de cada mudança.</p>
            </div>
            """
        )

    with col_hdr_right:
        st.html(
            """
            <div style="text-align:right; font-size:12px; color:#71717A;">
                📅 Mais recentes primeiro
            </div>
            """
        )

    st.markdown('<div style="height:12px;"></div>', unsafe_allow_html=True)

    # 4. Lista de Alterações
    if not changes:
        st.html(
            """
            <div style="background:#FFFFFF; border:1px dashed #E4E1DB; border-radius:12px; padding:48px; text-align:center;">
                <div style="width:48px; height:48px; border-radius:50%; background:#F5F3FF; color:#6D28D9; display:inline-flex; align-items:center; justify-content:center; font-size:20px; margin-bottom:12px;">
                    ✅
                </div>
                <h3 style="font-size:14px; font-weight:600; color:#1C1C2E; margin:0 0 4px 0;">Nenhuma alteração</h3>
                <p style="font-size:12px; color:#71717A; margin:0;">Não existem mudanças recentes nas suas reservas.</p>
            </div>
            """
        )
    else:
        for chg in changes:
            chg_type = chg.get("type", "espaco")
            style = TYPE_STYLES.get(chg_type, TYPE_STYLES["espaco"])

            # Renderização do topo do card de alteração
            st.html(
                f"""
                <div class="rf-change-card" style="border-left: 4px solid {style['border_color']};">
                    <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:16px; margin-bottom:16px;">
                        <div style="display:flex; align-items:flex-start; gap:12px;">
                            <div style="width:40px; height:40px; border-radius:12px; background:{style['icon_bg']}; color:{style['icon_color']}; display:flex; align-items:center; justify-content:center; font-size:18px; flex-shrink:0;">
                                {style['icon_symbol']}
                            </div>
                            <div>
                                <h3 style="font-size:14px; font-weight:600; color:#1C1C2E; margin:0 0 4px 0;">{esc(chg['event'])}</h3>
                                <p style="font-size:12px; color:#71717A; margin:0;">{esc(chg['date'])} &bull; {esc(chg['time'])}</p>
                            </div>
                        </div>
                        <span style="padding:3px 10px; border-radius:999px; background:{style['badge_bg']}; color:{style['badge_color']}; font-size:11px; font-weight:600; flex-shrink:0;">
                            {esc(style['label'])}
                        </span>
                    </div>
                """
            )

            # Comparação (Anterior -> Novo) ou Alerta de Cancelamento
            if chg_type in {"espaco", "horario"}:
                is_brand = chg_type == "espaco"
                icon = "📍" if is_brand else "🕒"
                new_class = "new-brand" if is_brand else "new-mustard"
                accent_color = "#6D28D9" if is_brand else "#B45309"

                c_prev, c_arrow, c_next = st.columns([4, 1, 4], vertical_alignment="center")

                with c_prev:
                    st.html(
                        f"""
                        <div class="rf-comp-box">
                            <p style="font-size:10px; font-weight:700; text-transform:uppercase; color:#71717A; margin:0 0 4px 0;">Anterior</p>
                            <p style="font-size:13px; color:#71717A; text-decoration:line-through; margin:0;">{icon} {esc(chg['from'])}</p>
                        </div>
                        """
                    )

                with c_arrow:
                    st.html(
                        f"""
                        <div style="text-align:center; font-size:18px; color:{accent_color}; font-weight:700;">
                            &rarr;
                        </div>
                        """
                    )

                with c_next:
                    st.html(
                        f"""
                        <div class="rf-comp-box {new_class}">
                            <p style="font-size:10px; font-weight:700; text-transform:uppercase; color:{accent_color}; margin:0 0 4px 0;">Novo</p>
                            <p style="font-size:13px; font-weight:700; color:{accent_color}; margin:0;">{icon} {esc(chg['to'])}</p>
                        </div>
                        """
                    )

            elif chg_type == "cancelamento":
                st.html(
                    f"""
                    <div style="background:#FEF2F2; border:1px solid rgba(220,38,38,0.2); border-radius:10px; padding:12px; margin-bottom:16px;">
                        <p style="font-size:12px; font-weight:700; color:#DC2626; margin:0 0 4px 0;">❌ Reserva cancelada</p>
                        <p style="font-size:13px; color:#1C1C2E; margin:0;">{esc(chg['from'])}</p>
                    </div>
                    """
                )

            # Motivo da Alteração
            st.html(
                f"""
                <div style="border-top:1px solid #E4E1DB; padding-top:12px; margin-top:16px; display:flex; align-items:flex-start; gap:8px;">
                    <span style="font-size:14px; color:#16A34A;">✔</span>
                    <div>
                        <p style="font-size:10px; font-weight:700; text-transform:uppercase; color:#71717A; margin:0 0 2px 0;">Motivo da alteração</p>
                        <p style="font-size:13px; color:#1C1C2E; margin:0; line-height:1.5;">{esc(chg['reason'])}</p>
                    </div>
                </div>
                </div>
                """
            )

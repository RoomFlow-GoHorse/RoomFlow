import streamlit as st

from controllers import mock_data_service
from controllers.app_state_service import go
from views.components.ui_components import esc


# =========================================================
# DADOS DE DEMONSTRAÇÃO DO FIGMA
# =========================================================

DEMO_AGENDA_EVENTS = [
    {
        "id": "e1",
        "title": "Aula de Metodologia",
        "startTime": "08:00",
        "endTime": "10:00",
        "space": "Sala 101",
        "location": "Bloco A - 1º andar",
        "color": "#6D28D9",
        "weekday": "Sex",
        "date": "21/08",
    },
    {
        "id": "e2",
        "title": "Banca de TCC",
        "startTime": "09:30",
        "endTime": "11:00",
        "space": "Sala 204",
        "location": "Bloco B - 2º andar",
        "color": "#B45309",
        "weekday": "Sex",
        "date": "21/08",
    },
    {
        "id": "e3",
        "title": "Workshop de Pesquisa",
        "startTime": "14:00",
        "endTime": "17:00",
        "space": "Auditório Principal",
        "location": "Bloco Central",
        "color": "#16A34A",
        "weekday": "Sáb",
        "date": "22/08",
    },
    {
        "id": "e4",
        "title": "Reunião de Coordenação",
        "startTime": "10:00",
        "endTime": "11:30",
        "space": "Sala de Reuniões B",
        "location": "Administrativo",
        "color": "#2563EB",
        "weekday": "Seg",
        "date": "24/08",
    },
]

DEMO_CHANGES_LOG = [
    {
        "id": "c1",
        "event": "Aula de Metodologia",
        "change": "Alteração de sala para acomodar a turma.",
        "from": "Sala 204",
        "to": "Sala 101",
        "type": "alteracao",
    },
    {
        "id": "c2",
        "event": "Monitoria de Programação",
        "change": "Sessão cancelada por indisponibilidade do laboratório.",
        "from": None,
        "to": "—",
        "type": "cancelamento",
    },
    {
        "id": "c3",
        "event": "Workshop de Pesquisa",
        "change": "Ajuste no horário de início.",
        "from": "13:30",
        "to": "14:00",
        "type": "alteracao",
    },
]


# =========================================================
# ESTILOS DA PÁGINA
# =========================================================

def _render_styles():
    st.html(
        """
        <style>
            .st-key-rf_next_activity_card {
                background: #1C1C2E !important;
                border: none !important;
                border-radius: 16px !important;
                padding: 24px !important;
                margin-bottom: 28px !important;
            }

            .st-key-rf_next_activity_card button {
                background: rgba(255, 255, 255, 0.12) !important;
                color: #FFFFFF !important;
                border: none !important;
                border-radius: 8px !important;
                padding: 8px 16px !important;
                font-size: 13px !important;
                font-weight: 500 !important;
                white-space: nowrap !important;
                transition: background 0.2s ease !important;
            }

            .st-key-rf_next_activity_card button:hover {
                background: rgba(255, 255, 255, 0.22) !important;
                color: #FFFFFF !important;
            }

            .st-key-rf_agenda_card,
            .st-key-rf_changes_card {
                background: #FFFFFF !important;
                border: 1px solid #E4E1DB !important;
                border-radius: 12px !important;
                padding: 20px !important;
            }

            .st-key-rf_agenda_card button[kind="tertiary"],
            .st-key-rf_changes_card button[kind="tertiary"] {
                color: #6D28D9 !important;
                font-size: 12px !important;
                font-weight: 600 !important;
                padding: 0 !important;
                background: transparent !important;
                border: none !important;
                box-shadow: none !important;
            }

            .st-key-rf_agenda_card button[kind="tertiary"]:hover,
            .st-key-rf_changes_card button[kind="tertiary"]:hover {
                color: #5B21B6 !important;
                text-decoration: underline !important;
            }
        </style>
        """
    )


# =========================================================
# NAVEGAÇÃO INTERNA
# =========================================================

def _navigate(page: str) -> None:
    go(page)
    st.rerun()


# =========================================================
# PÁGINA PRINCIPAL
# =========================================================

def dashboard(user: dict):
    _render_styles()

    # Nome do usuário e data de referência
    first_name = user["name"].split()[0] if user and user.get("name") else "Participante"

    # 1. Saudação
    st.html(
        f"""
        <div style="margin-bottom: 28px;">
            <h1 style="font-size: 22px; font-weight: 600; color: #1C1C2E; margin: 0 0 4px 0; letter-spacing: -0.01em;">
                Olá, {esc(first_name)}!
            </h1>
            <p style="font-size: 14px; color: #71717A; margin: 0;">
                Sexta-feira, 21 de agosto de 2026
            </p>
        </div>
        """
    )

    # Obter eventos e alterações do mock_data_service ou do conjunto demo
    agenda_list = DEMO_AGENDA_EVENTS
    upcoming = agenda_list[:3]
    changes_list = DEMO_CHANGES_LOG[:3]

    # 2. Próxima Atividade (Banner em Destaque)
    if upcoming:
        next_ev = upcoming[0]
        with st.container(key="rf_next_activity_card"):
            col_info, col_btn = st.columns([4, 1], vertical_alignment="center")

            with col_info:
                st.html(
                    f"""
                    <div>
                        <p style="font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; color: rgba(255, 255, 255, 0.5); margin: 0 0 6px 0;">
                            Próxima atividade
                        </p>
                        <p style="font-size: 18px; font-weight: 600; color: #FFFFFF; margin: 0 0 8px 0;">
                            {esc(next_ev['title'])}
                        </p>
                        <div style="display: flex; align-items: center; gap: 16px; font-size: 13px; color: rgba(255, 255, 255, 0.75);">
                            <span style="display: inline-flex; align-items: center; gap: 5px;">
                                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
                                {esc(next_ev['startTime'])}–{esc(next_ev['endTime'])}
                            </span>
                            <span style="display: inline-flex; align-items: center; gap: 5px;">
                                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path><circle cx="12" cy="10" r="3"></circle></svg>
                                {esc(next_ev['space'])}
                            </span>
                        </div>
                        <p style="font-size: 12px; color: rgba(255, 255, 255, 0.5); margin: 6px 0 0 0;">
                            {esc(next_ev['location'])}
                        </p>
                    </div>
                    """
                )

            with col_btn:
                if st.button("Como chegar", key="btn_como_chegar"):
                    _navigate("localizar")

    # 3. Conteúdo Principal (2 Colunas)
    col_agenda, col_changes = st.columns([2, 1], gap="medium")

    # =====================================================
    # MINHA AGENDA
    # =====================================================
    with col_agenda:
        with st.container(key="rf_agenda_card"):
            hdr_left, hdr_right = st.columns([3, 1], vertical_alignment="center")

            with hdr_left:
                st.html(
                    '<h2 style="font-size: 14px; font-weight: 600; color: #1C1C2E; margin: 0 0 16px 0;">Minha agenda</h2>'
                )

            with hdr_right:
                if st.button("Ver calendário →", key="btn_ver_agenda", type="tertiary"):
                    _navigate("agenda")

            # Lista de eventos
            for ev in agenda_list:
                st.html(
                    f"""
                    <div style="display: flex; align-items: center; gap: 12px; padding: 12px; border: 1px solid #E4E1DB; border-radius: 8px; margin-bottom: 10px; background: #FFFFFF;">
                        <div style="width: 4px; height: 40px; border-radius: 999px; flex-shrink: 0; background: {ev['color']};"></div>
                        <div style="flex: 1; min-width: 0;">
                            <p style="font-size: 14px; font-weight: 500; color: #1C1C2E; margin: 0 0 2px 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                                {esc(ev['title'])}
                            </p>
                            <div style="display: flex; align-items: center; gap: 8px; font-size: 12px; color: #71717A;">
                                <span style="display: inline-flex; align-items: center; gap: 4px;">
                                    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
                                    {esc(ev['startTime'])}–{esc(ev['endTime'])}
                                </span>
                                <span>·</span>
                                <span style="display: inline-flex; align-items: center; gap: 4px;">
                                    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path><circle cx="12" cy="10" r="3"></circle></svg>
                                    {esc(ev['space'])}
                                </span>
                            </div>
                        </div>
                        <div style="text-align: right; flex-shrink: 0;">
                            <span style="display: inline-block; padding: 2px 8px; border-radius: 4px; background: #F0EEE9; color: #52525B; font-size: 11px; font-weight: 600;">
                                {esc(ev['weekday'])}
                            </span>
                            <p style="font-size: 12px; color: #A1A1AA; margin: 4px 0 0 0;">
                                {esc(ev['date'])}
                            </p>
                        </div>
                    </div>
                    """
                )

    # =====================================================
    # ALTERAÇÕES RECENTES
    # =====================================================
    with col_changes:
        with st.container(key="rf_changes_card"):
            hdr_c_left, hdr_c_right = st.columns([3, 1], vertical_alignment="center")

            with hdr_c_left:
                st.html(
                    '<h2 style="font-size: 14px; font-weight: 600; color: #1C1C2E; margin: 0 0 16px 0;">Alterações recentes</h2>'
                )

            with hdr_c_right:
                if st.button("Ver todas →", key="btn_ver_alteracoes", type="tertiary"):
                    _navigate("alteracoes")

            # Lista de alterações
            for chg in changes_list:
                is_cancel = chg.get("type") == "cancelamento"
                border_color = "rgba(220, 38, 38, 0.2)" if is_cancel else "#FCD34D"
                bg_color = "rgba(254, 226, 226, 0.5)" if is_cancel else "#FEF3C7"

                from_to_html = ""
                if chg.get("from") and chg.get("to") and chg.get("to") != "—":
                    from_to_html = f"""
                    <p style="font-size: 12px; color: #71717A; margin: 4px 0 0 0;">
                        <span style="text-decoration: line-through;">{esc(chg['from'])}</span> &rarr; <strong style="color: #6D28D9;">{esc(chg['to'])}</strong>
                    </p>
                    """

                st.html(
                    f"""
                    <div style="padding: 12px; border-radius: 8px; border: 1px solid {border_color}; background: {bg_color}; margin-bottom: 12px;">
                        <p style="font-size: 12px; font-weight: 600; color: #1C1C2E; margin: 0 0 4px 0;">
                            {esc(chg['event'])}
                        </p>
                        <p style="font-size: 12px; color: #52525B; margin: 0;">
                            {esc(chg['change'])}
                        </p>
                        {from_to_html}
                    </div>
                    """
                )

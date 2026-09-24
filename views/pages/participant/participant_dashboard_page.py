from dataclasses import dataclass
from datetime import date
from typing import List, Optional
import streamlit as st

from controllers.app_state_service import go
from views.components.ui_components import esc, page_header

# =========================================================
# MODELOS DE DADOS (TYPES)
# =========================================================

@dataclass
class AgendaEvent:
    id: str
    title: str
    start_time: str
    end_time: str
    space: str
    location: str
    color: str
    weekday: str
    formatted_date: str
    event_date: date


@dataclass
class ChangeLog:
    id: str
    event_title: str
    description: str
    from_value: Optional[str]
    to_value: Optional[str]
    change_type: str  # 'alteracao' | 'cancelamento'


# =========================================================
# SERVIÇO DE DADOS (MOCK / REPOSITÓRIO)
# =========================================================

def _get_demo_agenda_events() -> List[AgendaEvent]:
    return [
        AgendaEvent(
            id="e1",
            title="Aula de Metodologia",
            start_time="08:00",
            end_time="10:00",
            space="Sala 101",
            location="Bloco A - 1º andar",
            color="#6D28D9",
            weekday="Sex",
            formatted_date="21/08",
            event_date=date(2026, 8, 21),
        ),
        AgendaEvent(
            id="e2",
            title="Banca de TCC",
            start_time="09:30",
            end_time="11:00",
            space="Sala 204",
            location="Bloco B - 2º andar",
            color="#B45309",
            weekday="Sex",
            formatted_date="21/08",
            event_date=date(2026, 8, 21),
        ),
        AgendaEvent(
            id="e3",
            title="Workshop de Pesquisa",
            start_time="14:00",
            end_time="17:00",
            space="Auditório Principal",
            location="Bloco Central",
            color="#16A34A",
            weekday="Sáb",
            formatted_date="22/08",
            event_date=date(2026, 8, 22),
        ),
        AgendaEvent(
            id="e4",
            title="Reunião de Coordenação",
            start_time="10:00",
            end_time="11:30",
            space="Sala de Reuniões B",
            location="Administrativo",
            color="#2563EB",
            weekday="Seg",
            formatted_date="24/08",
            event_date=date(2026, 8, 24),
        ),
    ]


def _get_demo_changes_log() -> List[ChangeLog]:
    return [
        ChangeLog(
            id="c1",
            event_title="Aula de Metodologia",
            description="Alteração de sala para acomodar a turma.",
            from_value="Sala 204",
            to_value="Sala 101",
            change_type="alteracao",
        ),
        ChangeLog(
            id="c2",
            event_title="Monitoria de Programação",
            description="Sessão cancelada por indisponibilidade do laboratório.",
            from_value=None,
            to_value="—",
            change_type="cancelamento",
        ),
        ChangeLog(
            id="c3",
            event_title="Workshop de Pesquisa",
            description="Ajuste no horário de início.",
            from_value="13:30",
            to_value="14:00",
            change_type="alteracao",
        ),
    ]


# =========================================================
# ESTILOS CSS DA PÁGINA
# =========================================================

def _render_styles() -> None:
    st.markdown(
        """
        <style>
            /* Hero Card - Banner da Próxima Atividade */
            .st-key-rf_next_activity_card {
                background: linear-gradient(135deg, var(--brand) 0%, #4C1D95 100%) !important;
                border: none !important;
                border-radius: 16px !important;
                padding: 24px !important;
                margin-bottom: 24px !important;
                color: #FFFFFF !important;
                box-shadow: 0 4px 12px rgba(109, 40, 217, 0.15);
            }

            /* Estilização do Botão "Como chegar" dentro do Banner */
            .st-key-rf_next_activity_card button {
                background-color: rgba(255, 255, 255, 0.18) !important;
                color: #FFFFFF !important;
                border: 1px solid rgba(255, 255, 255, 0.3) !important;
                border-radius: 8px !important;
                font-weight: 600 !important;
                transition: all 0.2s ease !important;
            }

            .st-key-rf_next_activity_card button:hover {
                background-color: rgba(255, 255, 255, 0.3) !important;
                color: #FFFFFF !important;
                border-color: rgba(255, 255, 255, 0.5) !important;
            }

            .st-key-rf_next_activity_card button:active,
            .st-key-rf_next_activity_card button:focus {
                color: #FFFFFF !important;
                box-shadow: none !important;
            }

            /* Containers Genéricos de Cards */
            .st-key-rf_agenda_card,
            .st-key-rf_changes_card {
                background: var(--surface-card) !important;
                border: 1px solid var(--stroke) !important;
                border-radius: 12px !important;
                padding: 20px !important;
                box-shadow: 0 1px 3px rgba(0,0,0,0.02);
            }

            /* Botões tertiary dos cabeçalhos */
            .st-key-rf_agenda_card button[kind="tertiary"],
            .st-key-rf_changes_card button[kind="tertiary"] {
                color: var(--brand) !important;
                font-size: 13px !important;
                font-weight: 600 !important;
                padding: 0 !important;
                background: transparent !important;
                border: none !important;
            }

            .st-key-rf_agenda_card button[kind="tertiary"]:hover,
            .st-key-rf_changes_card button[kind="tertiary"]:hover {
                color: var(--brand-hover) !important;
                text-decoration: underline !important;
            }

            /* Event Card Item */
            .rf-event-item {
                display: flex;
                align-items: center;
                gap: 12px;
                padding: 12px;
                border: 1px solid var(--stroke);
                border-radius: 8px;
                margin-bottom: 10px;
                background: var(--surface-card);
                transition: transform 0.1s ease, border-color 0.1s ease;
            }

            .rf-event-item:hover {
                border-color: var(--brand);
            }

            /* Log de Alteração Item */
            .rf-change-item {
                padding: 12px;
                border-radius: 8px;
                margin-bottom: 10px;
                border: 1px solid transparent;
            }

            .rf-change-item.alteracao {
                background-color: #FEF3C7;
                border-color: #FCD34D;
                color: #78350F;
            }

            .rf-change-item.cancelamento {
                background-color: #FEE2E2;
                border-color: #FCA5A5;
                color: #991B1B;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

# =========================================================
# COMPONENTES AUXILIARES DE RENDERIZAÇÃO
# =========================================================

def _render_hero_banner(event: AgendaEvent) -> None:
    """Renderiza o destaque da próxima atividade."""
    with st.container(key="rf_next_activity_card"):
        col_info, col_btn = st.columns([4, 1], vertical_alignment="center")

        with col_info:
            st.markdown(
                f"""
                <div style="color: #FFFFFF;">
                    <p style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; opacity: 0.7; margin: 0 0 4px 0;">
                        Próxima atividade
                    </p>
                    <h3 style="font-size: 20px; font-weight: 700; margin: 0 0 10px 0; color: #FFFFFF;">
                        {esc(event.title)}
                    </h3>
                    <div style="display: flex; align-items: center; gap: 16px; font-size: 13px; opacity: 0.9;">
                        <span style="display: inline-flex; align-items: center; gap: 6px;">
                            🕒 {esc(event.start_time)} – {esc(event.end_time)}
                        </span>
                        <span style="display: inline-flex; align-items: center; gap: 6px;">
                            📍 {esc(event.space)}
                        </span>
                    </div>
                    <p style="font-size: 12px; opacity: 0.75; margin: 6px 0 0 0;">
                        {esc(event.location)}
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col_btn:
            if st.button("Como chegar", key="btn_como_chegar", use_container_width=True):
                go("localizar")
                st.rerun()


def _render_event_item(event: AgendaEvent) -> None:
    """Renderiza a linha do evento na lista da agenda."""
    st.markdown(
        f"""
        <div class="rf-event-item">
            <div style="width: 4px; height: 38px; border-radius: 4px; flex-shrink: 0; background: {event.color};"></div>
            <div style="flex: 1; min-width: 0;">
                <p style="font-size: 14px; font-weight: 600; color: var(--graphite); margin: 0 0 2px 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                    {esc(event.title)}
                </p>
                <div style="display: flex; align-items: center; gap: 8px; font-size: 12px; color: var(--graphite-muted);">
                    <span>🕒 {esc(event.start_time)}–{esc(event.end_time)}</span>
                    <span>•</span>
                    <span>📍 {esc(event.space)}</span>
                </div>
            </div>
            <div style="text-align: right; flex-shrink: 0;">
                <span style="display: inline-block; padding: 2px 8px; border-radius: 4px; background: var(--surface-alt); color: var(--graphite-soft); font-size: 11px; font-weight: 600;">
                    {esc(event.weekday)}
                </span>
                <p style="font-size: 12px; color: var(--graphite-muted); margin: 2px 0 0 0;">
                    {esc(event.formatted_date)}
                </p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_change_item(change: ChangeLog) -> None:
    """Renderiza um cartão de notificação/alteração."""
    from_to_html = ""
    if change.from_value and change.to_value and change.to_value != "—":
        from_to_html = f"""
        <p style="font-size: 12px; margin: 4px 0 0 0;">
            <span style="text-decoration: line-through; opacity: 0.7;">{esc(change.from_value)}</span>
            &rarr; <strong>{esc(change.to_value)}</strong>
        </p>
        """

    st.markdown(
        f"""
        <div class="rf-change-item {change.change_type}">
            <p style="font-size: 13px; font-weight: 700; margin: 0 0 2px 0;">
                {esc(change.event_title)}
            </p>
            <p style="font-size: 12px; margin: 0; opacity: 0.95;">
                {esc(change.description)}
            </p>
            {from_to_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# PÁGINA PRINCIPAL
# =========================================================

def dashboard(user: dict) -> None:
    _render_styles()

    # Informações do usuário
    user_name = user.get("name", "Participante") if user else "Participante"
    first_name = user_name.split()[0]

    # Cabeçalho Padrão
    page_header(
        f"Olá, {first_name}!",
        "Sexta-feira, 21 de agosto de 2026",
    )

    # Carregamento de dados
    agenda_events = _get_demo_agenda_events()
    changes_log = _get_demo_changes_log()

    # Banner Destaque (Próxima atividade)
    if agenda_events:
        _render_hero_banner(agenda_events[0])

    # Conteúdo Principal: Duas Colunas
    col_agenda, col_changes = st.columns([2, 1], gap="medium")

    # 1. Coluna de Agenda
    with col_agenda:
        with st.container(key="rf_agenda_card"):
            hdr_left, hdr_right = st.columns([3, 1], vertical_alignment="center")

            with hdr_left:
                st.markdown('<h3 style="font-size: 16px; font-weight: 600; color: var(--graphite); margin: 0 0 16px 0;">Minha agenda</h3>', unsafe_allow_html=True)

            with hdr_right:
                if st.button("Ver tudo", key="btn_ver_agenda", type="tertiary"):
                    go("agenda")
                    st.rerun()

            for event in agenda_events:
                _render_event_item(event)

    # 2. Coluna de Alterações Recentes
    with col_changes:
        with st.container(key="rf_changes_card"):
            hdr_c_left, hdr_c_right = st.columns([3, 1], vertical_alignment="center")

            with hdr_c_left:
                st.markdown('<h3 style="font-size: 16px; font-weight: 600; color: var(--graphite); margin: 0 0 16px 0;">Alterações recentes</h3>', unsafe_allow_html=True)

            with hdr_c_right:
                if st.button("Ver todas", key="btn_ver_alteracoes", type="tertiary"):
                    go("notificacoes")
                    st.rerun()

            for change in changes_log:
                _render_change_item(change)
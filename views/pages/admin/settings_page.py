import streamlit as st
from datetime import time

from controllers import mock_data_service
from controllers.app_state_service import set_toast
from views.components.ui_components import page_header


# =========================================================
# CONSTANTES
# =========================================================

CATEGORIES = [
    ("geral",         "Informações gerais",   ":material/info:"),
    ("politicas",     "Políticas de reserva",  ":material/policy:"),
    ("conflitos",     "Regras de conflito",    ":material/gavel:"),
    ("notificacoes",  "Notificações",          ":material/notifications:"),
]

NOTIFICATION_OPTIONS = [
    ("reserva_aprovada",    "Reserva aprovada",        "Notificar o solicitante quando sua reserva for aprovada"),
    ("reserva_rejeitada",   "Reserva rejeitada",       "Notificar o solicitante quando sua reserva for rejeitada"),
    ("conflito_detectado",  "Conflito detectado",      "Notificar administrador e solicitantes envolvidos"),
    ("alteracao_espaco",    "Alteração de espaço",     "Notificar participantes quando um espaço for alterado"),
    ("cancelamento_reserva","Cancelamento de reserva", "Notificar participantes sobre cancelamentos"),
    ("lembrete_reserva",    "Lembrete de reserva",     "Enviar lembrete 1 hora antes da atividade"),
]


# =========================================================
# CATEGORIAS — conteúdo por seção
# =========================================================

def _section_geral(institution_name):
    st.text_input("Nome da instituição",    value=institution_name,                      key="cfg_nome")
    st.text_input("Endereço",               value="Av. Principal, 1000 — São Paulo, SP", key="cfg_endereco")

    col1, col2 = st.columns(2)
    col1.text_input("Contato principal", value="admin@instituicao.edu.br", key="cfg_contato")
    col2.text_input("Telefone",          value="(11) 9999-9999",           key="cfg_telefone")

    st.selectbox(
        "Fuso horário",
        options=[
            "America/Sao_Paulo (UTC-3)",
            "America/Manaus (UTC-4)",
            "America/Fortaleza (UTC-3)",
        ],
        key="cfg_fuso",
    )


def _section_politicas():
    col1, col2 = st.columns(2)
    col1.number_input("Antecedência mínima de reserva", min_value=1, value=1, key="cfg_min_ant")
    col2.selectbox("Unidade (mínima)", ["dias", "horas"], key="cfg_min_unit")

    col3, col4 = st.columns(2)
    col3.number_input("Antecedência máxima de reserva", min_value=1, value=60, key="cfg_max_ant")
    col4.selectbox("Unidade (máxima)", ["dias", "semanas"], key="cfg_max_unit")

    col5, col6 = st.columns(2)
    col5.time_input("Horário de início permitido", value=time(7, 0),  key="cfg_hora_inicio")
    col6.time_input("Horário de fim permitido",    value=time(22, 0), key="cfg_hora_fim")

    st.selectbox(
        "Aprovação automática",
        options=[
            "Desativada — todas as reservas precisam de aprovação",
            "Ativada — aprovação automática para solicitações sem conflito",
        ],
        key="cfg_aprovacao",
    )

    st.checkbox(
        "Exigir justificativa em todas as solicitações",
        value=True,
        key="cfg_justificativa",
    )


def _section_conflitos():
    st.selectbox(
        "Critério de resolução padrão",
        options=[
            "Por prioridade da atividade",
            "Por ordem de chegada (FIFO)",
            "Por cargo do solicitante",
            "Decisão manual obrigatória",
        ],
        key="cfg_criterio",
    )

    st.selectbox(
        "Notificação em caso de conflito",
        options=[
            "Notificar administrador imediatamente",
            "Aguardar 1 hora antes de notificar",
            "Apenas registrar no histórico",
        ],
        key="cfg_notif_conflito",
    )

    st.checkbox(
        "Sugerir espaços alternativos automaticamente ao detectar conflito",
        value=True,
        key="cfg_sugestao",
    )


def _section_notificacoes():
    for key, label, description in NOTIFICATION_OPTIONS:
        with st.container(border=True):
            st.checkbox(label, value=True, key=f"cfg_notif_{key}")
            st.caption(description)


# =========================================================
# PÁGINA PRINCIPAL
# =========================================================

def settings(user):
    # --- Cabeçalho ---
    page_header(
        "Configurações do sistema",
        "Políticas, regras e preferências globais do RoomFlow.",
    )

    # --- Estado da categoria ativa ---
    if "settings_category" not in st.session_state:
        st.session_state.settings_category = "geral"

    # --- Dados do mock ---
    institutions = mock_data_service.institutions()
    institution_name = institutions[0] if institutions else "Instituição não cadastrada"

    # --- Layout: menu | conteúdo ---
    col_menu, col_content = st.columns([1, 3])

    # ---------------------------------------------------------
    # MENU DE CATEGORIAS
    # ---------------------------------------------------------
    with col_menu:
        with st.container(border=True):
            for cat_id, cat_label, cat_icon in CATEGORIES:
                is_active = st.session_state.settings_category == cat_id

                if st.button(
                    cat_label,
                    key=f"cfg_cat_{cat_id}",
                    icon=cat_icon,
                    type="primary" if is_active else "tertiary",
                    width="stretch",
                ):
                    st.session_state.settings_category = cat_id
                    st.rerun()

    # ---------------------------------------------------------
    # ÁREA DE CONTEÚDO
    # ---------------------------------------------------------
    with col_content:
        active_label = next(
            label for cid, label, _ in CATEGORIES
            if cid == st.session_state.settings_category
        )

        with st.container(border=True):
            st.subheader(active_label)

            category = st.session_state.settings_category

            if category == "geral":
                _section_geral(institution_name)
            elif category == "politicas":
                _section_politicas()
            elif category == "conflitos":
                _section_conflitos()
            elif category == "notificacoes":
                _section_notificacoes()

            st.divider()

            if st.button(
                "Salvar configurações",
                key="cfg_salvar",
                type="primary",
                icon=":material/save:",
                width="stretch",
            ):
                set_toast("Configurações salvas com sucesso.")
                st.rerun()

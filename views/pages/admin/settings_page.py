from datetime import time

import streamlit as st

from application.services.institution_management_service import InstitutionUpdate
from controllers.app_state_service import set_toast
from controllers.streamlit_runtime import get_streamlit_actor, get_streamlit_runtime
from models.domain.entities.institution import (
    ConflictPreferences,
    Institution,
    InstitutionPreferences,
    NotificationPreferences,
    ReservationPreferences,
)
from models.domain.exceptions import DomainAuthorizationError, ResourceNotFound
from views.components.ui_components import page_header


CATEGORIES = [
    ("geral", "Informações gerais", ":material/info:"),
    ("politicas", "Políticas de reserva", ":material/policy:"),
    ("conflitos", "Regras de conflito", ":material/gavel:"),
    ("notificacoes", "Notificações", ":material/notifications:"),
]
TIMEZONES = {
    "America/Sao_Paulo": "America/Sao_Paulo (UTC-3)",
    "America/Manaus": "America/Manaus (UTC-4)",
    "America/Fortaleza": "America/Fortaleza (UTC-3)",
}
AUTO_APPROVAL_OPTIONS = {
    "disabled": "Desativada — todas as reservas precisam de aprovação",
    "no_conflict": "Ativada — aprovação automática para solicitações sem conflito",
}
CONFLICT_CRITERIA = {
    "priority": "Por prioridade da atividade",
    "fifo": "Por ordem de chegada (FIFO)",
    "requester_role": "Por cargo do solicitante",
    "manual": "Decisão manual obrigatória",
}
CONFLICT_NOTIFICATION_TIMING = {
    "immediate": "Notificar administrador imediatamente",
    "one_hour": "Aguardar 1 hora antes de notificar",
    "history_only": "Apenas registrar no histórico",
}
NOTIFICATION_OPTIONS = (
    ("reservation_approved", "Reserva aprovada", "Notificar o solicitante quando sua reserva for aprovada"),
    ("reservation_rejected", "Reserva rejeitada", "Notificar o solicitante quando sua reserva for rejeitada"),
    ("conflict_detected", "Conflito detectado", "Notificar administrador e solicitantes envolvidos"),
    ("space_changed", "Alteração de espaço", "Notificar participantes quando um espaço for alterado"),
    ("reservation_cancelled", "Cancelamento de reserva", "Notificar participantes sobre cancelamentos"),
    ("reservation_reminder", "Lembrete de reserva", "Enviar lembrete 1 hora antes da atividade"),
)


def _set_form_values(institution: Institution) -> None:
    reservations = institution.preferences.reservations
    conflicts = institution.preferences.conflicts
    notifications = institution.preferences.notifications
    values = {
        "cfg_nome": institution.name,
        "cfg_endereco": institution.address or "",
        "cfg_cidade": institution.city or "",
        "cfg_estado": institution.state or "",
        "cfg_contato": institution.email or "",
        "cfg_telefone": institution.phone or "",
        "cfg_fuso": TIMEZONES[institution.timezone],
        "cfg_min_ant": reservations.min_advance,
        "cfg_min_unit": reservations.min_advance_unit,
        "cfg_max_ant": reservations.max_advance,
        "cfg_max_unit": reservations.max_advance_unit,
        "cfg_hora_inicio": time.fromisoformat(reservations.allowed_start),
        "cfg_hora_fim": time.fromisoformat(reservations.allowed_end),
        "cfg_aprovacao": AUTO_APPROVAL_OPTIONS[reservations.automatic_approval],
        "cfg_justificativa": reservations.justification_required,
        "cfg_criterio": CONFLICT_CRITERIA[conflicts.resolution_criterion],
        "cfg_notif_conflito": CONFLICT_NOTIFICATION_TIMING[conflicts.notification_timing],
        "cfg_sugestao": conflicts.suggest_alternatives,
    }
    values.update({
        f"cfg_notif_{field}": getattr(notifications, field)
        for field, _, _ in NOTIFICATION_OPTIONS
    })
    for key, value in values.items():
        st.session_state[key] = value


def _render_general() -> None:
    st.text_input("Nome da instituição", key="cfg_nome", max_chars=180)
    st.text_input("Endereço", key="cfg_endereco", max_chars=240)
    col1, col2 = st.columns(2)
    col1.text_input("Cidade", key="cfg_cidade", max_chars=100)
    col2.text_input("Estado (UF)", key="cfg_estado", max_chars=2)
    col1, col2 = st.columns(2)
    col1.text_input("Contato principal", key="cfg_contato", max_chars=255)
    col2.text_input("Telefone", key="cfg_telefone", max_chars=30)
    st.selectbox("Fuso horário", list(TIMEZONES.values()), key="cfg_fuso")


def _render_reservations() -> None:
    col1, col2 = st.columns(2)
    col1.number_input("Antecedência mínima de reserva", min_value=1, max_value=365, key="cfg_min_ant")
    col2.selectbox("Unidade (mínima)", ["dias", "horas"], key="cfg_min_unit")
    col3, col4 = st.columns(2)
    col3.number_input("Antecedência máxima de reserva", min_value=1, max_value=520, key="cfg_max_ant")
    col4.selectbox("Unidade (máxima)", ["dias", "semanas"], key="cfg_max_unit")
    col5, col6 = st.columns(2)
    col5.time_input("Horário de início permitido", key="cfg_hora_inicio")
    col6.time_input("Horário de fim permitido", key="cfg_hora_fim")
    st.selectbox("Aprovação automática", list(AUTO_APPROVAL_OPTIONS.values()), key="cfg_aprovacao")
    st.checkbox("Exigir justificativa em todas as solicitações", key="cfg_justificativa")


def _render_conflicts() -> None:
    st.selectbox("Critério de resolução padrão", list(CONFLICT_CRITERIA.values()), key="cfg_criterio")
    st.selectbox("Notificação em caso de conflito", list(CONFLICT_NOTIFICATION_TIMING.values()), key="cfg_notif_conflito")
    st.checkbox("Sugerir espaços alternativos automaticamente ao detectar conflito", key="cfg_sugestao")


def _render_notifications() -> None:
    for field, label, description in NOTIFICATION_OPTIONS:
        with st.container(border=True):
            st.checkbox(label, key=f"cfg_notif_{field}")
            st.caption(description)


def _build_update() -> InstitutionUpdate:
    timezone = next(key for key, label in TIMEZONES.items() if label == st.session_state.cfg_fuso)
    auto_approval = next(key for key, label in AUTO_APPROVAL_OPTIONS.items() if label == st.session_state.cfg_aprovacao)
    conflict_criterion = next(key for key, label in CONFLICT_CRITERIA.items() if label == st.session_state.cfg_criterio)
    notification_timing = next(key for key, label in CONFLICT_NOTIFICATION_TIMING.items() if label == st.session_state.cfg_notif_conflito)
    preferences = InstitutionPreferences(
        reservations=ReservationPreferences(
            min_advance=int(st.session_state.cfg_min_ant),
            min_advance_unit=st.session_state.cfg_min_unit,
            max_advance=int(st.session_state.cfg_max_ant),
            max_advance_unit=st.session_state.cfg_max_unit,
            allowed_start=st.session_state.cfg_hora_inicio.strftime("%H:%M"),
            allowed_end=st.session_state.cfg_hora_fim.strftime("%H:%M"),
            automatic_approval=auto_approval,
            justification_required=st.session_state.cfg_justificativa,
        ),
        conflicts=ConflictPreferences(
            resolution_criterion=conflict_criterion,
            notification_timing=notification_timing,
            suggest_alternatives=st.session_state.cfg_sugestao,
        ),
        notifications=NotificationPreferences(**{
            field: st.session_state[f"cfg_notif_{field}"]
            for field, _, _ in NOTIFICATION_OPTIONS
        }),
    )
    return InstitutionUpdate(
        name=st.session_state.cfg_nome,
        city=st.session_state.cfg_cidade,
        state=st.session_state.cfg_estado,
        email=st.session_state.cfg_contato,
        phone=st.session_state.cfg_telefone,
        address=st.session_state.cfg_endereco,
        timezone=timezone,
        preferences=preferences,
    )


def settings(user):
    del user
    page_header(
        "Configurações da instituição",
        "Dados, políticas de reserva, conflitos e notificações da sua instituição.",
    )
    actor = get_streamlit_actor()
    if actor is None:
        st.error("Sua sessão expirou. Entre novamente para acessar as configurações.")
        return
    runtime = get_streamlit_runtime()
    try:
        institution = runtime.institution_management.get_own(actor)
    except (DomainAuthorizationError, ResourceNotFound) as exc:
        st.error(str(exc))
        return

    if st.session_state.get("settings_loaded_institution") != institution.id:
        _set_form_values(institution)
        st.session_state.settings_loaded_institution = institution.id
    st.session_state.setdefault("settings_category", "geral")

    col_menu, col_content = st.columns([1, 3])
    with col_menu:
        with st.container(border=True):
            for category_id, label, icon in CATEGORIES:
                if st.button(
                    label,
                    key=f"cfg_cat_{category_id}",
                    icon=icon,
                    type="primary" if st.session_state.settings_category == category_id else "tertiary",
                    width="stretch",
                ):
                    st.session_state.settings_category = category_id
                    st.rerun()

    with col_content:
        active_label = next(label for key, label, _ in CATEGORIES if key == st.session_state.settings_category)
        with st.container(border=True):
            st.subheader(active_label)
            category = st.session_state.settings_category
            if category == "geral":
                _render_general()
            elif category == "politicas":
                _render_reservations()
            elif category == "conflitos":
                _render_conflicts()
            elif category == "notificacoes":
                _render_notifications()
            st.divider()
            if st.button("Salvar configurações", key="cfg_salvar", type="primary", icon=":material/save:", width="stretch"):
                try:
                    runtime.institution_management.update_own(actor, _build_update())
                except (DomainAuthorizationError, ResourceNotFound, ValueError) as exc:
                    st.error(str(exc))
                else:
                    set_toast("Configurações da instituição salvas com sucesso.")
                    st.rerun()

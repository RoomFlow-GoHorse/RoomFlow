from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo

import streamlit as st

from controllers.streamlit_runtime import get_streamlit_actor, get_streamlit_runtime
from models.domain.entities.admin_audit_event import AdminAuditAction as Action
from models.domain.entities.profile import Profile
from models.domain.exceptions import DomainAuthorizationError, ResourceNotFound
from views.components.ui_components import page_header


ACTION_LABELS = {
    Action.USER_CREATED: "Usuário criado",
    Action.USER_PROFILE_CHANGED: "Perfil de usuário alterado",
    Action.USER_ACTIVATED: "Usuário ativado",
    Action.USER_DEACTIVATED: "Usuário desativado",
    Action.USER_ACCOUNT_UPDATED: "Dados de usuário editados",
    Action.INSTITUTION_CREATED: "Instituição criada",
    Action.INSTITUTION_SETTINGS_UPDATED: "Configurações institucionais alteradas",
    Action.INVITATION_CODE_GENERATED: "Código institucional gerado",
    Action.INVITATION_CODE_REPLACED: "Código institucional substituído",
    Action.INVITATION_CODE_REVOKED: "Código institucional revogado",
    Action.ENROLLMENT_CREATED: "Matrícula cadastrada",
    Action.ENROLLMENT_DEACTIVATED: "Matrícula desativada",
    Action.ENROLLMENT_IMPORTED: "Matrícula importada",
    Action.BUILDING_CREATED: "Prédio cadastrado",
    Action.BUILDING_UPDATED: "Prédio editado",
    Action.BUILDING_ACTIVATED: "Prédio ativado",
    Action.BUILDING_DEACTIVATED: "Prédio inativado",
    Action.FLOOR_CREATED: "Andar cadastrado",
    Action.FLOOR_UPDATED: "Andar editado",
    Action.FLOOR_ACTIVATED: "Andar ativado",
    Action.FLOOR_DEACTIVATED: "Andar inativado",
    Action.SPACE_CREATED: "Sala cadastrada",
    Action.SPACE_UPDATED: "Sala editada",
    Action.SPACE_ACTIVATED: "Sala ativada",
    Action.SPACE_DEACTIVATED: "Sala inativada",
    Action.SPACE_RESOURCES_UPDATED: "Recursos da sala alterados",
    Action.RESOURCE_CREATED: "Recurso cadastrado",
    Action.RESOURCE_UPDATED: "Recurso editado",
    Action.RESOURCE_ACTIVATED: "Recurso ativado",
    Action.RESOURCE_DEACTIVATED: "Recurso inativado",
    Action.FLOOR_PLAN_UPLOADED: "Planta enviada",
    Action.FLOOR_PLAN_REPLACED: "Planta substituída",
    Action.FLOOR_PLAN_REMOVED: "Planta removida",
    Action.FLOOR_PLAN_POSITION_SET: "Posição da sala registrada",
    Action.FLOOR_PLAN_POSITION_REMOVED: "Posição da sala removida",
}


def admin_audit(user):
    actor = get_streamlit_actor(user)
    if actor is None or actor.profile is not Profile.ADMIN:
        st.error("Acesso não autorizado.")
        return

    page_header("Histórico administrativo", "Consulte as alterações registradas para sua instituição.")
    runtime = get_streamlit_runtime()
    try:
        institution = runtime.institution_management.get_own(actor)
        users = runtime.user_management.list_users(actor)
    except (DomainAuthorizationError, ResourceNotFound) as exc:
        st.error(str(exc))
        return

    local_timezone = ZoneInfo(institution.timezone)
    actors = {item.id: f"{item.name} ({item.id})" for item in users}
    start_col, end_col, actor_col, action_col = st.columns(4)
    start = start_col.date_input("Data inicial", value=None, format="DD/MM/YYYY", key="audit_start")
    end = end_col.date_input("Data final", value=None, format="DD/MM/YYYY", key="audit_end")
    responsible = actor_col.selectbox(
        "Responsável", [None, *actors], format_func=lambda item: actors.get(item, "Todos"), key="audit_actor",
    )
    action = action_col.selectbox(
        "Ação", [None, *ACTION_LABELS], format_func=lambda item: ACTION_LABELS.get(item, "Todas"), key="audit_action",
    )

    try:
        events = runtime.admin_audit.list_events(
            actor,
            start_at=datetime.combine(start, time.min, local_timezone).astimezone(timezone.utc) if start else None,
            end_at=datetime.combine(end, time.max, local_timezone).astimezone(timezone.utc) if end else None,
            actor_user_id=responsible,
            action=action,
            limit=500,
        )
    except (DomainAuthorizationError, ValueError) as exc:
        st.error(str(exc))
        return

    if not events:
        st.info("Nenhum evento encontrado para os filtros selecionados.")
        return

    st.dataframe(
        [
            {
                "Data e hora": event.occurred_at.astimezone(local_timezone).strftime("%d/%m/%Y %H:%M:%S"),
                "Responsável": event.actor_name,
                "Ação": ACTION_LABELS[event.action],
                "Identificador do recurso": event.resource_id,
            }
            for event in events
        ],
        hide_index=True,
    )
    st.caption(f"{institution.timezone} · Até 500 eventos recentes por consulta")

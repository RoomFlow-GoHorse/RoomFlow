import pandas as pd
import streamlit as st

from controllers.streamlit_runtime import get_streamlit_actor
from models.domain.entities.permission import Permission
from models.domain.entities.profile import Profile
from models.domain.policies.permission_policy import PermissionPolicy
from views.components.ui_components import page_header


EFFECTIVE_PERMISSIONS = [
    ("Acessar dashboard do administrador", {Permission.VIEW_ADMIN_DASHBOARD}),
    ("Consultar histórico administrativo", {Permission.VIEW_ADMIN_AUDIT}),
    ("Gerenciar a própria conta", {Permission.MANAGE_OWN_ACCOUNT}),
    ("Gerenciar usuários, códigos e matrículas", {Permission.MANAGE_USERS}),
    ("Consultar permissões", {Permission.VIEW_PERMISSIONS}),
    ("Gerenciar planta da instituição", {Permission.MANAGE_FLOOR_PLAN}),
    ("Configurações da instituição", {Permission.EDIT_INSTITUTION_SETTINGS}),
    ("Gerenciar salas e recursos", {Permission.MANAGE_FLOOR_PLAN, Permission.MANAGE_SPACES}),
    ("Criar reservas", {Permission.CREATE_RESERVATION}),
    ("Consultar, aprovar e rejeitar solicitações", {Permission.REVIEW_RESERVATIONS}),
    ("Consultar as próprias reservas", {Permission.VIEW_OWN_RESERVATIONS}),
    ("Cancelar as próprias reservas", {Permission.CANCEL_OWN_RESERVATION}),
    ("Consultar e resolver conflitos", {Permission.RESOLVE_CONFLICTS}),
    ("Consultar painel do gerente e ocupação", {Permission.VIEW_MANAGER_DASHBOARD}),
    ("Consultar e marcar as próprias notificações", {Permission.VIEW_NOTIFICATIONS}),
]

PENDING_PERMISSIONS = [
    ("Acessar dashboard do solicitante", "none", "none", "pending", "none"),
    ("Acessar dashboard do participante", "none", "none", "none", "pending"),
    ("Bloquear espaços", "none", "pending", "none", "none"),
    ("Consultar agenda", "none", "none", "pending", "pending"),
    ("Localizar espaços", "none", "none", "none", "pending"),
]

ACCESS_LABELS = {
    "institution": "Instituição do vínculo",
    "own": "Próprio usuário",
    "pending": "A validar",
    "none": "—",
}


def _permission_dataframe() -> pd.DataFrame:
    policy = PermissionPolicy()
    profiles = (Profile.ADMIN, Profile.MANAGER, Profile.REQUESTER, Profile.PARTICIPANT)
    grants = [policy.effective_permissions(profile) for profile in profiles]
    effective_rows = []
    for action, permissions in EFFECTIVE_PERMISSIONS:
        own = {
            Permission.MANAGE_OWN_ACCOUNT, Permission.VIEW_OWN_RESERVATIONS,
            Permission.CANCEL_OWN_RESERVATION, Permission.VIEW_NOTIFICATIONS,
        }
        scope = "own" if permissions & own else "institution"
        effective_rows.append((action, *(scope if permissions & values else "none" for values in grants)))
    return pd.DataFrame(
        [
            {
                "Funcionalidade": action,
                "Administrador": ACCESS_LABELS[admin],
                "Gerente": ACCESS_LABELS[manager],
                "Solicitante": ACCESS_LABELS[requester],
                "Participante": ACCESS_LABELS[participant],
            }
            for action, admin, manager, requester, participant in [*effective_rows, *PENDING_PERMISSIONS]
        ]
    )


def permissions(user):
    actor = get_streamlit_actor(user)
    if actor is None or Permission.VIEW_PERMISSIONS not in PermissionPolicy().effective_permissions(actor.profile):
        st.error("Acesso não autorizado.")
        return

    page_header("Permissões", "Matriz de permissões por perfil de usuário no sistema.")

    with st.container(border=True):
        st.caption(
            ":material/info: Instituição do vínculo: escopo da instituição do usuário autenticado · "
            "Próprio usuário: conta ou reservas do usuário autenticado · "
            "A validar: não concede acesso efetivo pela API"
        )

    st.dataframe(
        _permission_dataframe(),
        column_config={
            "Funcionalidade": st.column_config.TextColumn("Funcionalidade", width="large", pinned=True),
            "Administrador": st.column_config.TextColumn("Administrador", width="small"),
            "Gerente": st.column_config.TextColumn("Gerente", width="small"),
            "Solicitante": st.column_config.TextColumn("Solicitante", width="small"),
            "Participante": st.column_config.TextColumn("Participante", width="small"),
        },
        hide_index=True,
        width="stretch",
    )

    st.info(
        "As permissões institucionais se limitam à instituição vinculada. "
        "Os escopos marcados como 'A validar' aguardam decisão da equipe e não são grants da API.",
        icon=":material/shield:",
    )

import pandas as pd
import streamlit as st

from views.components.ui_components import page_header


# A matriz distingue grants efetivos de acessos ainda sem escopo validado.
PERMISSION_MATRIX = [
    ("Acessar dashboard do administrador", "institution", "none", "none", "none"),
    ("Acessar dashboard do gerente", "none", "pending", "none", "none"),
    ("Acessar dashboard do solicitante", "none", "none", "pending", "none"),
    ("Acessar dashboard do participante", "none", "none", "none", "pending"),
    ("Gerenciar a própria conta", "own", "own", "own", "own"),
    ("Gerenciar usuários", "institution", "none", "none", "none"),
    ("Consultar permissões", "institution", "none", "none", "none"),
    ("Gerenciar planta da instituição", "institution", "none", "none", "none"),
    ("Configurações da instituição", "institution", "none", "none", "none"),
    ("Gerenciar espaços", "none", "pending", "none", "none"),
    ("Gerenciar recursos", "none", "pending", "none", "none"),
    ("Criar reservas", "none", "none", "pending", "none"),
    ("Aprovar / rejeitar reservas", "none", "pending", "none", "none"),
    ("Cancelar próprias reservas", "none", "none", "own_pending", "none"),
    ("Resolver conflitos", "none", "pending", "none", "none"),
    ("Bloquear espaços", "none", "pending", "none", "none"),
    ("Consultar agenda", "none", "none", "pending", "pending"),
    ("Localizar espaços", "none", "none", "none", "pending"),
    ("Histórico de reservas", "none", "pending", "own_pending", "none"),
    ("Consultar notificações", "none", "none", "pending", "pending"),
    ("Relatórios de ocupação", "none", "pending", "none", "none"),
]

ACCESS_LABELS = {
    "institution": "Instituição do vínculo",
    "own": "Próprio usuário",
    "own_pending": "Próprio*",
    "pending": "A validar",
    "none": "—",
}


def _permission_dataframe() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Funcionalidade": action,
                "Administrador": ACCESS_LABELS[admin],
                "Gerente": ACCESS_LABELS[manager],
                "Solicitante": ACCESS_LABELS[requester],
                "Participante": ACCESS_LABELS[participant],
            }
            for action, admin, manager, requester, participant in PERMISSION_MATRIX
        ]
    )


def permissions(user):
    page_header("Permissões", "Matriz de permissões por perfil de usuário no sistema.")

    with st.container(border=True):
        st.caption(
            ":material/info: Instituição do vínculo: escopo do admin autenticado · "
            "Próprio usuário: apenas a própria conta · "
            "Próprio*: somente registros do solicitante, escopo institucional pendente · "
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
        "As permissões efetivas do admin se limitam à instituição vinculada. "
        "Os escopos marcados como 'A validar' aguardam decisão da equipe e não são grants da API.",
        icon=":material/shield:",
    )

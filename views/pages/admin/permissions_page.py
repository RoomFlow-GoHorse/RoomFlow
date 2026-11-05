import pandas as pd
import streamlit as st

from views.components.ui_components import page_header


# Níveis: acesso completo, somente registros próprios ou sem acesso.
PERMISSION_MATRIX = [
    ("Gerenciar usuários", "full", "none", "none", "none"),
    ("Gerenciar permissões", "full", "none", "none", "none"),
    ("Configurações do sistema", "full", "none", "none", "none"),
    ("Gerenciar espaços", "full", "full", "none", "none"),
    ("Gerenciar recursos", "full", "full", "none", "none"),
    ("Tipos de reserva", "full", "full", "none", "none"),
    ("Criar reservas", "full", "full", "own", "none"),
    ("Aprovar / rejeitar reservas", "full", "full", "none", "none"),
    ("Cancelar reservas", "full", "full", "own", "none"),
    ("Resolver conflitos", "full", "full", "none", "none"),
    ("Bloquear espaços", "full", "full", "none", "none"),
    ("Consultar agenda", "full", "full", "full", "full"),
    ("Localizar espaços", "full", "full", "full", "full"),
    ("Histórico de reservas", "full", "full", "own", "none"),
    ("Relatórios de ocupação", "full", "full", "none", "none"),
]

ACCESS_LABELS = {"full": "Completo", "own": "Próprio", "none": "—"}


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
            ":material/info: Completo: acesso a todos os registros · Próprio: apenas os próprios registros · —: sem acesso"
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
        "Apenas o administrador pode editar a matriz de permissões. Alterações afetam imediatamente todos os usuários do perfil selecionado.",
        icon=":material/shield:",
    )

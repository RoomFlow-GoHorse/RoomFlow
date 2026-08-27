from config.constants import PERMISSIONS
from views.components.ui_components import page_header, table


def permissions(user):
    page_header("Permissoes", "Matriz visual de permissoes por perfil.")
    rows = []
    actions = sorted(set().union(*PERMISSIONS.values()))
    for action in actions:
        rows.append([action] + ["Sim" if action in PERMISSIONS[role] else "Nao" for role in ["admin", "gerente", "solicitante", "participante"]])
    table(["Acao", "Gerente", "Administrador", "Solicitante", "Participante"], rows)

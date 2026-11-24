"""Role based landing routes shared by login and authenticated navigation."""


def dashboard_for_role(role: str, *, persistent: bool) -> str:
    if persistent:
        return {
            "admin": "admin_dashboard",
            "gerente": "gerente_dashboard",
            "solicitante": "minhas_reservas",
            "participante": "participante_dashboard",
        }.get(role, "conta")
    return {
        "admin": "admin_dashboard",
        "gerente": "gerente_dashboard",
        "solicitante": "solicitante_dashboard",
        "participante": "participante_dashboard",
    }.get(role, "participante_dashboard")

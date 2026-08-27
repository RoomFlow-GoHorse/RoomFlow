ROLE_LABELS = {
    "admin": "Gerente",
    "gerente": "Administrador",
    "solicitante": "Solicitante",
    "participante": "Participante",
}

ROLE_NAV = {
    "admin": [
        ("Dashboard", "admin_dashboard"),
        ("Agenda", "agenda"),
        ("Reservas", "admin_reservas"),
        ("Conflitos", "admin_conflitos"),
        ("Espacos", "espacos"),
        ("Notificacoes", "notificacoes"),
        ("Conta", "conta"),
    ],
    "gerente": [
        ("Dashboard", "gerente_dashboard"),
        ("Agenda", "agenda"),
        ("Espacos", "espacos"),
        ("Usuarios", "usuarios"),
        ("Permissoes", "permissoes"),
        ("Notificacoes", "notificacoes"),
        ("Conta", "conta"),
    ],
    "solicitante": [
        ("Dashboard", "solicitante_dashboard"),
        ("Agenda", "agenda"),
        ("Nova reserva", "nova_reserva"),
        ("Minhas reservas", "minhas_reservas"),
        ("Notificacoes", "notificacoes"),
        ("Conta", "conta"),
    ],
    "participante": [
        ("Dashboard", "participante_dashboard"),
        ("Agenda", "agenda"),
        ("Localizar", "localizar"),
        ("Alteracoes", "alteracoes"),
        ("Notificacoes", "notificacoes"),
        ("Conta", "conta"),
    ],
}

PUBLIC_NAV = {
    "landing": "Inicio",
    "login": "Entrar",
    "signup_choice": "Criar conta",
    "signup_institution": "Cadastro instituicao",
    "signup_member": "Cadastro membro",
    "forgot_password": "Recuperar senha",
}

STATUS_LABELS = {
    "aprovada": "Aprovada",
    "pendente": "Pendente",
    "rejeitada": "Rejeitada",
    "conflito": "Conflito",
    "em_analise": "Em analise",
    "disponivel": "Disponivel",
    "ocupado": "Ocupado",
    "bloqueado": "Bloqueado",
    "ativo": "Ativo",
    "inativo": "Inativo",
}

PERMISSIONS = {
    "admin": {
        "Aprovar reservas",
        "Rejeitar reservas",
        "Alterar reservas",
        "Resolver conflitos",
        "Gerenciar espacos",
        "Ver agenda",
    },
    "gerente": {
        "Gerenciar usuarios",
        "Ver permissoes",
        "Ver espacos",
        "Ver agenda",
        "Editar configuracoes",
    },
    "solicitante": {
        "Criar reserva",
        "Cancelar propria reserva",
        "Ver agenda",
        "Ver notificacoes",
    },
    "participante": {
        "Ver agenda",
        "Localizar espacos",
        "Ver alteracoes",
        "Ver notificacoes",
    },
}

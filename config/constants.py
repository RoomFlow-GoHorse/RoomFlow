ROLE_LABELS = {
    "admin": "Administrador",
    "gerente": "Gerente",
    "solicitante": "Solicitante",
    "participante": "Participante",
}

ROLE_NAV = {
    "admin": [
        ("Dashboard", "admin_dashboard"),
        ("Usuarios", "usuarios"),
        ("Permissoes", "permissoes"),
        ("Planta da instituição", "planta_instituicao"),
        ("Configuracoes da instituicao", "configuracoes_instituicao"),
    ],
    "gerente": [
        ("Dashboard", "gerente_dashboard"),
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
        "Acessar dashboard do administrador",
        "Gerenciar usuarios",
        "Ver permissoes",
        "Editar configuracoes da instituicao",
    },
    "gerente": {
        "Acessar dashboard do gerente",
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
        "Ver notificacoes",
    },
}

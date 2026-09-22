import hashlib
from datetime import date, timedelta


TODAY = date.today()

PASSWORD_SALT = "roomflow-demo"


def password_hash(password):
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        PASSWORD_SALT.encode("utf-8"),
        120000,
    ).hex()


USERS = [
    {"id": "u1", "name": "Marina Costa", "email": "admin@gmail.com", "role": "admin", "status": "ativo", "initials": "MC"},
    {"id": "u2", "name": "Rafael Nunes", "email": "gerente@gmail.com", "role": "gerente", "status": "ativo", "initials": "RN"},
    {"id": "u3", "name": "Ana Beatriz", "email": "solicitante@gmail.com", "role": "solicitante", "status": "ativo", "initials": "AB"},
    {"id": "u4", "name": "Lucas Lima", "email": "participante@gmail.com", "role": "participante", "status": "ativo", "initials": "LL"},
]

DEMO_USERS = [
    {"id": "u1", "name": "Marina Costa", "email": "admin@gmail.com", "password": "admin123", "role": "admin", "status": "ativo", "initials": "MC"},
    {"id": "u2", "name": "Rafael Nunes", "email": "gerente@gmail.com", "password": "gerente123", "role": "gerente", "status": "ativo", "initials": "RN"},
    {"id": "u3", "name": "Ana Beatriz", "email": "solicitante@gmail.com", "password": "solicitante123", "role": "solicitante", "status": "ativo", "initials": "AB"},
    {"id": "u4", "name": "Lucas Lima", "email": "participante@gmail.com", "password": "participante123", "role": "participante", "status": "ativo", "initials": "LL"},
]


def seed_demo_users():
    users_by_email = {user["email"].lower(): user for user in USERS}

    for demo in DEMO_USERS:
        email = demo["email"].lower()
        seeded_user = {
            key: value
            for key, value in demo.items()
            if key != "password"
        }
        seeded_user["password_hash"] = password_hash(demo["password"])

        if email in users_by_email:
            users_by_email[email].update(seeded_user)
        else:
            USERS.append(seeded_user)
            users_by_email[email] = seeded_user


seed_demo_users()

BUILDINGS = [
    {"id": "b-1", "name": "Bloco A"},
    {"id": "b-2", "name": "Bloco B"},
    {"id": "b-3", "name": "Bloco C"},
    {"id": "b-4", "name": "Bloco D"},
]

FLOORS = [
    {"id": "b-1-f-1", "buildingId": "b-1", "name": "Térreo"},
    {"id": "b-1-f-2", "buildingId": "b-1", "name": "1º andar"},
    {"id": "b-1-f-3", "buildingId": "b-1", "name": "2º andar"},
    {"id": "b-2-f-1", "buildingId": "b-2", "name": "Térreo"},
    {"id": "b-2-f-2", "buildingId": "b-2", "name": "2º andar"},
    {"id": "b-3-f-1", "buildingId": "b-3", "name": "Térreo"},
    {"id": "b-4-f-1", "buildingId": "b-4", "name": "Térreo"},
]

SPACES = [
    {"id": "s1", "name": "Sala 101", "type": "Sala de aula", "capacity": 20, "building": "Bloco A", "floor": "1º andar", "location": "Bloco A, 1º andar", "status": "disponivel", "resources": ["Projetor", "Quadro branco"], "occupancy": 64},
    {"id": "s2", "name": "Sala 204", "type": "Sala de aula", "capacity": 30, "building": "Bloco B", "floor": "2º andar", "location": "Bloco B, 2º andar", "status": "ocupado", "resources": ["TV", "Ar-condicionado"], "occupancy": 78},
    {"id": "s3", "name": "Auditório Principal", "type": "Auditório", "capacity": 150, "building": "Bloco A", "floor": "Térreo", "location": "Bloco A, Térreo", "status": "disponivel", "resources": ["Audio", "Microfones", "Projetor"], "occupancy": 52},
    {"id": "s4", "name": "Laboratório de Informática", "type": "Laboratório", "capacity": 40, "building": "Bloco C", "floor": "Térreo", "location": "Bloco C, Térreo", "status": "disponivel", "resources": ["Computadores", "Projetor"], "occupancy": 71},
    {"id": "s5", "name": "Auditório A", "type": "Auditório", "capacity": 80, "building": "Bloco D", "floor": "Térreo", "location": "Bloco D, Térreo", "status": "bloqueado", "resources": ["Audio"], "occupancy": 12},
    {"id": "s6", "name": "Sala de Reuniões B", "type": "Sala de reuniões", "capacity": 8, "building": "Bloco A", "floor": "1º andar", "location": "Bloco A, 1º andar", "status": "disponivel", "resources": ["Videoconferencia"], "occupancy": 46},
]

RESERVATIONS = [
    {"id": "r1", "requester": "Ana Beatriz", "requester_id": "u3", "title": "Aula de Metodologia", "space": "Sala 101", "date": TODAY.isoformat(), "start": "08:00", "end": "10:00", "type": "Aula", "status": "aprovada", "priority": "media", "participants": 18, "justification": "Aula regular da turma ADM-2."},
    {"id": "r2", "requester": "Ana Beatriz", "requester_id": "u3", "title": "Banca de TCC", "space": "Sala 204", "date": TODAY.isoformat(), "start": "09:30", "end": "11:00", "type": "Banca", "status": "pendente", "priority": "alta", "participants": 7, "justification": "Banca com convidados externos."},
    {"id": "r3", "requester": "Ana Beatriz", "requester_id": "u3", "title": "Workshop de Pesquisa", "space": "Auditorio Principal", "date": (TODAY + timedelta(days=1)).isoformat(), "start": "14:00", "end": "17:00", "type": "Workshop", "status": "em_analise", "priority": "media", "participants": 90, "justification": "Evento institucional."},
    {"id": "r4", "requester": "Rafael Nunes", "requester_id": "u2", "title": "Reuniao de coordenacao", "space": "Sala de Reunioes B", "date": (TODAY + timedelta(days=2)).isoformat(), "start": "10:00", "end": "11:30", "type": "Reuniao", "status": "aprovada", "priority": "baixa", "participants": 6, "justification": "Alinhamento semanal."},
    {"id": "r5", "requester": "Ana Beatriz", "requester_id": "u3", "title": "Monitoria", "space": "Laboratorio de Informatica", "date": (TODAY - timedelta(days=1)).isoformat(), "start": "16:00", "end": "18:00", "type": "Monitoria", "status": "rejeitada", "priority": "baixa", "participants": 22, "justification": "Conflito de recursos."},
    {"id": "r6", "requester": "Rafael Nunes", "requester_id": "u2", "title": "Reunião com coordenação", "space": "Sala 204", "date": TODAY.isoformat(), "start": "10:00", "end": "11:30", "type": "Reunião", "status": "conflito", "priority": "alta", "participants": 10, "justification": "Reunião extraordinária da coordenação."},
    {"id": "r7", "requester": "Marina Costa", "requester_id": "u1", "title": "Encontro de docentes", "space": "Auditorio Principal", "date": (TODAY + timedelta(days=1)).isoformat(), "start": "14:00", "end": "16:00", "type": "Reunião", "status": "conflito", "priority": "alta", "participants": 45, "justification": "Planejamento do próximo período letivo."},
    {"id": "r8", "requester": "Lucas Lima", "requester_id": "u4", "title": "Palestra de carreiras", "space": "Auditorio Principal", "date": (TODAY + timedelta(days=1)).isoformat(), "start": "15:00", "end": "17:00", "type": "Palestra", "status": "conflito", "priority": "media", "participants": 80, "justification": "Atividade aberta aos estudantes."},
    {"id": "r9", "requester": "Rafael Nunes", "requester_id": "u2", "title": "Treinamento de equipe", "space": "Sala 101", "date": TODAY.isoformat(), "start": "09:00", "end": "11:00", "type": "Treinamento", "status": "aprovada", "priority": "media", "participants": 16, "justification": "Capacitação interna da equipe."},
]

CONFLICTS = [
    {"id": "c1", "space": "Sala 204", "status": "nao_resolvido", "severity": "alta", "reservation_a": "r2", "reservation_b": "r6", "affected_reservations": ["r2", "r6"], "reason": "Sobreposicao entre 10:00 e 11:00", "decision": ""},
    {"id": "c2", "space": "Auditorio Principal", "status": "em_analise", "severity": "media", "reservation_a": "r3", "reservation_b": "r7", "affected_reservations": ["r3", "r7", "r8"], "reason": "Evento institucional disputa mesmo periodo", "decision": ""},
    {"id": "c3", "space": "Sala 101", "status": "resolvido", "severity": "baixa", "reservation_a": "r1", "reservation_b": "r9", "affected_reservations": ["r1", "r9"], "reason": "Sobreposicao entre 09:00 e 10:00", "decision": "Mantida a reserva de Aula de Metodologia."},
]

NOTIFICATIONS = [
    {
        "id": "n1",
        "title": "Reserva confirmada",
        "message": "Sua reserva da Sala 101 para Aula de Metodologia foi aprovada.",
        "type": "success",
        "category": "reserva",
        "date": "Hoje, 14:30",
        "read": False,
        "audiences": ["solicitante"],
    },
    {
        "id": "n2",
        "title": "Alteração de horário solicitada",
        "message": "O horário da reserva de Workshop de Pesquisa foi ajustado para 14:00.",
        "type": "warning",
        "category": "alteracao",
        "date": "Hoje, 11:20",
        "read": False,
        "audiences": ["solicitante"],
    },
    {
        "id": "n3",
        "title": "Conflito de sala identificado",
        "message": "Foi identificado um conflito de horário na Sala 204 para a Banca de TCC.",
        "type": "danger",
        "category": "conflito",
        "date": "Ontem, 16:45",
        "read": True,
        "audiences": ["solicitante"],
    },
    {
        "id": "n4",
        "title": "Reserva encerrada",
        "message": "A solicitação de Monitoria no Laboratório de Informática foi finalizada.",
        "type": "info",
        "category": "reserva",
        "date": "18/09/2026, 10:00",
        "read": True,
        "audiences": ["solicitante"],
    },
    {
        "id": "n5",
        "title": "Mudança de sala da atividade",
        "message": "A Aula de Metodologia de hoje mudou da Sala 204 para a Sala 101.",
        "type": "warning",
        "category": "alteracao",
        "date": "Hoje, 08:15",
        "read": False,
        "audiences": ["participante"],
    },
    {
        "id": "n6",
        "title": "Ajuste no horário do Workshop",
        "message": "O Workshop de Pesquisa amanhã começará às 14:00 (anteriormente 13:30).",
        "type": "info",
        "category": "alteracao",
        "date": "Ontem, 17:30",
        "read": False,
        "audiences": ["participante"],
    },
    {
        "id": "n7",
        "title": "Sessão de Monitoria cancelada",
        "message": "A monitoria de sexta-feira foi cancelada devido à manutenção do laboratório.",
        "type": "danger",
        "category": "alteracao",
        "date": "19/09/2026, 15:10",
        "read": True,
        "audiences": ["participante"],
    },
    {
        "id": "n8",
        "title": "Solicitação pendente de aprovação",
        "message": "Nova solicitação para Auditório Principal aguarda análise de reserva.",
        "type": "info",
        "category": "reserva",
        "date": "Hoje, 13:10",
        "read": False,
        "audiences": ["gerente"],
    },
    {
        "id": "n9",
        "title": "Alerta de sobreposição de salas",
        "message": "Conflito severo detectado na Sala 204 entre Banca de TCC e Aula regular.",
        "type": "danger",
        "category": "conflito",
        "date": "Hoje, 09:40",
        "read": False,
        "audiences": ["gerente"],
    },
    {
        "id": "n10",
        "title": "Reserva de espaço aprovada",
        "message": "A reserva da Sala de Reuniões B para Reunião de Coordenação foi concluída.",
        "type": "success",
        "category": "reserva",
        "date": "Ontem, 14:00",
        "read": True,
        "audiences": ["gerente"],
    },
    {
        "id": "n11",
        "title": "Conflito de alta prioridade",
        "message": "Sobreposição não resolvida no Auditório Principal para evento institucional.",
        "type": "danger",
        "category": "conflito",
        "date": "Hoje, 15:00",
        "read": False,
        "audiences": ["admin"],
    },
    {
        "id": "n12",
        "title": "Nova reserva cadastrada no sistema",
        "message": "Uma nova solicitação de reserva foi registrada no bloco administrativo.",
        "type": "info",
        "category": "reserva",
        "date": "Hoje, 10:30",
        "read": False,
        "audiences": ["admin"],
    },
    {
        "id": "n13",
        "title": "Reserva encerrada com sucesso",
        "message": "A utilização do Laboratório de Informática foi concluída sem intercorrências.",
        "type": "success",
        "category": "reserva",
        "date": "Ontem, 18:00",
        "read": True,
        "audiences": ["admin"],
    },
    {
        "id": "n14",
        "title": "Atualização de segurança do sistema",
        "message": "Nova diretriz de acesso institucional aplicada.",
        "type": "info",
        "category": "sistema",
        "date": "15/09/2026",
        "read": True,
        "audiences": ["admin", "gerente", "solicitante", "participante"],
    },
]

RESOURCES = [
    {"name": "Projetor", "total": 8, "available": 5},
    {"name": "Ar-condicionado", "total": 12, "available": 11},
    {"name": "Computadores", "total": 45, "available": 40},
    {"name": "Microfones", "total": 6, "available": 4},
]

INSTITUTIONS = ["Faculdade Unisapiens", "Centro Universitario Norte", "Instituto Rio Negro", "Escola Tecnica Central"]

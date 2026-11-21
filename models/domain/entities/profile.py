from enum import Enum


class Profile(str, Enum):
    ADMIN = "admin"
    MANAGER = "gerente"
    REQUESTER = "solicitante"
    PARTICIPANT = "participante"

"""Intermedia as ações das telas de conflitos."""

from models.conflict_model import ConflictModel
from services.app_state_service import model_state


def resolve_conflict(conflict_id, decision):
    return ConflictModel(model_state()).resolve_conflict(conflict_id=conflict_id, decision=decision)


def conflicts():
    return ConflictModel(model_state()).conflicts()

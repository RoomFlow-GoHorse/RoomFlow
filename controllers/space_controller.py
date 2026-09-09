"""Intermedia as ações das telas de espaços."""

from models.space_model import SpaceModel
from services.app_state_service import model_state


def spaces(status=None, query=''):
    return SpaceModel(model_state()).spaces(status=status, query=query)


def toggle_space(space_id):
    return SpaceModel(model_state()).toggle_space(space_id=space_id)


def resources():
    return SpaceModel(model_state()).resources()

"""Intermedia as ações das telas de usuários e instituições."""

from models.user_model import UserModel
from services.app_state_service import model_state


def users():
    return UserModel(model_state()).users()


def toggle_user(user_id):
    return UserModel(model_state()).toggle_user(user_id=user_id)


def institutions():
    return UserModel(model_state()).institutions()

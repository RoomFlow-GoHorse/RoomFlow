"""Intermedia as ações das telas de notificações."""

from models.notification_model import NotificationModel
from services.app_state_service import model_state


def notifications_for(role):
    return NotificationModel(model_state()).notifications_for(role=role)


def mark_notification_read(notification_id=None, role=None):
    return NotificationModel(model_state()).mark_notification_read(notification_id=notification_id, role=role)

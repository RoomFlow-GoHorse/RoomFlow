"""Intermedia as ações das telas de reservas."""

from models.reservation_model import ReservationModel
from services.app_state_service import model_state


def reservations(status=None, requester_id=None):
    return ReservationModel(model_state()).reservations(status=status, requester_id=requester_id)


def update_reservation_status(reservation_id, status):
    return ReservationModel(model_state()).update_reservation_status(reservation_id=reservation_id, status=status)


def create_reservation(data):
    return ReservationModel(model_state()).create_reservation(data=data)


def agenda_events(space='Todos', event_type='Todos'):
    return ReservationModel(model_state()).agenda_events(space=space, event_type=event_type)

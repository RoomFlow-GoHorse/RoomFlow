"""Inicializa dados de demonstração em um armazenamento por sessão."""

import copy

from data import mock_data


def initialize_data(state):
    defaults = {
        "reservations": copy.deepcopy(mock_data.RESERVATIONS),
        "spaces": copy.deepcopy(mock_data.SPACES),
        "users": copy.deepcopy(mock_data.USERS),
        "resources": copy.deepcopy(mock_data.RESOURCES),
        "institutions": copy.deepcopy(mock_data.INSTITUTIONS),
        "notifications": copy.deepcopy(mock_data.NOTIFICATIONS),
        "conflicts": copy.deepcopy(mock_data.CONFLICTS),
    }
    for key, value in defaults.items():
        state.setdefault(key, value)

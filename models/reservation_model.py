"""Dados e operações de reservas, independentes da interface."""


class ReservationModel:
    def __init__(self, state):
        self.state = state

    def reservations(self, status=None, requester_id=None):
        items = self.state["reservations"]
        if status and status != "Todas":
            items = [item for item in items if item["status"] == status]
        if requester_id:
            items = [item for item in items if item["requester_id"] == requester_id]
        return items

    def update_reservation_status(self, reservation_id, status):
        for item in self.state["reservations"]:
            if item["id"] == reservation_id:
                item["status"] = status
                return item
        return None

    def create_reservation(self, data):
        data["id"] = f"r{len(self.state['reservations']) + 1}"
        data.setdefault("status", "pendente")
        data.setdefault("priority", "media")
        self.state["reservations"].append(data)
        return data

    def agenda_events(self, space="Todos", event_type="Todos"):
        items = [item for item in self.state["reservations"] if item["status"] in {"aprovada", "pendente", "em_analise", "conflito"}]
        if space != "Todos":
            items = [item for item in items if item["space"] == space]
        if event_type != "Todos":
            items = [item for item in items if item["type"] == event_type]
        return sorted(items, key=lambda item: (item["date"], item["start"]))

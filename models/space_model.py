"""Dados e operações de espaços, independentes da interface."""


class SpaceModel:
    def __init__(self, state):
        self.state = state

    def spaces(self, status=None, query=""):
        items = self.state["spaces"]
        if status and status != "Todos":
            items = [item for item in items if item["status"] == status]
        if query:
            items = [item for item in items if query.lower() in item["name"].lower()]
        return items

    def toggle_space(self, space_id):
        for item in self.state["spaces"]:
            if item["id"] == space_id:
                item["status"] = "disponivel" if item["status"] == "bloqueado" else "bloqueado"
                return item
        return None

    def resources(self):
        return self.state["resources"]

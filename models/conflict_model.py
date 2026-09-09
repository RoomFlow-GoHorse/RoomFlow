"""Dados e operações de conflitos, independentes da interface."""


class ConflictModel:
    def __init__(self, state):
        self.state = state

    def resolve_conflict(self, conflict_id, decision):
        for item in self.state["conflicts"]:
            if item["id"] == conflict_id:
                item["status"] = "em_analise" if decision == "alterar" else "resolvido"
                item["decision"] = decision
                return item
        return None

    def conflicts(self):
        return self.state["conflicts"]

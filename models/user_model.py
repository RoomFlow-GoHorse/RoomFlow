"""Dados e operações de usuários e instituições, independentes da interface."""


class UserModel:
    def __init__(self, state):
        self.state = state

    def users(self):
        return self.state["users"]

    def toggle_user(self, user_id):
        for item in self.state["users"]:
            if item["id"] == user_id:
                item["status"] = "ativo" if item["status"] == "inativo" else "inativo"
                return item
        return None

    def institutions(self):
        return self.state["institutions"]

"""Dados e operações de notificações, independentes da interface."""


class NotificationModel:
    def __init__(self, state):
        self.state = state

    def notifications_for(self, role):
        return [item for item in self.state["notifications"] if role in item["audiences"]]

    def mark_notification_read(self, notification_id=None, role=None):
        for item in self.state["notifications"]:
            matches_notification = notification_id is None or item["id"] == notification_id
            matches_role = role is None or role in item["audiences"]
            if matches_notification and matches_role:
                item["read"] = True

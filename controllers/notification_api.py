from urllib.parse import quote


class ApiNotifications:
    def __init__(self, api):
        self._api = api

    def inbox(self, *, unread_only=False, category=None, limit=25, offset=0):
        params = {"unread_only": unread_only, "limit": limit, "offset": offset}
        if category is not None:
            params["category"] = category
        return self._api.request("GET", "/notifications", params=params)

    def unread_count(self):
        return self._api.request("GET", "/notifications/unread-count")["unread_count"]

    def mark_read(self, notification_id):
        return self._api.request("PATCH", f"/notifications/{quote(notification_id, safe='')}/read")

    def mark_all_read(self):
        return self._api.request("PATCH", "/notifications/read")

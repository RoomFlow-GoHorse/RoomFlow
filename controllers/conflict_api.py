from urllib.parse import quote


class ApiConflicts:
    def __init__(self, api):
        self._api = api

    def list(self, status=None, query=""):
        params = {"query": query, **({"status": status} if status else {})}
        return self._api.request("GET", "/conflicts", params=params)

    def detect(self):
        return self._api.request("POST", "/conflicts/detect")

    def detail(self, conflict_id):
        return self._api.request("GET", f"/conflicts/{quote(conflict_id, safe='')}")

    def alternatives(self, conflict_id):
        return self._api.request("GET", f"/conflicts/{quote(conflict_id, safe='')}/alternatives")

    def resolve(self, conflict_id, payload):
        return self._api.request("POST", f"/conflicts/{quote(conflict_id, safe='')}/resolve", payload=payload)

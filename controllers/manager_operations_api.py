from datetime import date, time


class ApiManagerOperations:
    def __init__(self, api):
        self._api = api

    def context(self):
        return self._api.request("GET", "/manager/operations/context")

    def report(self, **filters):
        params = {
            key: value.isoformat() if isinstance(value, (date, time)) else value
            for key, value in filters.items() if value is not None
        }
        return self._api.request("GET", "/manager/operations", params=params)
